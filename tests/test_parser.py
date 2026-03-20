from __future__ import annotations

import math
import unittest

from rk_visualizer.parser import ExpressionCompilationError, compile_expression


class ParserTests(unittest.TestCase):
    def test_compiles_expression_with_math_functions(self) -> None:
        function = compile_expression("sin(t) + y**2", ("t", "y"))
        self.assertAlmostEqual(function(math.pi / 2, 2.0), 5.0)

    def test_supports_piecewise_expression(self) -> None:
        function = compile_expression("1 if t < 0 else 2", ("t",))
        self.assertEqual(function(-1.0), 1.0)
        self.assertEqual(function(0.5), 2.0)

    def test_rejects_unknown_name(self) -> None:
        with self.assertRaises(ExpressionCompilationError):
            compile_expression("__import__('os').system('pwd')", ("t", "y"))


if __name__ == "__main__":
    unittest.main()

