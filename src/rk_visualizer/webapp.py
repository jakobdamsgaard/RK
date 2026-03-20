from __future__ import annotations

import argparse
import json
import math
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from .methods import available_methods, get_method
from .parser import ExpressionCompilationError, compile_expression
from .reference import build_reference_solution
from .solver import compute_abs_errors, linear_interpolate, solve_initial_value_problem


STATIC_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def available_method_payloads() -> list[dict[str, Any]]:
    return [
        {
            "key": method.key,
            "name": method.name,
            "description": method.description,
            "color": method.color,
            "stages": method.stages,
        }
        for method in available_methods()
    ]


def build_simulation_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    function_expression = str(raw_payload.get("function", "")).strip()
    exact_expression = str(raw_payload.get("exact_function", "")).strip()
    method_key = str(raw_payload.get("method", "rk4")).strip() or "rk4"
    t0 = float(raw_payload.get("t0", 0.0))
    y0 = float(raw_payload.get("y0", 0.5))
    h = float(raw_payload.get("h", 0.2))
    steps = int(raw_payload.get("steps", 10))
    refinement = int(raw_payload.get("refinement", 40))

    if not function_expression:
        raise ValueError("Function expression cannot be empty.")
    if h <= 0.0:
        raise ValueError("Step size h must be positive.")
    if steps < 1:
        raise ValueError("Steps must be at least 1.")
    if refinement < 2:
        raise ValueError("Refinement must be at least 2.")

    method = get_method(method_key)
    ode_function = compile_expression(function_expression, ("t", "y"))
    exact_function = (
        compile_expression(exact_expression, ("t",)) if exact_expression else None
    )

    trace = solve_initial_value_problem(
        function=ode_function,
        method=method,
        t0=t0,
        y0=y0,
        h=h,
        steps=steps,
    )

    reference_label: str
    reference_points: list[dict[str, float]]
    reference_values: list[float]
    if exact_function is not None:
        t_end = t0 + steps * h
        dense_count = max(420, steps * 36)
        dense_ts = [
            t0 + (t_end - t0) * index / (dense_count - 1)
            for index in range(dense_count)
        ]
        try:
            reference_values = [float(exact_function(t_value)) for t_value in trace.ts]
            reference_points = [
                {"t": t_value, "y": float(exact_function(t_value))}
                for t_value in dense_ts
            ]
        except Exception as error:
            raise ValueError(f"Could not evaluate exact solution: {error}") from error
        reference_label = "Eksakt losning"
    else:
        reference_trace = build_reference_solution(
            function=ode_function,
            t0=t0,
            y0=y0,
            h=h,
            steps=steps,
            refinement=refinement,
        )
        reference_values = [
            linear_interpolate(reference_trace.ts, reference_trace.ys, t_value)
            for t_value in trace.ts
        ]
        reference_points = [
            {"t": t_value, "y": y_value}
            for t_value, y_value in zip(
                reference_trace.ts,
                reference_trace.ys,
                strict=True,
            )
        ]
        reference_label = f"RK4 referanse ({refinement}x tettere)"

    errors = compute_abs_errors(list(trace.ys), reference_values)
    trace_points = [
        {"t": t_value, "y": y_value}
        for t_value, y_value in zip(trace.ts, trace.ys, strict=True)
    ]
    serialized_steps = [
        {
            "index": step.index,
            "t": step.t,
            "y": step.y,
            "t_next": step.t_next,
            "y_next": step.y_next,
            "h": step.h,
            "stage_samples": [
                {
                    "stage_number": stage.stage_number,
                    "t": stage.t,
                    "y": stage.y,
                    "slope": stage.slope,
                }
                for stage in step.stage_samples
            ],
            "error": errors[step.index + 1],
        }
        for step in trace.steps
    ]

    view = build_view_box(trace_points, reference_points, serialized_steps)
    slope_field = build_slope_field_samples(
        ode_function,
        view,
        columns=20,
        rows=14,
    )
    phases = build_animation_phases(trace, errors)

    return {
        "method": {
            "key": method.key,
            "name": method.name,
            "description": method.description,
            "color": method.color,
            "stages": method.stages,
        },
        "problem": {
            "function": function_expression,
            "exact_function": exact_expression,
            "t0": t0,
            "y0": y0,
            "h": h,
            "steps": steps,
            "t_end": t0 + steps * h,
        },
        "summary": {
            "reference_label": reference_label,
            "max_error": max(errors),
            "final_error": errors[-1],
            "final_value": trace.ys[-1],
        },
        "trace": {
            "points": trace_points,
            "steps": serialized_steps,
        },
        "reference": {
            "label": reference_label,
            "points": reference_points,
        },
        "view": view,
        "slope_field": slope_field,
        "phases": phases,
    }


def build_view_box(
    trace_points: list[dict[str, float]],
    reference_points: list[dict[str, float]],
    serialized_steps: list[dict[str, Any]],
) -> dict[str, float]:
    all_points = trace_points + reference_points
    for step in serialized_steps:
        for stage in step["stage_samples"]:
            all_points.append({"t": stage["t"], "y": stage["y"]})

    x_values = [point["t"] for point in all_points]
    y_values = [point["y"] for point in all_points]
    x_min, x_max = resolve_range(x_values)
    y_min, y_max = resolve_range(y_values)
    return {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
    }


def resolve_range(values: list[float]) -> tuple[float, float]:
    lower = min(values)
    upper = max(values)
    if math.isclose(lower, upper):
        padding = 1.0 if math.isclose(lower, 0.0) else abs(lower) * 0.25
        return (lower - padding, upper + padding)
    padding = (upper - lower) * 0.16
    return (lower - padding, upper + padding)


