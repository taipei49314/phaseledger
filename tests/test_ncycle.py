"""N-cycle runner: 5 mini-cycles via shipped run_n_cycles / CLI."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from phaseledger.cli import main
from phaseledger.ncycle import run_n_cycles


class TestNCycle(unittest.TestCase):
    def test_five_mini_cycles_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_n_cycles(tmp, count=5)
            self.assertTrue(result.ok, result.format_text())
            self.assertEqual(result.count, 5)
            self.assertEqual(len(result.cycles), 5)
            self.assertTrue(all(c.ok for c in result.cycles))
            text = result.format_text()
            self.assertIn("NCYCLE: PASS", text)
            for i in range(5):
                self.assertIn(f"mini-cycle[{i}]: OK", text)

    def test_ncycle_fails_closed_on_bad_measure(self) -> None:
        def bad_obs(phase: str, claim: str, salt: str) -> dict:
            # missing checks + sha → INCOMPLETE → not PASS
            return {"phase": phase, "claim": claim, "artifact_present": True}

        with tempfile.TemporaryDirectory() as tmp:
            result = run_n_cycles(tmp, count=5, observations_for=bad_obs)
            self.assertFalse(result.ok)
            self.assertIn("NCYCLE: FAIL", result.format_text())
            # stopped at first failure
            self.assertEqual(len(result.cycles), 1)
            self.assertFalse(result.cycles[0].ok)

    def test_cli_ncycle_five(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.txt"
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["ncycle", "--dir", str(Path(tmp) / "runs"), "--count", "5", "--out", str(out)])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertEqual(text, buf.getvalue())
            self.assertIn("NCYCLE: PASS", text)
            self.assertIn("completed_ok: 5", text)


if __name__ == "__main__":
    unittest.main()
