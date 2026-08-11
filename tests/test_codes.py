"""Stable code constants match docs and AdvanceError usage (CYCLE-009)."""

from __future__ import annotations

import unittest
from pathlib import Path

from phaseledger.codes import ADVANCE_CODES, ADVANCE_SUCCESS, MEASURE_VERDICTS
from phaseledger.measure import VERDICTS

ROOT = Path(__file__).resolve().parents[1]


class TestCodes(unittest.TestCase):
    def test_measure_verdicts_match(self) -> None:
        self.assertEqual(tuple(VERDICTS), MEASURE_VERDICTS)

    def test_advance_codes_documented(self) -> None:
        docs = (ROOT / "docs" / "MEASURE_BOUNDARIES.md").read_text(encoding="utf-8")
        for code in ADVANCE_CODES:
            self.assertIn(code, docs, msg=f"{code} missing from boundary docs")
        self.assertIn(ADVANCE_SUCCESS, docs)

    def test_ledger_raises_known_codes_only(self) -> None:
        src = (ROOT / "phaseledger" / "ledger.py").read_text(encoding="utf-8")
        # Every code= in advance path should be known or ADVANCED event.
        import re

        found = set(re.findall(r'code="([A-Z_]+)"', src))
        allowed = set(ADVANCE_CODES) | {ADVANCE_SUCCESS}
        unknown = found - allowed
        self.assertFalse(unknown, msg=f"unknown codes in ledger.py: {unknown}")


if __name__ == "__main__":
    unittest.main()
