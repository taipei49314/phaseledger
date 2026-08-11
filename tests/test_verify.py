"""Verify/replay integrity on shipped PhaseLedger.verify()."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phaseledger.cli import main
from phaseledger.ledger import PhaseLedger


def _pass(phase: str, claim: str) -> dict:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
    }


class TestVerify(unittest.TestCase):
    def test_verify_healthy_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, f"{phase}-ok")
                ledger.record_measure(phase, _pass(phase, f"{phase}-ok"))
                ledger.advance(phase)
            v = ledger.verify()
            self.assertTrue(v.ok)
            self.assertEqual(v.verdict, "PASS")
            self.assertIn("VERIFY: PASS", v.format_text())

    def test_verify_corrupt_ledger_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            (root / "ledger.json").write_text("{not-json", encoding="utf-8")
            # open() would raise; verify() must fail-closed on corrupt disk state.
            broken = PhaseLedger(root=root)
            v = broken.verify()
            self.assertFalse(v.ok)
            self.assertEqual(v.verdict, "FAIL")
            self.assertTrue(any("corrupt" in r.lower() or "ledger" in r.lower() for r in v.reasons))

    def test_verify_missing_capture_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            (root / "measures" / "plan-latest.json").unlink()
            v = ledger.verify()
            self.assertFalse(v.ok)
            self.assertEqual(v.verdict, "FAIL")
            self.assertTrue(any("missing" in r.lower() for r in v.reasons))

    def test_verify_restored_after_remeasure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            (root / "measures" / "plan-latest.json").unlink()
            self.assertFalse(ledger.verify().ok)
            # honest re-measure restores capture; re-advance plan
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            v = ledger.verify()
            self.assertTrue(v.ok, v.reasons)
            self.assertEqual(v.verdict, "PASS")

    def test_cli_verify_exit_codes(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["verify", "--ledger", str(root)])
            # empty new ledger is consistent (no measures)
            self.assertEqual(code, 0)
            self.assertIn("VERIFY: PASS", buf.getvalue())
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "y")
            ledger.record_measure("plan", _pass("plan", "y"))
            ledger.advance("plan")
            (root / "measures" / "plan-latest.json").unlink()
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                code2 = main(["verify", "--ledger", str(root)])
            self.assertEqual(code2, 1)
            self.assertIn("VERIFY: FAIL", buf2.getvalue())


if __name__ == "__main__":
    unittest.main()
