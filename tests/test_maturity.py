"""Maturity M0–M4 + claims-policy closeout (CYCLE-011)."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phaseledger.cli import main
from phaseledger.codes import MEASURE_VERDICTS
from phaseledger.maturity import FORBIDDEN_VERDICTS, REQUIRED_DOC_PHRASES, format_maturity, run_maturity

ROOT = Path(__file__).resolve().parents[1]


class TestMaturity(unittest.TestCase):
    def test_maturity_all_levels_pass(self) -> None:
        report = run_maturity(ROOT)
        self.assertTrue(report["ok"], format_maturity(report))
        self.assertEqual(report["passed_levels"], 5)
        self.assertEqual(report["total_levels"], 5)
        for name in ("M0", "M1", "M2", "M3", "M4"):
            self.assertTrue(report["levels"][name]["ok"], name)

    def test_cli_maturity_text(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["maturity"])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("MATURITY: PASS", out)
        self.assertIn("maturity: 5/5", out)
        self.assertIn("M0", out)

    def test_cli_maturity_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["maturity", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["total_levels"], 5)

    def test_forbidden_verdicts_absent_from_vocab(self) -> None:
        leaked = set(FORBIDDEN_VERDICTS) & set(MEASURE_VERDICTS)
        self.assertFalse(leaked)

    def test_required_doc_phrases_present(self) -> None:
        for filename, phrases in REQUIRED_DOC_PHRASES.items():
            text = (ROOT / filename).read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, text, msg=f"{filename}: {phrase}")


if __name__ == "__main__":
    unittest.main()
