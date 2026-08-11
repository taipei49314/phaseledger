"""Fixed-seed property/fuzz suite: incomplete observations never yield PASS."""

from __future__ import annotations

import random
import unittest

from phaseledger.measure import REQUIRED_KEYS, measure


class TestMeasureFuzz(unittest.TestCase):
    def test_fuzz_missing_keys_never_pass(self) -> None:
        rng = random.Random(20260811)
        keys = list(REQUIRED_KEYS)
        samples = 200
        incomplete_hits = 0
        for i in range(samples):
            # Drop at least one required key; fill others with noise types.
            drop = rng.choice(keys)
            obs = {}
            for k in keys:
                if k == drop:
                    continue
                kind = rng.randint(0, 4)
                if kind == 0:
                    obs[k] = None
                elif kind == 1:
                    obs[k] = rng.randint(0, 99)
                elif kind == 2:
                    obs[k] = "x" * rng.randint(0, 8)
                elif kind == 3:
                    obs[k] = []
                else:
                    obs[k] = {"nested": True}
            # Sometimes omit more keys
            if rng.random() < 0.3 and len(obs) > 0:
                obs.pop(rng.choice(list(obs.keys())), None)
            result = measure(obs)
            self.assertNotEqual(
                result.verdict,
                "PASS",
                msg=f"sample {i} produced PASS for incomplete obs={obs!r}",
            )
            if result.verdict == "INCOMPLETE":
                incomplete_hits += 1
                self.assertTrue(result.missing_keys)
        # Most pure missing-key samples should be INCOMPLETE; allow some FAIL on type errors when all keys present-ish
        self.assertGreater(incomplete_hits, samples // 4)

    def test_fuzz_empty_and_partial_never_pass(self) -> None:
        rng = random.Random(42)
        for i in range(50):
            obs = {}
            n = rng.randint(0, len(REQUIRED_KEYS) - 1)
            for k in rng.sample(list(REQUIRED_KEYS), n):
                obs[k] = "partial"
            r = measure(obs)
            self.assertNotEqual(r.verdict, "PASS")
            # Advance must never treat INCOMPLETE as authorizing — measure path only here
            if set(REQUIRED_KEYS) - set(obs.keys()):
                self.assertEqual(r.verdict, "INCOMPLETE")

    def test_incomplete_not_advance_authorizing_via_ledger(self) -> None:
        import tempfile

        from phaseledger.ledger import AdvanceError, PhaseLedger

        # Do not drop "phase": record_measure setdefaults phase from the argument.
        droppable = ("claim", "artifact_present", "artifact_sha256", "checks")
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            for i in range(20):
                drop = droppable[i % len(droppable)]
                obs = {
                    "phase": "plan",
                    "claim": f"c{i}",
                    "artifact_present": True,
                    "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "checks": [{"name": "ok", "passed": True}],
                }
                del obs[drop]
                r = ledger.record_measure("plan", obs)
                self.assertNotEqual(r.verdict, "PASS")
                with self.assertRaises(AdvanceError):
                    ledger.advance("plan")


if __name__ == "__main__":
    unittest.main()
