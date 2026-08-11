"""Ledger tests: advance only after PASS measure."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phaseledger.ledger import AdvanceError, PhaseLedger
from phaseledger.measure import measure


def _pass_obs(phase: str, claim: str) -> dict:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
    }


class TestPhaseLedger(unittest.TestCase):
    def test_advance_without_measure_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("no measure", str(ctx.exception).lower())

    def test_advance_on_incomplete_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            incomplete = {"phase": "plan", "claim": "x", "artifact_present": True}
            result = ledger.record_measure("plan", incomplete)
            self.assertEqual(result.verdict, "INCOMPLETE")
            with self.assertRaises(AdvanceError):
                ledger.advance("plan")

    def test_pass_then_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "plan claim")
            result = ledger.record_measure("plan", _pass_obs("plan", "plan claim"))
            self.assertEqual(result.verdict, "PASS")
            st = ledger.advance("plan")
            self.assertTrue(st.advanced)
            self.assertEqual(st.measure_verdict, "PASS")
            latest = Path(tmp) / "measures" / "plan-latest.json"
            self.assertTrue(latest.is_file())
            capture = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(capture["result"]["verdict"], "PASS")

    def test_implement_requires_prior_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_measure("implement", _pass_obs("implement", "impl"))
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("implement")
            self.assertIn("plan", str(ctx.exception))

    def test_full_pipeline_plan_implement_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, f"{phase} done")
                r = ledger.record_measure(phase, _pass_obs(phase, f"{phase} done"))
                self.assertEqual(r.verdict, measure(_pass_obs(phase, f"{phase} done")).verdict)
                ledger.advance(phase)
            for phase in ("plan", "implement", "test"):
                self.assertTrue(ledger.states[phase].advanced)

    def test_measure_uses_shipped_measure(self) -> None:
        """record_measure must produce same verdict as bare measure()."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            obs = _pass_obs("plan", "same path")
            bare = measure(obs)
            via_ledger = ledger.record_measure("plan", obs)
            self.assertEqual(bare.verdict, via_ledger.verdict)
            self.assertEqual(bare.observation_digest, via_ledger.observation_digest)

    def test_reclaim_invalidates_prior_measure_for_advance(self) -> None:
        """New claim must not advance on a stale PASS from a previous claim."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "claim A")
            r = ledger.record_measure("plan", _pass_obs("plan", "claim A"))
            self.assertEqual(r.verdict, "PASS")
            st = ledger.advance("plan")
            self.assertTrue(st.advanced)
            # Supersede claim without measuring the new claim.
            ledger.record_claim("plan", "claim B")
            self.assertFalse(ledger.states["plan"].advanced)
            self.assertIsNone(ledger.states["plan"].measure_verdict)
            self.assertEqual(ledger.states["plan"].claim, "claim B")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            msg = str(ctx.exception).lower()
            self.assertIn("no measure", msg)
            # Fresh measure of the new claim is required before advance.
            r2 = ledger.record_measure("plan", _pass_obs("plan", "claim B"))
            self.assertEqual(r2.verdict, "PASS")
            st2 = ledger.advance("plan")
            self.assertTrue(st2.advanced)
            self.assertEqual(st2.claim, "claim B")

    def test_advance_refuses_measure_for_different_claim(self) -> None:
        """Even if measure fields are set, claim mismatch must refuse advance."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "claim A")
            ledger.record_measure("plan", _pass_obs("plan", "claim A"))
            # Simulate a claim update that forgot to clear measure (tamper).
            ledger.states["plan"].claim = "claim B never measured"
            ledger.save()
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertIn("claim", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
