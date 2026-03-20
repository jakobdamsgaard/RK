from __future__ import annotations

from .solver import ODEFunction
from .methods import get_method
from .solver import SolutionTrace, solve_initial_value_problem


def build_reference_solution(
    function: ODEFunction,
    t0: float,
    y0: float,
    h: float,
    steps: int,
    refinement: int = 40,
) -> SolutionTrace:
    if refinement < 2:
        raise ValueError("Refinement must be at least 2.")

    return solve_initial_value_problem(
        function=function,
        method=get_method("rk4"),
        t0=t0,
        y0=y0,
        h=h / refinement,
        steps=steps * refinement,
    )
