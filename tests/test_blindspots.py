"""Blind-spot audit: fail-closed error shapes + previously untested edges."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phaseledger.bundle import export_bundle, import_bundle
from phaseledger.cli import main
from phaseledger.ledger import AdvanceError, PhaseLedger
from phaseledger.maintenance import run_maintenance
from phaseledger.measure import measure
from phaseledger.ncycle import run_n_cycles


def _pass(phase: str, claim: str) -> dict:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
        "schema_version": 1,
    }


class TestBlindspots(unittest.TestCase):
    def test_open_corrupt_ledger_is_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            PhaseLedger.open(root)
            (root / "ledger.json").write_text("{bad", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                PhaseLedger.open(root)
            self.assertIn("corrupt", str(ctx.exception).lower())

    def test_open_ledger_states_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            PhaseLedger.open(root)
            (root / "ledger.json").write_text(
                json.dumps({"phases": ["plan"], "states": []}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                PhaseLedger.open(root)
            self.assertIn("states", str(ctx.exception).lower())

    def test_import_missing_ledger_key_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / "b.json"
            b.write_text(json.dumps({"bundle_version": 1}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                import_bundle(b, Path(tmp) / "dest")
            self.assertIn("ledger", str(ctx.exception).lower())
            self.assertFalse((Path(tmp) / "dest").exists())

    def test_export_corrupt_measure_file_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            ledger = PhaseLedger.open(src)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            (src / "measures" / "junk.json").write_text("{notjson", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                export_bundle(src, Path(tmp) / "out.json")
            self.assertIn("corrupt measure", str(ctx.exception).lower())

    def test_import_verify_fail_removes_dest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            ledger = PhaseLedger.open(src)
            ledger.record_claim("plan", "x")
            ledger.record_measure("plan", _pass("plan", "x"))
            ledger.advance("plan")
            bundle = Path(tmp) / "b.json"
            export_bundle(src, bundle)
            data = json.loads(bundle.read_text(encoding="utf-8"))
            data["events_jsonl"] = ""
            bundle.write_text(json.dumps(data), encoding="utf-8")
            dest = Path(tmp) / "dest"
            with self.assertRaises(ValueError) as ctx:
                import_bundle(bundle, dest)
            self.assertIn("verify", str(ctx.exception).lower())
            self.assertFalse(dest.exists())

    def test_import_unsupported_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / "b.json"
            b.write_text(
                json.dumps({"bundle_version": 99, "ledger": {"phases": [], "states": {}}}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                import_bundle(b, Path(tmp) / "d")
            self.assertIn("bundle_version", str(ctx.exception).lower())

    def test_measure_non_mapping_type_error(self) -> None:
        with self.assertRaises(TypeError):
            measure([1, 2, 3])  # type: ignore[arg-type]

    def test_unknown_phase_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                PhaseLedger.open(tmp).record_claim("nope", "x")
            self.assertIn("unknown phase", str(ctx.exception).lower())

    def test_ncycle_count_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_n_cycles(tmp, count=0)

    def test_maintenance_steps_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_maintenance(tmp, steps=0)

    def test_history_corrupt_events_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            (Path(tmp) / "events.jsonl").write_text("not-json\n", encoding="utf-8")
            text = ledger.history_text()
            self.assertIn("ERROR:", text)

    def test_cli_bad_json_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{bad", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                main(["measure", str(p)])
            self.assertIn("valid JSON", str(ctx.exception))

    def test_cli_array_json_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "arr.json"
            p.write_text("[1,2]", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                main(["measure", str(p)])
            self.assertIn("JSON object", str(ctx.exception))

    def test_cli_measure_strict_empty_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "u.json"
            p.write_text(
                json.dumps(
                    {
                        "phase": "plan",
                        "claim": "c",
                        "artifact_present": True,
                        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "checks": [],
                    }
                ),
                encoding="utf-8",
            )
            # non-strict UNKNOWN exit 3; strict FAIL exit 1
            self.assertEqual(main(["measure", str(p)]), 3)
            self.assertEqual(main(["measure", str(p), "--strict"]), 1)

    def test_cli_measure_ledger_requires_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "o.json"
            led = Path(tmp) / "led"
            # no phase key
            p.write_text(
                json.dumps(
                    {
                        "claim": "c",
                        "artifact_present": True,
                        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "checks": [{"name": "ok", "passed": True}],
                    }
                ),
                encoding="utf-8",
            )
            code = main(["measure", str(p), "--ledger", str(led)])
            self.assertEqual(code, 2)
            # Must not create ledger on misuse (fail closed / no side effect).
            self.assertFalse(led.exists())

    def test_empty_claim_cannot_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            ledger.record_claim("plan", "")
            r = ledger.record_measure("plan", _pass("plan", ""))
            self.assertEqual(r.verdict, "FAIL")
            with self.assertRaises(AdvanceError) as ctx:
                ledger.advance("plan")
            self.assertEqual(ctx.exception.code, "NON_PASS_MEASURE")

    def test_events_non_object_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PhaseLedger.open(tmp)
            (Path(tmp) / "events.jsonl").write_text("[1,2,3]\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                ledger.read_events()
            self.assertIn("not an object", str(ctx.exception).lower())

    def test_verify_ordering_violation_detected(self) -> None:
        """Tamper ledger so test is advanced while plan is not."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = PhaseLedger.open(root)
            for phase in ("plan", "implement", "test"):
                ledger.record_claim(phase, phase)
                ledger.record_measure(phase, _pass(phase, phase))
                ledger.advance(phase)
            # Downgrade plan advanced flag after the fact
            data = json.loads((root / "ledger.json").read_text(encoding="utf-8"))
            data["states"]["plan"]["advanced"] = False
            (root / "ledger.json").write_text(json.dumps(data), encoding="utf-8")
            v = PhaseLedger.open(root).verify()
            self.assertFalse(v.ok)
            self.assertTrue(any("prior phase" in r for r in v.reasons))


if __name__ == "__main__":
    unittest.main()
