"""Measurer schema_version, strict mode, and boundary cases (CYCLE-003)."""

from __future__ import annotations

import unittest

from phaseledger.measure import measure


def _base(**overrides):
    obs = {
        "phase": "plan",
        "claim": "c",
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
    }
    obs.update(overrides)
    return obs


class TestMeasureSchema(unittest.TestCase):
    def test_schema_version_1_pass(self) -> None:
        r = measure(_base(schema_version=1))
        self.assertEqual(r.verdict, "PASS")
        self.assertEqual(r.schema_version, "1")

    def test_schema_version_string_1_pass(self) -> None:
        r = measure(_base(schema_version="1.0"))
        self.assertEqual(r.verdict, "PASS")

    def test_unsupported_schema_fail(self) -> None:
        r = measure(_base(schema_version=99))
        self.assertEqual(r.verdict, "FAIL")
        self.assertIn("unsupported schema_version", r.reason)

    def test_strict_empty_checks_fail(self) -> None:
        obs = _base(checks=[])
        self.assertEqual(measure(obs).verdict, "UNKNOWN")
        self.assertEqual(measure(obs, strict=True).verdict, "FAIL")
        self.assertIn("strict", measure(obs, strict=True).reason.lower())

    def test_empty_check_name_fail(self) -> None:
        r = measure(_base(checks=[{"name": "  ", "passed": True}]))
        self.assertEqual(r.verdict, "FAIL")
        self.assertIn("name", r.reason)

    def test_whitespace_phase_fail(self) -> None:
        r = measure(_base(phase="   "))
        self.assertEqual(r.verdict, "FAIL")

    def test_deterministic_with_schema(self) -> None:
        obs = _base(schema_version="1")
        a = measure(obs)
        b = measure(obs)
        self.assertEqual(a.format_text(), b.format_text())
        self.assertEqual(a.observation_digest, b.observation_digest)


if __name__ == "__main__":
    unittest.main()
