from __future__ import annotations

import unittest

from rk_visualizer.webapp import available_method_payloads, build_simulation_payload


class WebAppTests(unittest.TestCase):
    def test_methods_endpoint_payload_contains_rk4(self) -> None:
        methods = available_method_payloads()
        keys = {method["key"] for method in methods}
        self.assertIn("rk4", keys)

    def test_simulation_payload_contains_phases_and_summary(self) -> None:
        payload = build_simulation_payload(
            {
                "function": "y",
                "method": "rk4",
                "t0": 0.0,
                "y0": 1.0,
                "h": 0.1,
                "steps": 5,
                "refinement": 20,
            }
        )
        self.assertEqual(payload["method"]["key"], "rk4")
        self.assertEqual(len(payload["trace"]["steps"]), 5)
        self.assertEqual(payload["phases"][0]["kind"], "stage")
        self.assertEqual(payload["phases"][-1]["kind"], "advance")
        self.assertIn("final_error", payload["summary"])

    def test_simulation_rejects_empty_function(self) -> None:
        with self.assertRaises(ValueError):
            build_simulation_payload({"function": "   ", "method": "rk4"})


if __name__ == "__main__":
    unittest.main()
