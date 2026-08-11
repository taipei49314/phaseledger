"""CLI tests invoke the real entry point."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phaseledger.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class TestCLI(unittest.TestCase):
    def test_measure_complete_exit_zero_and_verdict(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["measure", str(FIXTURES / "complete.json")])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("VERDICT: PASS", out)

    def test_measure_incomplete_exit_four(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["measure", str(FIXTURES / "incomplete.json")])
        out = buf.getvalue()
        self.assertEqual(code, 4)
        self.assertIn("VERDICT: INCOMPLETE", out)

    def test_measure_writes_out_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m.txt"
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "measure",
                        str(FIXTURES / "complete.json"),
                        "--out",
                        str(out),
                    ]
                )
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("VERDICT: PASS", text)
            self.assertEqual(text, buf.getvalue())

    def test_ledger_measure_advance_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = str(Path(tmp) / ".phaseledger")
            claim_code = main(
                ["claim", "--ledger", ledger, "--phase", "plan", "--claim", "cli plan"]
            )
            self.assertEqual(claim_code, 0)
            buf = io.StringIO()
            with redirect_stdout(buf):
                mcode = main(
                    [
                        "measure",
                        str(FIXTURES / "complete.json"),
                        "--ledger",
                        ledger,
                        "--phase",
                        "plan",
                    ]
                )
            self.assertEqual(mcode, 0)
            self.assertIn("VERDICT: PASS", buf.getvalue())
            acode = main(["advance", "--ledger", ledger, "--phase", "plan"])
            self.assertEqual(acode, 0)
            sbuf = io.StringIO()
            with redirect_stdout(sbuf):
                scode = main(["status", "--ledger", ledger])
            self.assertEqual(scode, 0)
            status = sbuf.getvalue()
            self.assertIn("plan: ADVANCED", status)
            self.assertIn("measure=PASS", status)


if __name__ == "__main__":
    unittest.main()
