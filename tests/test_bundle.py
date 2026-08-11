"""Export/import ledger bundle (CYCLE-006)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phaseledger.bundle import export_bundle, import_bundle
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


class TestBundle(unittest.TestCase):
    def test_export_import_roundtrip_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            bundle = Path(tmp) / "bundle.json"
            ledger = PhaseLedger.open(src)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, f"{phase}-c")
                ledger.record_measure(phase, _pass(phase, f"{phase}-c"))
                ledger.advance(phase)
            export_bundle(src, bundle)
            self.assertTrue(bundle.is_file())
            imported = import_bundle(bundle, dest)
            self.assertTrue(imported.verify().ok)
            for phase in ("plan", "implement", "test"):
                self.assertTrue(imported.states[phase].advanced)

    def test_export_refuses_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bad"
            ledger = PhaseLedger.open(root)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            (root / "measures" / "plan-latest.json").unlink()
            with self.assertRaises(ValueError) as ctx:
                export_bundle(root, Path(tmp) / "out.json")
            self.assertIn("verify", str(ctx.exception).lower())

    def test_import_refuses_nonempty_dest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "noise.txt").write_text("x", encoding="utf-8")
            ledger = PhaseLedger.open(src)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            bundle = Path(tmp) / "b.json"
            export_bundle(src, bundle)
            with self.assertRaises(ValueError):
                import_bundle(bundle, dest)

    def test_cli_export_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "src")
            dest = str(Path(tmp) / "dest")
            bundle = str(Path(tmp) / "b.json")
            main(["init", "--ledger", src])
            ledger = PhaseLedger.open(src)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, phase)
                ledger.record_measure(phase, _pass(phase, phase))
                ledger.advance(phase)
            self.assertEqual(main(["export", "--ledger", src, "--out", bundle]), 0)
            self.assertEqual(main(["import", "--bundle", bundle, "--ledger", dest]), 0)
            self.assertTrue(PhaseLedger.open(dest).verify().ok)


if __name__ == "__main__":
    unittest.main()
