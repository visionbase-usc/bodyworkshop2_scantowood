"""English reports preserve geometry values and translate every warning."""
import ast
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from m2w.output import write_report


class ReportTests(unittest.TestCase):
    def test_english_report_and_all_warning_branches(self):
        source = Path(__file__).resolve().parents[1] / "mesh2wood.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        context = dict(warnings=[], warnings_en=[], size=np.array([800, 600, 100]),
                       up="z", spread=12, tool=6, split=[2, 3], loose=["P04a"])
        # Exercise the real warning strings, including branches that a single mesh cannot reach.
        for node in ast.walk(tree):
            if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and isinstance(node.value.func.value, ast.Name)
                    and node.value.func.value.id in ("warnings", "warnings_en")):
                exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), context)
        self.assertEqual(len(context["warnings"]), 8)
        self.assertEqual(len(context["warnings_en"]), 8)
        report = dict(name="sample.stl", size=[800, 600, 100], n_panels=6, n_parts=7,
                      n_sheets=2, sheet=[2440, 1220], thickness=18, n_joints=5,
                      min_angle=45, tool=6, tolerance=0.3, stable=False, order=[2, 1],
                      joints=[dict(early=2, late=1, angle=45, width=18.3, length=120)],
                      warnings=context["warnings"], warnings_en=context["warnings_en"])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "report.md"
            for stable in (False, True):
                report["stable"] = stable
                write_report(report, target, lang="en")
                text = target.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"[\u3040-\u30ff\u3400-\u9fff]")
                self.assertIn("P02 → P01", text)
                self.assertIn("| P02 | P01 | 45° | 18.3 | 120 |", text)
                self.assertIn("Yes:" if stable else "No:", text)
                self.assertIn("Sheet boundary — do not cut", text)
                for warning in report["warnings_en"]:
                    self.assertIn(warning, text)
            write_report(report, target)
            self.assertIn("組裝順序", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
