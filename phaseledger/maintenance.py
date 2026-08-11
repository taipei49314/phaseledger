"""Same-ledger maintenance runner: N re-claim→measure→advance passes + verify.

Unlike ncycle (fresh mini dirs), maintenance reuses one ledger and appends history.
Fail-closed on first non-PASS or verify failure.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .ledger import AdvanceError, DEFAULT_PHASES, PhaseLedger
from .measure import measure


def _obs(phase: str, claim: str, step: int) -> dict:
    digest = hashlib.sha256(f"maint:{step}:{phase}:{claim}".encode("utf-8")).hexdigest()
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": digest,
        "checks": [
            {"name": "maintenance_step", "passed": True},
            {"name": "schema_ok", "passed": True},
        ],
        "schema_version": 1,
    }


@dataclass(frozen=True)
class MaintenanceStepResult:
    step: int
    ok: bool
    detail: str


@dataclass(frozen=True)
class MaintenanceResult:
    steps: int
    ok: bool
    results: tuple[MaintenanceStepResult, ...]

    def format_text(self) -> str:
        lines = [
            f"MAINTENANCE: {'PASS' if self.ok else 'FAIL'}",
            f"steps: {self.steps}",
            f"completed_ok: {sum(1 for r in self.results if r.ok)}",
        ]
        for r in self.results:
            st = "OK" if r.ok else "FAIL"
            lines.append(f"  step[{r.step}]: {st} — {r.detail}")
        return "\n".join(lines) + "\n"


def run_maintenance(
    ledger_root: str | Path,
    steps: int = 5,
    phases: tuple[str, ...] = DEFAULT_PHASES,
) -> MaintenanceResult:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    ledger = PhaseLedger.open(ledger_root, phases=phases)
    results: list[MaintenanceStepResult] = []

    for step in range(steps):
        try:
            for phase in phases:
                claim = f"maintenance-step-{step}-{phase}"
                ledger.record_claim(phase, claim)
                obs = _obs(phase, claim, step)
                bare = measure(obs, strict=True)
                rec = ledger.record_measure(phase, obs, strict=True)
                if bare.verdict != rec.verdict or rec.verdict != "PASS":
                    raise AdvanceError(
                        f"step {step} phase {phase}: measure {rec.verdict}"
                    )
                ledger.advance(phase)
            v = ledger.verify()
            if not v.ok:
                raise AdvanceError(f"verify failed at step {step}: {v.reasons}")
            results.append(
                MaintenanceStepResult(
                    step=step,
                    ok=True,
                    detail="phases re-advanced + verify PASS",
                )
            )
        except (AdvanceError, ValueError, OSError, TypeError) as e:
            results.append(MaintenanceStepResult(step=step, ok=False, detail=str(e)))
            return MaintenanceResult(steps=steps, ok=False, results=tuple(results))

    ok = len(results) == steps and all(r.ok for r in results)
    return MaintenanceResult(steps=steps, ok=ok, results=tuple(results))
