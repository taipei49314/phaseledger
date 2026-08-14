"""M0–M4 maturity evidence for this checkout. Declarations are not evidence."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .codes import ADVANCE_CODES, ADVANCE_SUCCESS, MEASURE_VERDICTS
from .doctor import run_doctor
from .ledger import AdvanceError, PhaseLedger
from .measure import VERDICTS, measure

REQUIRED_DOC_PHRASES = {
    "CLAIMS_POLICY.md": (
        "never reports VERIFIED, SECURE, PRODUCTION_READY, AUDITED, or INDEPENDENT",
        "VERIFY PASS is local file integrity, not Unasked VERIFIED",
        "A green doctor or maturity run is evidence about this checkout",
    ),
    "THREAT_MODEL.md": (
        "Ledger directories are operator-trusted storage",
        "Host user can rewrite ledger.json and captures",
        "digests are not a cryptographic attestation chain",
        "One operator can fabricate a complete PASS pipeline",
    ),
    "INVARIANTS.md": (
        "Missing observation is never PASS",
        "verify is local integrity, not third-party audit",
    ),
}

FORBIDDEN_VERDICTS = (
    "VERIFIED",
    "SECURE",
    "PRODUCTION_READY",
    "AUDITED",
    "INDEPENDENT",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _pass_obs(phase: str, claim: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "checks": [{"name": "ok", "passed": True}],
        "schema_version": 1,
    }


def _m0() -> tuple[bool, str]:
    root = repo_root()
    doctor = run_doctor(root, run_tests=False)
    fixtures_ok = (root / "fixtures" / "complete.json").is_file() and (
        root / "fixtures" / "incomplete.json"
    ).is_file()
    vocab_ok = tuple(VERDICTS) == MEASURE_VERDICTS == ("PASS", "FAIL", "UNKNOWN", "INCOMPLETE")
    ok = doctor.ok and fixtures_ok and vocab_ok
    return ok, "closed verdict vocab + required fixtures + doctor structural PASS"


def _m1() -> tuple[bool, str]:
    root = repo_root()
    raw = json.loads((root / "fixtures" / "incomplete.json").read_text(encoding="utf-8"))
    result = measure(raw)
    if result.verdict != "INCOMPLETE":
        return False, f"incomplete fixture verdict is {result.verdict!r}, not INCOMPLETE"
    with tempfile.TemporaryDirectory() as tmp:
        ledger = PhaseLedger.open(tmp)
        ledger.record_claim("plan", str(raw.get("claim") or "incomplete"))
        ledger.record_measure("plan", raw)
        try:
            ledger.advance("plan")
        except AdvanceError as e:
            if e.code != "NON_PASS_MEASURE":
                return False, f"incomplete advance refused with {e.code}, not NON_PASS_MEASURE"
        else:
            return False, "incomplete measure authorized advance"
    return True, "incomplete fixture is INCOMPLETE and cannot authorize advance"


def _m2() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        ledger = PhaseLedger.open(tmp)
        for phase in ledger.phases:
            ledger.record_claim(phase, f"{phase}-v1")
            ledger.record_measure(phase, _pass_obs(phase, f"{phase}-v1"))
            ledger.advance(phase)
        if not all(ledger.states[p].advanced for p in ledger.phases):
            return False, "could not establish a full ADVANCED pipeline"
        ledger.record_claim("plan", "plan-v2-changed")
        later_clear = all(
            (not ledger.states[p].advanced) and ledger.states[p].measure_verdict is None
            for p in ("implement", "test")
        )
        if not later_clear or ledger.states["plan"].advanced:
            return False, "re-claim plan did not cascade-invalidate later phases"
        try:
            ledger.advance("plan")
        except AdvanceError as e:
            if e.code != "NO_MEASURE":
                return False, f"re-claim plan advance refused with {e.code}, not NO_MEASURE"
        else:
            return False, "re-claim plan still authorized advance"
    return True, "re-claim plan cascade-invalidates later phases; stale PASS cannot advance"


def _m3() -> tuple[bool, str]:
    expected = (
        "PRIOR_NOT_ADVANCED",
        "NO_MEASURE",
        "NON_PASS_MEASURE",
        "MISSING_CAPTURE",
        "CAPTURE_CORRUPT",
        "CLAIM_MISMATCH",
        "CAPTURE_NON_PASS",
        "DIGEST_MISMATCH",
    )
    if ADVANCE_CODES != expected:
        return False, f"ADVANCE_CODES drifted: {ADVANCE_CODES}"
    if ADVANCE_SUCCESS != "ADVANCED":
        return False, f"ADVANCE_SUCCESS is {ADVANCE_SUCCESS!r}"
    leaked = set(FORBIDDEN_VERDICTS) & set(MEASURE_VERDICTS)
    if leaked:
        return False, f"forbidden verdicts in vocab: {sorted(leaked)}"
    return True, "frozen refuse codes + measure exit vocab; forbidden verdicts absent"


def _m4() -> tuple[bool, str]:
    root = repo_root()
    missing: list[str] = []
    for filename, phrases in REQUIRED_DOC_PHRASES.items():
        path = root / filename
        if not path.is_file():
            missing.append(f"{filename} missing")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                missing.append(f"{filename} missing phrase: {phrase}")
    if missing:
        return False, "; ".join(missing)
    return True, "claims, threat model, and invariants record the local-only residual"


def run_maturity(root: Path | None = None) -> dict[str, Any]:
    # root is accepted for CLI symmetry; checks always read the package checkout.
    _ = root
    levels: dict[str, dict[str, Any]] = {}
    for name, fn in (
        ("M0", _m0),
        ("M1", _m1),
        ("M2", _m2),
        ("M3", _m3),
        ("M4", _m4),
    ):
        ok, detail = fn()
        levels[name] = {"ok": ok, "detail": detail}
    passed = sum(1 for row in levels.values() if row["ok"])
    return {
        "ok": passed == len(levels),
        "passed_levels": passed,
        "total_levels": len(levels),
        "levels": levels,
    }


def format_maturity(report: dict[str, Any]) -> str:
    lines = ["phaseledger maturity"]
    for name, row in report["levels"].items():
        mark = "ok" if row["ok"] else "FAIL"
        lines.append(f"  {mark} {name}: {row['detail']}")
    lines.append(f"maturity: {report['passed_levels']}/{report['total_levels']}")
    lines.append(f"MATURITY: {'PASS' if report['ok'] else 'FAIL'}")
    return "\n".join(lines) + "\n"
