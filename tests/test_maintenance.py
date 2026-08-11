"""Same-ledger maintenance runner + init CLI (CYCLE-004)."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phaseledger.cli import main
from phaseledger.ledger import PhaseLedger
from phaseledger.maintenance import run_maintenance


class TestMaintenance(unittest.TestCase):
    def test_five_maintenance_steps_same_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_maintenance(tmp, steps=5)
            self.assertTrue(result.ok, result.format_text())
            self.assertEqual(result.steps, 5)
            self.assertEqual(len(result.results), 5)
            text = result.format_text()
            self.assertIn("MAINTENANCE: PASS", text)
            self.assertIn("completed_ok: 5", text)
            # History must have grown (append-only across steps).
            events = PhaseLedger.open(tmp).read_events()
            # 5 steps × 3 phases × (claim+measure+advance) = 45 events minimum
            self.assertGreaterEqual(len(events), 45)
            self.assertTrue(PhaseLedger.open(tmp).verify().ok)

    def test_cli_init_and_maintenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = str(Path(tmp) / "led")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["init", "--ledger", ledger])
            self.assertEqual(code, 0)
            self.assertIn("initialized", buf.getvalue())
            self.assertTrue((Path(ledger) / "ledger.json").is_file())
            out = Path(tmp) / "maint.txt"
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                code2 = main(
                    ["maintenance", "--ledger", ledger, "--steps", "3", "--out", str(out)]
                )
            self.assertEqual(code2, 0)
            body = out.read_text(encoding="utf-8")
            self.assertIn("MAINTENANCE: PASS", body)
            self.assertIn("completed_ok: 3", body)


if __name__ == "__main__":
    unittest.main()
