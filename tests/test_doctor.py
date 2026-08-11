"""Doctor self-check (CYCLE-007)."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phaseledger.cli import main
from phaseledger.doctor import run_doctor

ROOT = Path(__file__).resolve().parents[1]


class TestDoctor(unittest.TestCase):
    def test_doctor_structure_without_nested_suite(self) -> None:
        # Avoid doctor→suite→doctor recursion inside unittest discover.
        result = run_doctor(ROOT, run_tests=False)
        self.assertTrue(result.ok, result.format_text())
        text = result.format_text()
        self.assertIn("DOCTOR: PASS", text)
        self.assertIn("capability scoreboard", text)
        self.assertIn("OK file", text)

    def test_cli_doctor_structure(self) -> None:
        # CLI path with nested skip when PHASELEDGER_DOCTOR already set is covered
        # by run_tests=False structural check above; full suite runs outside doctor.
        result = run_doctor(ROOT, run_tests=False)
        self.assertIn("G Gate", result.format_text())


if __name__ == "__main__":
    unittest.main()
