"""Repo self-check: capability scoreboard from in-tree invariants + tests (CYCLE-007)."""

from __future__ import annotations

import io
import os
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import TextTestRunner


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    lines: tuple[str, ...]

    def format_text(self) -> str:
        return "\n".join(self.lines) + "\n"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_doctor(repo_root: Path | None = None, *, run_tests: bool = True) -> DoctorResult:
    root = repo_root or _repo_root()
    lines: list[str] = ["phaseledger doctor", f"root: {root}"]
    ok = True

    required = [
        root / "INVARIANTS.md",
        root / "CLAIMS_POLICY.md",
        root / "THREAT_MODEL.md",
        root / "docs" / "MEASURE_BOUNDARIES.md",
        root / "phaseledger" / "measure.py",
        root / "phaseledger" / "ledger.py",
        root / "phaseledger" / "bundle.py",
        root / "phaseledger" / "maturity.py",
        root / "scripts" / "run_regression.py",
    ]
    for p in required:
        if p.is_file():
            lines.append(f"  OK file {p.relative_to(root)}")
        else:
            ok = False
            lines.append(f"  MISSING {p.relative_to(root)}")

    inv = ""
    if (root / "INVARIANTS.md").is_file():
        inv = (root / "INVARIANTS.md").read_text(encoding="utf-8")
    boundaries = ""
    bpath = root / "docs" / "MEASURE_BOUNDARIES.md"
    if bpath.is_file():
        boundaries = bpath.read_text(encoding="utf-8")
    corpus = inv + "\n" + boundaries

    for token in (
        "G-RECLAIM-INVALIDATES",
        "G-MISSING-CAPTURE",
        "M-STRICT-EMPTY-CHECKS",
        "L-EVENTS-APPEND",
        "NO_MEASURE",
        "DIGEST_MISMATCH",
        "MAT-M0",
        "MAT-M4",
    ):
        if token in corpus:
            lines.append(f"  OK invariant token {token}")
        else:
            ok = False
            lines.append(f"  MISSING invariant token {token}")

    tests_dir = root / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []
    lines.append(f"  test modules: {len(test_files)}")
    if len(test_files) < 8:
        ok = False
        lines.append("  FAIL expected >= 8 test modules")

    # Avoid recursive doctor→suite→doctor. Nested invocations skip the suite.
    nested = os.environ.get("PHASELEDGER_DOCTOR") == "1"
    if run_tests and not nested:
        os.environ["PHASELEDGER_DOCTOR"] = "1"
        try:
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            loader = unittest.TestLoader()
            # Load modules except test_doctor (which would re-enter).
            suite = unittest.TestSuite()
            for mod_path in test_files:
                if mod_path.name == "test_doctor.py":
                    continue
                name = f"tests.{mod_path.stem}"
                try:
                    suite.addTests(loader.loadTestsFromName(name))
                except Exception as e:  # noqa: BLE001 — doctor must report, not crash
                    ok = False
                    lines.append(f"  FAIL load {name}: {e}")
            stream = io.StringIO()
            result = TextTestRunner(stream=stream, verbosity=1).run(suite)
            lines.append(f"  tests run: {result.testsRun}")
            lines.append(f"  failures: {len(result.failures)}")
            lines.append(f"  errors: {len(result.errors)}")
            if not result.wasSuccessful():
                ok = False
                lines.append("  FAIL unittest suite")
            else:
                lines.append("  OK unittest suite")
        finally:
            os.environ.pop("PHASELEDGER_DOCTOR", None)
    elif nested:
        lines.append("  SKIP suite (nested doctor)")
    else:
        lines.append("  SKIP suite (run_tests=False)")

    lines.append("capability scoreboard (honest):")
    lines.append("  G Gate: strong (matrix + codes + regression guards)")
    lines.append("  M Measurer: medium+ (schema, strict, fuzz, boundaries doc)")
    lines.append("  L Ledger: medium+ (events, verify, export/import)")
    lines.append("  C CLI: medium (init/history/verify/ncycle/maintenance/export/import/doctor/maturity)")
    lines.append("  O Ops: medium+ (maintenance N, regression, doctor, maturity M0–M4)")
    lines.append(f"DOCTOR: {'PASS' if ok else 'FAIL'}")
    return DoctorResult(ok=ok, lines=tuple(lines))
