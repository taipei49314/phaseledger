"""User-journey regression: re-plan must cascade-invalidate later phases."""

from __future__ import annotations

import tempfile
import unittest

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


class TestUserJourney(unittest.TestCase):
    def test_reclaim_plan_cascades_implement_and_test(self) -> None:
        """User re-plans after full pipeline — implement/test must not stay ADVANCED."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, f"{phase}-v1")
                ledger.record_measure(phase, _pass(phase, f"{phase}-v1"))
                ledger.advance(phase)
            self.assertTrue(all(ledger.states[p].advanced for p in ledger.phases))

            ledger.record_claim("plan", "plan-v2-changed")
            self.assertFalse(ledger.states["plan"].advanced)
            self.assertIsNone(ledger.states["plan"].measure_verdict)
            # Cascade: later phases cleared
            for later in ("implement", "test"):
                self.assertFalse(ledger.states[later].advanced)
                self.assertIsNone(ledger.states[later].measure_verdict)
                self.assertIsNone(ledger.states[later].claim)

            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "NO_MEASURE")

            # After fresh plan measure+advance, implement still blocked
            ledger.record_measure("plan", _pass("plan", "plan-v2-changed"))
            ledger.advance("plan")
            with self.assertRaises(AdvanceError) as ctx2:
                ledger.advance("implement")
            self.assertEqual(ctx2.exception.code, "NO_MEASURE")

    def test_remeasure_plan_cascades_later(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, phase)
                ledger.record_measure(phase, _pass(phase, phase))
                ledger.advance(phase)
            ledger.record_measure("plan", _pass("plan", "plan"))
            self.assertFalse(ledger.states["plan"].advanced)
            self.assertFalse(ledger.states["implement"].advanced)
            self.assertFalse(ledger.states["test"].advanced)


if __name__ == "__main__":
    unittest.main()
