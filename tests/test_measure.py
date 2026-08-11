"""Tests drive the shipped measure() — not a reimplementation."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from phaseledger.measure import REQUIRED_KEYS, measure, observation_digest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class TestMeasureCore(unittest.TestCase):
    def test_complete_fixture_is_pass(self) -> None:
        obs = json.loads((FIXTURES / "complete.json").read_text(encoding="utf-8"))
        r1 = measure(obs)
        r2 = measure(obs)
        self.assertEqual(r1.verdict, "PASS")
        self.assertEqual(r2.verdict, "PASS")
        self.assertEqual(r1.observation_digest, r2.observation_digest)
        self.assertEqual(r1.format_text(), r2.format_text())
        self.assertIn("VERDICT: PASS", r1.format_text())

    def test_incomplete_fixture_is_incomplete(self) -> None:
        obs = json.loads((FIXTURES / "incomplete.json").read_text(encoding="utf-8"))
        result = measure(obs)
        self.assertEqual(result.verdict, "INCOMPLETE")
        self.assertIn("artifact_sha256", result.missing_keys)
        self.assertIn("checks", result.missing_keys)
        # fail-closed: must never report PASS when keys missing
        self.assertNotEqual(result.verdict, "PASS")
        self.assertIn("VERDICT: INCOMPLETE", result.format_text())

    def test_failing_check_is_fail(self) -> None:
        obs = json.loads((FIXTURES / "failing_check.json").read_text(encoding="utf-8"))
        result = measure(obs)
        self.assertEqual(result.verdict, "FAIL")
        self.assertIn("core_tests", result.reason)

    def test_empty_checks_is_unknown(self) -> None:
        obs = json.loads((FIXTURES / "unknown_no_checks.json").read_text(encoding="utf-8"))
        result = measure(obs)
        self.assertEqual(result.verdict, "UNKNOWN")

    def test_artifact_absent_is_fail(self) -> None:
        obs = {
            "phase": "plan",
            "claim": "x",
            "artifact_present": False,
            "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checks": [{"name": "a", "passed": True}],
        }
        self.assertEqual(measure(obs).verdict, "FAIL")

    def test_deterministic_digest(self) -> None:
        obs = json.loads((FIXTURES / "complete.json").read_text(encoding="utf-8"))
        d1 = observation_digest(obs)
        d2 = observation_digest(obs)
        self.assertEqual(d1, d2)
        self.assertEqual(len(d1), 64)
        # notes excluded from digest
        obs2 = dict(obs)
        obs2["notes"] = "noise"
        self.assertEqual(observation_digest(obs2), d1)

    def test_required_keys_documented(self) -> None:
        self.assertIn("phase", REQUIRED_KEYS)
        self.assertIn("checks", REQUIRED_KEYS)

    def test_empty_mapping_incomplete(self) -> None:
        result = measure({})
        self.assertEqual(result.verdict, "INCOMPLETE")
        self.assertEqual(set(result.missing_keys), set(REQUIRED_KEYS))


if __name__ == "__main__":
    unittest.main()
