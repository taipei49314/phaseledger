"""≥10 distinct gate cases on the shipped PhaseLedger path (CYCLE-002)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phaseledger.ledger import AdvanceError, PhaseLedger
from phaseledger.measure import measure


def _pass(phase: str, claim: str) -> dict:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
    }


def _unknown(phase: str, claim: str) -> dict:
    o = _pass(phase, claim)
    o["checks"] = []
    return o


class TestGateMatrix(unittest.TestCase):
    """Each test is one gate variant; names appear in suite log for verification."""

    def test_gate01_no_measure_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("no measure", str(ctx.exception).lower())

    def test_gate02_incomplete_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            r = ledger.record_measure("plan", {"phase": "plan", "claim": "x", "artifact_present": True})
            self.assertEqual(r.verdict, "INCOMPLETE")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("incomplete", str(ctx.exception).lower())

    def test_gate03_fail_verdict_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            obs = _pass("plan", "f")
            obs["artifact_present"] = False
            self.assertEqual(ledger.record_measure("plan", obs).verdict, "FAIL")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("not pass", str(ctx.exception).lower())

    def test_gate04_unknown_verdict_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            self.assertEqual(ledger.record_measure("plan", _unknown("plan", "u")).verdict, "UNKNOWN")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("unknown", str(ctx.exception).lower())

    def test_gate05_reclaim_invalidates_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "A")
            ledger.record_measure("plan", _pass("plan", "A"))
            ledger.advance("plan")
            ledger.record_claim("plan", "B")
            self.assertIsNone(ledger.states["plan"].measure_verdict)
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("no measure", str(ctx.exception).lower())

    def test_gate06_claim_mismatch_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "A")
            ledger.record_measure("plan", _pass("plan", "A"))
            ledger.states["plan"].claim = "B"
            ledger.save()
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("claim", str(ctx.exception).lower())

    def test_gate07_missing_latest_capture_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            (root / "measures" / "plan-latest.json").unlink()
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("missing", str(ctx.exception).lower())

    def test_gate08_out_of_order_implement_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_measure("implement", _pass("implement", "i"))
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("implement")
            self.assertIn("plan", str(ctx.exception).lower())

    def test_gate09_out_of_order_test_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_measure("test", _pass("test", "t"))
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("test")
            self.assertIn("plan", str(ctx.exception).lower())

    def test_gate10_capture_verdict_tamper_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            latest = root / "measures" / "plan-latest.json"
            data = json.loads(latest.read_text(encoding="utf-8"))
            data["result"]["verdict"] = "FAIL"
            latest.write_text(json.dumps(data), encoding="utf-8")
            # state still PASS
            self.assertEqual(ledger.states["plan"].measure_verdict, "PASS")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("capture verdict", str(ctx.exception).lower())

    def test_gate11_remeasure_clears_advanced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "c")
            ledger.record_measure("plan", _pass("plan", "c"))
            ledger.advance("plan")
            self.assertTrue(ledger.states["plan"].advanced)
            ledger.record_measure("plan", _pass("plan", "c"))
            # New measure must invalidate prior advance (cannot stay ADVANCED).
            self.assertFalse(ledger.states["plan"].advanced)
            self.assertIsNone(ledger.states["plan"].advanced_at)

    def test_gate12_pass_then_authorize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "ok")
            r = ledger.record_measure("plan", _pass("plan", "ok"))
            self.assertEqual(r.verdict, measure(_pass("plan", "ok")).verdict)
            st = ledger.advance("plan")
            self.assertTrue(st.advanced)
            self.assertEqual(st.measure_verdict, "PASS")

    def test_regression_guard_reclaim_must_clear_measure_fields(self) -> None:
        """If re-claim stopped clearing measure_verdict, this guard fails."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "A")
            ledger.record_measure("plan", _pass("plan", "A"))
            self.assertEqual(ledger.states["plan"].measure_verdict, "PASS")
            ledger.record_claim("plan", "B")
            st = ledger.states["plan"]
            self.assertIsNone(st.measure_verdict)
            self.assertIsNone(st.measure_digest)
            self.assertIsNone(st.measure_path)
            self.assertFalse(st.advanced)


if __name__ == "__main__":
    unittest.main()
