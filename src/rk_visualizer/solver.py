from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeAlias

from .methods import ExplicitRungeKuttaMethod


ODEFunction: TypeAlias = Callable[[float, float], float]


@dataclass(frozen=True)
class StageSample:
    stage_number: int
    t: float
    y: float
    slope: float


@dataclass(frozen=True)
class StepRecord:
    index: int
    t: float
    y: float
    h: float
    stage_samples: tuple[StageSample, ...]
    y_next: float

    @property
    def t_next(self) -> float:
        return self.t + self.h


@dataclass(frozen=True)
class SolutionTrace:
    method: ExplicitRungeKuttaMethod
    ts: tuple[float, ...]
    ys: tuple[float, ...]
    steps: tuple[StepRecord, ...]


def solve_initial_value_problem(
    function: ODEFunction,
    method: ExplicitRungeKuttaMethod,
    t0: float,
    y0: float,
    h: float,
    steps: int,
) -> SolutionTrace:
    if steps < 1:
        raise ValueError("The number of steps must be at least 1.")
    if h <= 0:
        raise ValueError("Step size h must be positive.")

    ts = [float(t0)]
    ys = [float(y0)]
    step_records: list[StepRecord] = []

    for step_index in range(steps):
        t = ts[-1]
        y = ys[-1]
        slopes: list[float] = []
        stage_samples: list[StageSample] = []

        for stage_index, c_i in enumerate(method.c):
            stage_t = t + c_i * h
            stage_y = y + h * sum(
                method.a[stage_index][prev_index] * slopes[prev_index]
                for prev_index in range(stage_index)
            )
            slope = float(function(stage_t, stage_y))
            slopes.append(slope)
            stage_samples.append(
                StageSample(
                    stage_number=stage_index + 1,
                    t=stage_t,
                    y=stage_y,
                    slope=slope,
                )
            )

        y_next = y + h * sum(weight * slope for weight, slope in zip(method.b, slopes))
        step_records.append(
            StepRecord(
                index=step_index,
                t=t,
                y=y,
                h=h,
                stage_samples=tuple(stage_samples),
                y_next=y_next,
            )
        )
        ts.append(t + h)
        ys.append(y_next)

    return SolutionTrace(
        method=method,
        ts=tuple(ts),
        ys=tuple(ys),
        steps=tuple(step_records),
    )


def linear_interpolate(
    xs: tuple[float, ...],
    ys: tuple[float, ...],
    x: float,
) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    left_index = 0
    right_index = len(xs) - 1
    while right_index - left_index > 1:
        middle = (left_index + right_index) // 2
        if xs[middle] <= x:
            left_index = middle
        else:
            right_index = middle

    x_left = xs[left_index]
    x_right = xs[right_index]
    y_left = ys[left_index]
    y_right = ys[right_index]
    weight = (x - x_left) / (x_right - x_left)
    return y_left + weight * (y_right - y_left)


def sample_trace(trace: SolutionTrace, query_points: list[float]) -> list[float]:
    return [linear_interpolate(trace.ts, trace.ys, query) for query in query_points]


def compute_abs_errors(values: list[float], reference: list[float]) -> list[float]:
    return [abs(value - target) for value, target in zip(values, reference, strict=True)]
