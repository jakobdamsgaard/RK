from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .solver import SolutionTrace, StepRecord


PhaseKind = Literal["stage", "combine"]


@dataclass(frozen=True)
class AnimationPhase:
    step_index: int
    kind: PhaseKind
    stage_index: int | None
    title: str
    description: str
    formula: str
    duration_ms: int


def build_animation_script(trace: SolutionTrace) -> tuple[AnimationPhase, ...]:
    phases: list[AnimationPhase] = []
    method = trace.method
    for step in trace.steps:
        for stage_index, stage in enumerate(step.stage_samples):
            phases.append(
                AnimationPhase(
                    step_index=step.index,
                    kind="stage",
                    stage_index=stage_index,
                    title=f"Steg {step.index + 1}: evaluerer k{stage.stage_number}",
                    description=_build_stage_description(step, stage_index),
                    formula=_format_stage_formula(method, step, stage_index),
                    duration_ms=900,
                )
            )
        phases.append(
            AnimationPhase(
                step_index=step.index,
                kind="combine",
                stage_index=None,
                title=f"Steg {step.index + 1}: kombinerer helningene",
                description=(
                    "Metoden blander alle stage-helningene med vektene b_i og "
                    "oppdaterer y-verdien til neste nettpunktsposisjon."
                ),
                formula=_format_combine_formula(method, step),
                duration_ms=1200,
            )
        )
    return tuple(phases)


def _build_stage_description(step: StepRecord, stage_index: int) -> str:
    if stage_index == 0:
        return (
            "Første stage måler helningen direkte i startpunktet for steget. "
            "Denne helningen brukes som første byggestein i oppdateringen."
        )
    return (
        "Metoden bruker tidligere helninger til å hoppe til et hjelpepunkt "
        "inne i steget. Der måles en ny lokal helning som justerer retningen."
    )


def _format_stage_formula(method, step: StepRecord, stage_index: int) -> str:
    stage = step.stage_samples[stage_index]
    c_value = method.c[stage_index]
    contributions: list[str] = []
    for prev_index in range(stage_index):
        coefficient = method.a[stage_index][prev_index]
        if math.isclose(coefficient, 0.0):
            continue
        contributions.append(f"{_fmt(coefficient)}*k{prev_index + 1}")

    if contributions:
        helper_expr = " + ".join(contributions)
        state_expr = f"y_n + h*({helper_expr})"
    else:
        state_expr = "y_n"

    return "\n".join(
        (
            f"k{stage.stage_number} = f(t_n + {_fmt(c_value)}*h, {state_expr})",
            f"      = f({_fmt(stage.t)}, {_fmt(stage.y)})",
            f"      = {_fmt(stage.slope)}",
        )
    )


