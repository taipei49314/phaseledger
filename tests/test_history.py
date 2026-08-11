"""Append-only events.jsonl + history CLI (CYCLE-003)."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
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
        "schema_version": 1,
    }


class TestHistory(unittest.TestCase):
    def test_events_append_only_claim_measure_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "A")
            ledger.record_measure("plan", _pass("plan", "A"))
            ledger.advance("plan")
            events = ledger.read_events()
            types = [e["type"] for e in events]
            self.assertEqual(types, ["claim", "measure", "advance"])
            # Append more — prior lines must remain
            ledger.record_claim("plan", "B")
            events2 = ledger.read_events()
            self.assertEqual(events2[0]["type"], "claim")
            self.assertEqual(events2[0]["claim"], "A")
            self.assertEqual(events2[-1]["type"], "claim")
            self.assertEqual(events2[-1]["claim"], "B")
            self.assertGreater(len(events2), len(events))

    def test_history_text_lists_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "hist")
            ledger.record_measure("plan", _pass("plan", "hist"))
            text = ledger.history_text()
            self.assertIn("phaseledger history", text)
            self.assertIn("claim", text)
            self.assertIn("measure", text)
            self.assertIn("hist", text)

    def test_verify_requires_advance_in_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            self.assertTrue(ledger.verify().ok)
            # Truncate events while leaving ledger advanced — integrity fail.
            (root / "events.jsonl").write_text("", encoding="utf-8")
            v = ledger.verify()
            self.assertFalse(v.ok)
            self.assertTrue(any("events.jsonl" in r for r in v.reasons))

    def test_cli_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "cli")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["history", "--ledger", tmp])
            self.assertEqual(code, 0)
            self.assertIn("claim", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
