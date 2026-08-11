"""Deterministic offline measurer: observations → fail-closed verdict.

Pure core. Same inputs always produce the same MeasureResult.
Missing required observation keys are INCOMPLETE (never PASS).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

VERDICTS = ("PASS", "FAIL", "UNKNOWN", "INCOMPLETE")

# Required observation keys for a complete measure of a phase claim.
REQUIRED_KEYS = (
    "phase",
    "claim",
    "artifact_present",
    "artifact_sha256",
    "checks",
)


@dataclass(frozen=True)
class MeasureResult:
    """Immutable measure output."""

    verdict: str
    phase: str | None
    claim: str | None
    reason: str
    observation_digest: str
    missing_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["missing_keys"] = list(self.missing_keys)
        return d

    def format_text(self) -> str:
        lines = [
            f"VERDICT: {self.verdict}",
            f"phase: {self.phase if self.phase is not None else ''}",
            f"claim: {self.claim if self.claim is not None else ''}",
            f"reason: {self.reason}",
            f"observation_digest: {self.observation_digest}",
        ]
        if self.missing_keys:
            lines.append(f"missing_keys: {','.join(self.missing_keys)}")
        return "\n".join(lines) + "\n"


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def observation_digest(observations: Mapping[str, Any]) -> str:
    """Stable SHA-256 of canonicalized observations (excluding free-form notes)."""
    payload = {k: observations[k] for k in sorted(observations.keys()) if k != "notes"}
    raw = _canonical_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def measure(observations: Mapping[str, Any]) -> MeasureResult:
    """Measure a claim against observations. Deterministic and fail-closed.

    Expected observation schema (all required for PASS/FAIL/UNKNOWN):
      - phase: str
      - claim: str
      - artifact_present: bool
      - artifact_sha256: str (non-empty hex when artifact_present is true)
      - checks: list of {name: str, passed: bool} (may be empty → UNKNOWN)

    Semantics:
      - missing any required key → INCOMPLETE
      - artifact_present is False → FAIL
      - artifact_present True but empty/invalid sha → FAIL
      - any check.passed is False → FAIL
      - no checks provided (empty list) → UNKNOWN
      - all checks passed and artifact ok → PASS
    """
    if not isinstance(observations, Mapping):
        raise TypeError("observations must be a mapping")

    missing = tuple(k for k in REQUIRED_KEYS if k not in observations)
    digest = observation_digest(dict(observations)) if observations else hashlib.sha256(b"{}").hexdigest()

    if missing:
        return MeasureResult(
            verdict="INCOMPLETE",
            phase=_as_str_or_none(observations.get("phase")),
            claim=_as_str_or_none(observations.get("claim")),
            reason="missing required observation keys (fail-closed)",
            observation_digest=digest,
            missing_keys=missing,
        )

    phase = observations["phase"]
    claim = observations["claim"]
    if not isinstance(phase, str) or not phase.strip():
        return MeasureResult(
            verdict="FAIL",
            phase=str(phase) if phase is not None else None,
            claim=str(claim) if claim is not None else None,
            reason="phase must be a non-empty string",
            observation_digest=digest,
        )
    if not isinstance(claim, str) or not claim.strip():
        return MeasureResult(
            verdict="FAIL",
            phase=phase,
            claim=str(claim) if claim is not None else None,
            reason="claim must be a non-empty string",
            observation_digest=digest,
        )

    artifact_present = observations["artifact_present"]
    if not isinstance(artifact_present, bool):
        return MeasureResult(
            verdict="FAIL",
            phase=phase,
            claim=claim,
            reason="artifact_present must be a boolean",
            observation_digest=digest,
        )

    if artifact_present is False:
        return MeasureResult(
            verdict="FAIL",
            phase=phase,
            claim=claim,
            reason="required artifact not present",
            observation_digest=digest,
        )

    sha = observations["artifact_sha256"]
    if not isinstance(sha, str) or not _is_hex_sha256(sha):
        return MeasureResult(
            verdict="FAIL",
            phase=phase,
            claim=claim,
            reason="artifact_sha256 must be a 64-char hex digest when artifact is present",
            observation_digest=digest,
        )

    checks = observations["checks"]
    if not isinstance(checks, list):
        return MeasureResult(
            verdict="FAIL",
            phase=phase,
            claim=claim,
            reason="checks must be a list",
            observation_digest=digest,
        )

    if len(checks) == 0:
        return MeasureResult(
            verdict="UNKNOWN",
            phase=phase,
            claim=claim,
            reason="artifact present but no checks recorded (insufficient evidence)",
            observation_digest=digest,
        )

    for i, item in enumerate(checks):
        if not isinstance(item, Mapping):
            return MeasureResult(
                verdict="FAIL",
                phase=phase,
                claim=claim,
                reason=f"checks[{i}] must be an object with name and passed",
                observation_digest=digest,
            )
        if "name" not in item or "passed" not in item:
            return MeasureResult(
                verdict="FAIL",
                phase=phase,
                claim=claim,
                reason=f"checks[{i}] missing name or passed",
                observation_digest=digest,
            )
        if not isinstance(item["passed"], bool):
            return MeasureResult(
                verdict="FAIL",
                phase=phase,
                claim=claim,
                reason=f"checks[{i}].passed must be a boolean",
                observation_digest=digest,
            )
        if item["passed"] is False:
            name = item.get("name", i)
            return MeasureResult(
                verdict="FAIL",
                phase=phase,
                claim=claim,
                reason=f"check failed: {name}",
                observation_digest=digest,
            )

    return MeasureResult(
        verdict="PASS",
        phase=phase,
        claim=claim,
        reason="all required observations present; all checks passed",
        observation_digest=digest,
    )


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _is_hex_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False
