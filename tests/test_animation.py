from __future__ import annotations

import unittest

from rk_visualizer.animation import blend_hex, build_animation_script, interpolate_point
from rk_visualizer.methods import get_method
from rk_visualizer.solver import solve_initial_value_problem


class AnimationTests(unittest.TestCase):
    def test_animation_script_has_one_combine_phase_per_step(self) -> None:
        trace = solve_initial_value_problem(
            function=lambda t, y: t + y,
            method=get_method("heun"),
            t0=0.0,
            y0=1.0,
            h=0.25,
            steps=3,
        )
        phases = build_animation_script(trace)

        self.assertEqual(len(phases), 3 * (trace.method.stages + 1))
        self.assertEqual(phases[0].kind, "stage")
        self.assertEqual(phases[2].kind, "combine")
        self.assertIn("y_(n+1)", phases[2].formula)

    def test_interpolate_point_clamps_ratio(self) -> None:
        self.assertEqual(interpolate_point((0.0, 0.0), (2.0, 4.0), -1.0), (0.0, 0.0))
        self.assertEqual(interpolate_point((0.0, 0.0), (2.0, 4.0), 0.5), (1.0, 2.0))
        self.assertEqual(interpolate_point((0.0, 0.0), (2.0, 4.0), 2.0), (2.0, 4.0))

    def test_blend_hex_interpolates_rgb_values(self) -> None:
        self.assertEqual(blend_hex("#000000", "#FFFFFF", 0.5), "#808080")


if __name__ == "__main__":
    unittest.main()
