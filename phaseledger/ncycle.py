"""Sequential mini-cycle runner: N times claim→measure→advance for plan/implement/test.

Fail-closed: first non-PASS measure or refused advance aborts with non-zero status.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .ledger import AdvanceError, DEFAULT_PHASES, PhaseLedger
from .measure import measure


def _pass_observations(phase: str, claim: str, salt: str) -> dict:
    digest = hashlib.sha256(f"{phase}:{claim}:{salt}".encode("utf-8")).hexdigest()
    return {
        "phase": phase,
        "claim": claim,
        "artifact_present": True,
        "artifact_sha256": digest,
        "checks": [
            {"name": "artifact_hash_bound", "passed": True},
            {"name": "mini_cycle_check", "passed": True},
        ],
    }


@dataclass(frozen=True)
class MiniCycleResult:
    index: int
    ok: bool
    detail: str


@dataclass(frozen=True)
class NCycleResult:
    count: int
    ok: bool
    cycles: tuple[MiniCycleResult, ...]

    def format_text(self) -> str:
        lines = [
            f"NCYCLE: {'PASS' if self.ok else 'FAIL'}",
            f"count: {self.count}",
            f"completed_ok: {sum(1 for c in self.cycles if c.ok)}",
        ]
        for c in self.cycles:
            status = "OK" if c.ok else "FAIL"
            lines.append(f"  mini-cycle[{c.index}]: {status} — {c.detail}")
        return "\n".join(lines) + "\n"


def run_n_cycles(
    root: str | Path,
    count: int = 5,
    phases: tuple[str, ...] = DEFAULT_PHASES,
    observations_for: Callable[[str, str, str], dict] | None = None,
) -> NCycleResult:
    """Run ``count`` independent mini-cycles under ``root/mini-N``.

    Each mini-cycle uses a fresh PhaseLedger directory and advances every phase
    only after a PASS measure from the shipped measure path.
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    make_obs = observations_for or _pass_observations
    results: list[MiniCycleResult] = []

    for i in range(count):
        cycle_dir = root_path / f"mini-{i}"
        if cycle_dir.exists():
            # wipe previous attempt for clean sequential runs
            import shutil

            shutil.rmtree(cycle_dir)
        ledger = PhaseLedger.open(cycle_dir, phases=phases)
        try:
            for phase in phases:
                claim = f"mini-cycle-{i}-{phase}"
                ledger.record_claim(phase, claim)
                obs = make_obs(phase, claim, salt=str(i))
                # Prefer ledger.record_measure (shipped path); also assert bare measure agrees.
                bare = measure(obs)
                recorded = ledger.record_measure(phase, obs)
                if bare.verdict != recorded.verdict:
                    raise AdvanceError(
                        f"measure path mismatch bare={bare.verdict} ledger={recorded.verdict}"
                    )
                if recorded.verdict != "PASS":
                    raise AdvanceError(
                        f"mini-cycle {i} phase {phase} measure {recorded.verdict}"
                    )
                ledger.advance(phase)
            # integrity check at end of mini-cycle
            v = ledger.verify()
            if not v.ok:
                raise AdvanceError(f"verify failed after mini-cycle {i}: {v.reasons}")
            results.append(MiniCycleResult(index=i, ok=True, detail="all phases advanced + verify PASS"))
        except (AdvanceError, ValueError, OSError, TypeError) as e:
            results.append(MiniCycleResult(index=i, ok=False, detail=str(e)))
            # fail closed: stop at first failure
            return NCycleResult(count=count, ok=False, cycles=tuple(results))

    ok = len(results) == count and all(c.ok for c in results)
    return NCycleResult(count=count, ok=ok, cycles=tuple(results))