def build_slope_field_samples(
    function,
    view: dict[str, float],
    columns: int,
    rows: int,
) -> list[dict[str, float]]:
    samples: list[dict[str, float]] = []
    x_min = view["x_min"]
    x_max = view["x_max"]
    y_min = view["y_min"]
    y_max = view["y_max"]
    for column in range(columns):
        t_value = x_min + (column + 0.5) * (x_max - x_min) / columns
        for row in range(rows):
            y_value = y_min + (row + 0.5) * (y_max - y_min) / rows
            try:
                slope = float(function(t_value, y_value))
            except Exception:
                continue
            if not math.isfinite(slope):
                continue
            samples.append(
                {
                    "t": t_value,
                    "y": y_value,
                    "slope": slope,
                }
            )
    return samples


def build_animation_phases(trace, errors: list[float]) -> list[dict[str, Any]]:
    phases: list[dict[str, Any]] = []
    for step in trace.steps:
        for stage_index, stage in enumerate(step.stage_samples):
            anchor = (
                {"t": step.t, "y": step.y}
                if stage_index == 0
                else {
                    "t": step.stage_samples[stage_index - 1].t,
                    "y": step.stage_samples[stage_index - 1].y,
                }
            )
            phases.append(
                {
                    "kind": "stage",
                    "step_index": step.index,
                    "stage_index": stage_index,
                    "duration_ms": 950,
                    "title": f"Evaluerer k{stage.stage_number}",
                    "description": stage_description(stage_index),
                    "formula": stage_formula(trace.method, step, stage_index),
                    "start_point": anchor,
                    "end_point": {"t": stage.t, "y": stage.y},
                    "focus_point": {"t": stage.t, "y": stage.y},
                    "slope": stage.slope,
                }
            )
        phases.append(
            {
                "kind": "advance",
                "step_index": step.index,
                "stage_index": None,
                "duration_ms": 1200,
                "title": "Kombinerer helningene",
                "description": (
                    "Metoden blander stage-helningene med vektene i Butcher-tablaet "
                    "og oppdaterer losningen til neste punkt."
                ),
                "formula": combine_formula(trace.method, step),
                "start_point": {"t": step.t, "y": step.y},
                "end_point": {"t": step.t_next, "y": step.y_next},
                "focus_point": {"t": step.t_next, "y": step.y_next},
                "slope": None,
                "error": errors[step.index + 1],
            }
        )
    return phases


def stage_description(stage_index: int) -> str:
    if stage_index == 0:
        return (
            "Den forste helningen måles direkte i startpunktet for steget. "
            "Det er den enkleste lokale retningen metoden kan lese av."
        )
    return (
        "Tidligere helninger brukes til a hoppe til et hjelpepunkt inne i intervallet. "
        "Der måles en ny helning som korrigerer retningen videre."
    )


def stage_formula(method, step, stage_index: int) -> str:
    stage = step.stage_samples[stage_index]
    terms: list[str] = []
    for prev_index in range(stage_index):
        coefficient = method.a[stage_index][prev_index]
        if math.isclose(coefficient, 0.0):
            continue
        terms.append(f"{fmt(coefficient)}*k{prev_index + 1}")
    state_expr = "y_n" if not terms else f"y_n + h*({' + '.join(terms)})"
    return "\n".join(
        (
            f"k{stage.stage_number} = f(t_n + {fmt(method.c[stage_index])}*h, {state_expr})",
            f"      = f({fmt(stage.t)}, {fmt(stage.y)})",
            f"      = {fmt(stage.slope)}",
        )
    )


def combine_formula(method, step) -> str:
    symbolic_terms: list[str] = []
    numeric_terms: list[str] = []
    for stage_index, weight in enumerate(method.b):
        if math.isclose(weight, 0.0):
            continue
        slope = step.stage_samples[stage_index].slope
        symbolic_terms.append(f"{fmt(weight)}*k{stage_index + 1}")
        numeric_terms.append(f"{fmt(weight)}*{fmt(slope)}")
    return "\n".join(
        (
            f"y_(n+1) = y_n + h*({' + '.join(symbolic_terms)})",
            f"        = {fmt(step.y)} + {fmt(step.h)}*({' + '.join(numeric_terms)})",
            f"        = {fmt(step.y_next)}",
        )
    )


def fmt(value: float) -> str:
    return f"{value:.6g}"


class RKRequestHandler(BaseHTTPRequestHandler):
    server_version = "RKVisualizerHTTP/0.1"

    def do_GET(self) -> None:
        if self.path == "/api/methods":
            self._send_json({"methods": available_method_payloads()})
            return

        asset = STATIC_ASSETS.get(self.path)
        if asset is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        filename, content_type = asset
        asset_bytes = load_asset(filename)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(asset_bytes)))
        self.end_headers()
        self.wfile.write(asset_bytes)

    def do_POST(self) -> None:
        if self.path != "/api/simulate":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
            response_payload = build_simulation_payload(payload)
        except json.JSONDecodeError as error:
            self._send_json({"error": f"Invalid JSON: {error}"}, status=HTTPStatus.BAD_REQUEST)
            return
        except (ValueError, TypeError, KeyError, ExpressionCompilationError) as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as error:
            self._send_json(
                {"error": f"Simulation failed: {error}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(response_payload)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def load_asset(filename: str) -> bytes:
    return files("rk_visualizer").joinpath("web").joinpath(filename).read_bytes()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the RK visualizer web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), RKRequestHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"RK Visualizer running at {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
