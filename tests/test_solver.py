from __future__ import annotations

import math
import unittest

from rk_visualizer.methods import get_method
from rk_visualizer.solver import solve_initial_value_problem


class SolverTests(unittest.TestCase):
    def test_rk4_is_accurate_for_exponential_growth(self) -> None:
        trace = solve_initial_value_problem(
            function=lambda _t, y: y,
            method=get_method("rk4"),
            t0=0.0,
            y0=1.0,
            h=0.1,
            steps=10,
        )
        self.assertAlmostEqual(trace.ys[-1], math.e, delta=3e-6)

    def test_stage_count_matches_method(self) -> None:
        trace = solve_initial_value_problem(
            function=lambda t, y: t + y,
            method=get_method("heun"),
            t0=0.0,
            y0=1.0,
            h=0.25,
            steps=2,
        )
        self.assertEqual(len(trace.steps), 2)
        self.assertEqual(len(trace.steps[0].stage_samples), 2)
        self.assertEqual(trace.steps[0].stage_samples[0].stage_number, 1)
        self.assertEqual(trace.steps[0].stage_samples[1].stage_number, 2)

    def test_rejects_non_positive_step_size(self) -> None:
        with self.assertRaises(ValueError):
            solve_initial_value_problem(
                function=lambda t, y: t + y,
                method=get_method("euler"),
                t0=0.0,
                y0=1.0,
                h=0.0,
                steps=3,
            )


if __name__ == "__main__":
    unittest.main()

