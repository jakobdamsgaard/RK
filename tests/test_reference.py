from __future__ import annotations

import math
import unittest

from rk_visualizer.reference import build_reference_solution
from rk_visualizer.solver import linear_interpolate


class ReferenceTests(unittest.TestCase):
    def test_dense_reference_matches_exact_solution_closely(self) -> None:
        trace = build_reference_solution(
            function=lambda _t, y: y,
            t0=0.0,
            y0=1.0,
            h=0.2,
            steps=5,
            refinement=25,
        )
        approximation = linear_interpolate(trace.ts, trace.ys, 1.0)
        self.assertAlmostEqual(approximation, math.e, delta=1e-4)


if __name__ == "__main__":
    unittest.main()