def _format_combine_formula(method, step: StepRecord) -> str:
    symbolic_terms: list[str] = []
    numeric_terms: list[str] = []
    for stage_index, weight in enumerate(method.b):
        if math.isclose(weight, 0.0):
            continue
        slope = step.stage_samples[stage_index].slope
        symbolic_terms.append(f"{_fmt(weight)}*k{stage_index + 1}")
        numeric_terms.append(f"{_fmt(weight)}*{_fmt(slope)}")
    return "\n".join(
        (
            f"y_(n+1) = y_n + h*({' + '.join(symbolic_terms)})",
            f"        = {_fmt(step.y)} + {_fmt(step.h)}*({' + '.join(numeric_terms)})",
            f"        = {_fmt(step.y_next)}",
        )
    )


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def blend_hex(color: str, target: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    red_1, green_1, blue_1 = _hex_to_rgb(color)
    red_2, green_2, blue_2 = _hex_to_rgb(target)
    red = round(red_1 + (red_2 - red_1) * ratio)
    green = round(green_1 + (green_2 - green_1) * ratio)
    blue = round(blue_1 + (blue_2 - blue_1) * ratio)
    return f"#{red:02X}{green:02X}{blue:02X}"


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    stripped = color.lstrip("#")
    if len(stripped) != 6:
        raise ValueError(f"Expected RGB hex color, received: {color}")
    return (
        int(stripped[0:2], 16),
        int(stripped[2:4], 16),
        int(stripped[4:6], 16),
    )


def interpolate_point(
    start: tuple[float, float],
    end: tuple[float, float],
    ratio: float,
) -> tuple[float, float]:
    ratio = max(0.0, min(1.0, ratio))
    return (
        start[0] + (end[0] - start[0]) * ratio,
        start[1] + (end[1] - start[1]) * ratio,
    )


class AnimationCanvas(tk.Canvas):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            background="#07111B",
            highlightthickness=1,
            highlightbackground="#203247",
            **kwargs,
        )
        self._trace: SolutionTrace | None = None
        self._reference_points: tuple[tuple[float, float], ...] = ()
        self._ode_function: Callable[[float, float], float] | None = None
        self._phases: tuple[AnimationPhase, ...] = ()
        self._phase_index = 0
        self._phase_progress = 0.0
        self._placeholder = "Ingen animasjon tilgjengelig."
        self._redraw_after_id: str | None = None
        self.bind("<Configure>", self._queue_redraw)

    def set_animation(
        self,
        trace: SolutionTrace,
        reference_points: tuple[tuple[float, float], ...],
        ode_function: Callable[[float, float], float] | None,
        phases: tuple[AnimationPhase, ...],
        phase_index: int,
        phase_progress: float,
    ) -> None:
        self._trace = trace
        self._reference_points = reference_points
        self._ode_function = ode_function
        self._phases = phases
        self._phase_index = phase_index
        self._phase_progress = phase_progress
        self._queue_redraw()

    def clear(self, message: str) -> None:
        self._trace = None
        self._reference_points = ()
        self._ode_function = None
        self._phases = ()
        self._phase_index = 0
        self._phase_progress = 0.0
        self._placeholder = message
        self._queue_redraw()

    def _queue_redraw(self, *_args) -> None:
        if self._redraw_after_id is not None:
            self.after_cancel(self._redraw_after_id)
        self._redraw_after_id = self.after(10, self._redraw)

    def _redraw(self) -> None:
        self._redraw_after_id = None
        self.delete("all")

        width = max(self.winfo_width(), int(self.cget("width")))
        height = max(self.winfo_height(), int(self.cget("height")))
        if width < 240 or height < 200:
            return

        if self._trace is None or not self._phases:
            self._draw_placeholder(width, height)
            return

        trace = self._trace
        phase = self._phases[min(self._phase_index, len(self._phases) - 1)]
        step = trace.steps[phase.step_index]
        method_color = trace.method.color
        halo_color = blend_hex(method_color, "#FFFFFF", 0.45)
        backdrop = "#07111B"

        plot_left = 78
        plot_top = 48
        plot_right = width - 32
        plot_bottom = height - 42

        all_points = list(self._reference_points) + list(zip(trace.ts, trace.ys, strict=True))
        for step_record in trace.steps:
            for stage in step_record.stage_samples:
                all_points.append((stage.t, stage.y))
        x_values = [point[0] for point in all_points]
        y_values = [point[1] for point in all_points]
        x_min, x_max = self._resolve_range(x_values)
        y_min, y_max = self._resolve_range(y_values)

        self._draw_background(width, height, plot_left, plot_top, plot_right, plot_bottom)
        self._draw_grid(plot_left, plot_top, plot_right, plot_bottom, x_min, x_max, y_min, y_max)

        def to_screen(x_value: float, y_value: float) -> tuple[float, float]:
            x_ratio = (x_value - x_min) / (x_max - x_min)
            y_ratio = (y_value - y_min) / (y_max - y_min)
            return (
                plot_left + x_ratio * (plot_right - plot_left),
                plot_bottom - y_ratio * (plot_bottom - plot_top),
            )

        if self._ode_function is not None:
            self._draw_slope_field(
                self._ode_function,
                plot_left,
                plot_top,
                plot_right,
                plot_bottom,
                x_min,
                x_max,
                y_min,
                y_max,
                backdrop,
            )

        if self._reference_points:
            self._draw_polyline(
                tuple(to_screen(x, y) for x, y in self._reference_points),
                color="#E9F1FF",
                width=2,
                dash=(5, 4),
            )

        full_trace_points = tuple(to_screen(x, y) for x, y in zip(trace.ts, trace.ys, strict=True))
        self._draw_polyline(
            full_trace_points,
            color=blend_hex(method_color, backdrop, 0.72),
            width=2,
            dash=(3, 4),
        )

        completed_path_points = [
            (trace.ts[index], trace.ys[index])
            for index in range(step.index + 1)
        ]
        if phase.kind == "combine":
            current_point = interpolate_point(
                (step.t, step.y),
                (step.t_next, step.y_next),
                self._phase_progress,
            )
            completed_path_points.append(current_point)
        glow_points = tuple(to_screen(x, y) for x, y in completed_path_points)
        self._draw_glow_polyline(glow_points, method_color, halo_color)

        self._draw_nodes(trace, step, phase, to_screen, backdrop)
        self._draw_stage_guides(step, phase, to_screen, method_color, halo_color, backdrop)
        self._draw_titles(trace, phase, width, plot_left, plot_top, plot_right)

    def _draw_placeholder(self, width: int, height: int) -> None:
        self._draw_background(width, height, 24, 24, width - 24, height - 24)
        self.create_text(
            width / 2,
            height / 2,
            text=self._placeholder,
            fill="#A9BCD0",
            font=("Helvetica", 14),
        )

    def _draw_background(
        self,
        width: int,
        height: int,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
    ) -> None:
        bands = (
            "#07111B",
            "#0A1622",
            "#0D1A29",
            "#102032",
            "#14283B",
        )
        band_height = height / len(bands)
        for index, color in enumerate(bands):
            self.create_rectangle(
                0,
                index * band_height,
                width,
                (index + 1) * band_height,
                fill=color,
                outline=color,
            )

        self.create_rectangle(
            plot_left,
            plot_top,
            plot_right,
            plot_bottom,
            fill="#0A1724",
            outline="#203247",
            width=1,
        )
        self.create_rectangle(
            plot_left + 12,
            plot_top + 12,
            plot_right - 12,
            plot_bottom - 12,
            outline="#152435",
        )

    def _draw_grid(
        self,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        for tick_index in range(6):
            x_ratio = tick_index / 5
            y_ratio = tick_index / 5
            x_screen = plot_left + x_ratio * (plot_right - plot_left)
            y_screen = plot_bottom - y_ratio * (plot_bottom - plot_top)
            self.create_line(x_screen, plot_top, x_screen, plot_bottom, fill="#10283A")
            self.create_line(plot_left, y_screen, plot_right, y_screen, fill="#10283A")

            self.create_text(
                x_screen,
                plot_bottom + 18,
                text=f"{x_min + x_ratio * (x_max - x_min):.3g}",
                fill="#8BA3BB",
                font=("Helvetica", 10),
            )
            self.create_text(
                plot_left - 12,
                y_screen,
                text=f"{y_min + y_ratio * (y_max - y_min):.3g}",
                fill="#8BA3BB",
                font=("Helvetica", 10),
                anchor="e",
            )

    def _draw_slope_field(
        self,
        function: Callable[[float, float], float],
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        backdrop: str,
    ) -> None:
        x_scale = (plot_right - plot_left) / (x_max - x_min)
        y_scale = (plot_bottom - plot_top) / (y_max - y_min)
        field_color = blend_hex("#6FB3D2", backdrop, 0.82)

        def to_screen(x_value: float, y_value: float) -> tuple[float, float]:
            x_ratio = (x_value - x_min) / (x_max - x_min)
            y_ratio = (y_value - y_min) / (y_max - y_min)
            return (
                plot_left + x_ratio * (plot_right - plot_left),
                plot_bottom - y_ratio * (plot_bottom - plot_top),
            )

        for column in range(20):
            x_value = x_min + (column + 0.5) * (x_max - x_min) / 20
            for row in range(14):
                y_value = y_min + (row + 0.5) * (y_max - y_min) / 14
                try:
                    slope = float(function(x_value, y_value))
                except Exception:
                    continue
                vx = x_scale
                vy = -slope * y_scale
                norm = math.hypot(vx, vy)
                if not math.isfinite(norm) or norm == 0.0:
                    continue
                dx = 9.0 * vx / norm
                dy = 9.0 * vy / norm
                center_x, center_y = to_screen(x_value, y_value)
                self.create_line(
                    center_x - dx,
                    center_y - dy,
                    center_x + dx,
                    center_y + dy,
                    fill=field_color,
                    width=1,
                )

    def _draw_polyline(
        self,
        points: tuple[tuple[float, float], ...],
        color: str,
        width: int,
        dash: tuple[int, ...] = (),
    ) -> None:
        if len(points) < 2:
            return
        flattened = [value for point in points for value in point]
        self.create_line(
            *flattened,
            fill=color,
            width=width,
            dash=dash if dash else None,
            smooth=False,
        )

    def _draw_glow_polyline(
        self,
        points: tuple[tuple[float, float], ...],
        color: str,
        halo_color: str,
    ) -> None:
        if len(points) < 2:
            return
        flattened = [value for point in points for value in point]
        self.create_line(*flattened, fill=blend_hex(halo_color, "#07111B", 0.55), width=10)
        self.create_line(*flattened, fill=blend_hex(halo_color, "#07111B", 0.25), width=6)
        self.create_line(*flattened, fill=color, width=3)

    def _draw_nodes(self, trace: SolutionTrace, step: StepRecord, phase: AnimationPhase, to_screen, backdrop: str) -> None:
        past_node_color = blend_hex(trace.method.color, backdrop, 0.35)
        future_node_color = blend_hex(trace.method.color, backdrop, 0.78)

        for index, (t_value, y_value) in enumerate(zip(trace.ts, trace.ys, strict=True)):
            x_screen, y_screen = to_screen(t_value, y_value)
            if index <= step.index:
                radius = 3 if index < step.index else 4
                self.create_oval(
                    x_screen - radius,
                    y_screen - radius,
                    x_screen + radius,
                    y_screen + radius,
                    fill=past_node_color,
                    outline="",
                )
            else:
                radius = 2
                self.create_oval(
                    x_screen - radius,
                    y_screen - radius,
                    x_screen + radius,
                    y_screen + radius,
                    outline=future_node_color,
                )

        if phase.kind == "combine":
            active = interpolate_point((step.t, step.y), (step.t_next, step.y_next), self._phase_progress)
            self._draw_orb(to_screen(*active), trace.method.color, 7)

    def _draw_stage_guides(
        self,
        step: StepRecord,
        phase: AnimationPhase,
        to_screen,
        method_color: str,
        halo_color: str,
        backdrop: str,
    ) -> None:
        start_point = (step.t, step.y)
        end_point = (step.t_next, step.y_next)
        start_screen = to_screen(*start_point)
        end_screen = to_screen(*end_point)

        self.create_line(
            start_screen[0],
            start_screen[1],
            end_screen[0],
            end_screen[1],
            fill=blend_hex(method_color, backdrop, 0.55),
            width=2,
            dash=(5, 5),
        )

        all_stages_visible = phase.kind == "combine"
        for stage_index, stage in enumerate(step.stage_samples):
            stage_point = (stage.t, stage.y)
            stage_screen = to_screen(*stage_point)
            tangent_color = blend_hex(method_color, backdrop, 0.25)
            self._draw_tangent(stage_point, stage.slope, step.h, to_screen, tangent_color, width=1)

            label_fill = blend_hex("#FFFFFF", backdrop, 0.12)
            if all_stages_visible or stage_index < (phase.stage_index or 0):
                self.create_oval(
                    stage_screen[0] - 4,
                    stage_screen[1] - 4,
                    stage_screen[0] + 4,
                    stage_screen[1] + 4,
                    fill=blend_hex(method_color, "#FFFFFF", 0.18),
                    outline="",
                )
            else:
                self.create_oval(
                    stage_screen[0] - 4,
                    stage_screen[1] - 4,
                    stage_screen[0] + 4,
                    stage_screen[1] + 4,
                    outline=blend_hex(method_color, backdrop, 0.25),
                )
            self.create_text(
                stage_screen[0] + 10,
                stage_screen[1] - 10,
                text=f"k{stage.stage_number}",
                fill=label_fill,
                font=("Helvetica", 10, "bold"),
                anchor="sw",
            )

        if phase.kind == "stage" and phase.stage_index is not None:
            active_stage = step.stage_samples[phase.stage_index]
            anchor_point = start_point if phase.stage_index == 0 else (
                step.stage_samples[phase.stage_index - 1].t,
                step.stage_samples[phase.stage_index - 1].y,
            )
            moving_point = interpolate_point(anchor_point, (active_stage.t, active_stage.y), self._phase_progress)
            anchor_screen = to_screen(*anchor_point)
            moving_screen = to_screen(*moving_point)
            self.create_line(
                anchor_screen[0],
                anchor_screen[1],
                moving_screen[0],
                moving_screen[1],
                fill=blend_hex(method_color, backdrop, 0.1),
                width=3,
            )
            self._draw_orb(moving_screen, method_color, 8)
            if self._phase_progress > 0.2:
                tangent_progress = min((self._phase_progress - 0.2) / 0.8, 1.0)
                self._draw_tangent(
                    (active_stage.t, active_stage.y),
                    active_stage.slope,
                    step.h * tangent_progress,
                    to_screen,
                    halo_color,
                    width=3,
                )
        else:
            for stage in step.stage_samples:
                self._draw_tangent(
                    (stage.t, stage.y),
                    stage.slope,
                    step.h,
                    to_screen,
                    halo_color,
                    width=2,
                )
            self._draw_orb(end_screen, method_color, 8)

        self._draw_orb(start_screen, "#FFFFFF", 5)

    def _draw_tangent(
        self,
        point: tuple[float, float],
        slope: float,
        local_h: float,
        to_screen,
        color: str,
        width: int,
    ) -> None:
        delta_t = 0.22 * max(local_h, 1e-9)
        left = (point[0] - delta_t, point[1] - slope * delta_t)
        right = (point[0] + delta_t, point[1] + slope * delta_t)
        left_screen = to_screen(*left)
        right_screen = to_screen(*right)
        self.create_line(
            left_screen[0],
            left_screen[1],
            right_screen[0],
            right_screen[1],
            fill=color,
            width=width,
        )

    def _draw_orb(self, position: tuple[float, float], color: str, radius: int) -> None:
        halo_outer = blend_hex(color, "#07111B", 0.55)
        halo_inner = blend_hex(color, "#07111B", 0.25)
        x_screen, y_screen = position
        self.create_oval(
            x_screen - radius - 8,
            y_screen - radius - 8,
            x_screen + radius + 8,
            y_screen + radius + 8,
            fill=halo_outer,
            outline="",
        )
        self.create_oval(
            x_screen - radius - 4,
            y_screen - radius - 4,
            x_screen + radius + 4,
            y_screen + radius + 4,
            fill=halo_inner,
            outline="",
        )
        self.create_oval(
            x_screen - radius,
            y_screen - radius,
            x_screen + radius,
            y_screen + radius,
            fill=color,
            outline="#FFFFFF",
            width=1,
        )

    def _draw_titles(
        self,
        trace: SolutionTrace,
        phase: AnimationPhase,
        width: int,
        plot_left: int,
        plot_top: int,
        plot_right: int,
    ) -> None:
        step_total = len(trace.steps)
        self.create_text(
            width / 2,
            22,
            text=f"{trace.method.name}: animert Runge-Kutta-flyt",
            fill="#F3F8FF",
            font=("Helvetica", 15, "bold"),
        )
        self.create_text(
            plot_left,
            plot_top - 20,
            text=f"{phase.title}   |   steg {phase.step_index + 1}/{step_total}",
            fill="#B8CCE0",
            font=("Helvetica", 11),
            anchor="w",
        )
        self.create_text(
            plot_right,
            plot_top - 20,
            text="Lys kule = aktiv beregning, stiplet linje = faktisk stegretning",
            fill="#7F96AE",
            font=("Helvetica", 10),
            anchor="e",
        )

    @staticmethod
    def _resolve_range(values: list[float]) -> tuple[float, float]:
        lower = min(values)
        upper = max(values)
        if math.isclose(lower, upper):
            padding = 1.0 if math.isclose(lower, 0.0) else abs(lower) * 0.25
            return (lower - padding, upper + padding)
        padding = (upper - lower) * 0.12
        return (lower - padding, upper + padding)


__all__ = [
    "AnimationCanvas",
    "AnimationPhase",
    "blend_hex",
    "build_animation_script",
    "interpolate_point",
]
