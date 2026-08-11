"""Structured AdvanceError.code tokens (CYCLE-005)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phaseledger.ledger import AdvanceError, PhaseLedger


def _pass(phase: str, claim: str) -> dict:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
        "schema_version": 1,
    }


class TestRefuseCodes(unittest.TestCase):
    def test_code_no_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "NO_MEASURE")
            self.assertIn("CODE=NO_MEASURE", str(ctx.exception))

    def test_code_prior_not_advanced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_measure("implement", _pass("implement", "i"))
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("implement")
            self.assertEqual(ctx.exception.code, "PRIOR_NOT_ADVANCED")

    def test_code_non_pass_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            obs = _pass("plan", "x")
            obs["artifact_present"] = False
            ledger.record_measure("plan", obs)
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "NON_PASS_MEASURE")

    def test_code_missing_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            (root / "measures" / "plan-latest.json").unlink()
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "MISSING_CAPTURE")

    def test_code_claim_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "A")
            ledger.record_measure("plan", _pass("plan", "A"))
            ledger.states["plan"].claim = "B"
            ledger.save()
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "CLAIM_MISMATCH")

    def test_code_capture_non_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            latest = root / "measures" / "plan-latest.json"
            data = json.loads(latest.read_text(encoding="utf-8"))
            data["result"]["verdict"] = "FAIL"
            latest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "CAPTURE_NON_PASS")

    def test_code_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            latest = root / "measures" / "plan-latest.json"
            data = json.loads(latest.read_text(encoding="utf-8"))
            data["result"]["observation_digest"] = "0" * 64
            latest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "DIGEST_MISMATCH")

    def test_code_capture_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            (root / "measures" / "plan-latest.json").write_text("{bad", encoding="utf-8")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "CAPTURE_CORRUPT")

    def test_success_still_advances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "ok")
            ledger.record_measure("plan", _pass("plan", "ok"))
            st = ledger.advance("plan")
            self.assertTrue(st.advanced)


if __name__ == "__main__":
    unittest.main()
