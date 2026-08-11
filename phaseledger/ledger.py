"""Phase ledger: claim → measure → advance. Advance only on PASS."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .measure import MeasureResult, measure

DEFAULT_PHASES = ("plan", "implement", "test")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class PhaseState:
    name: str
    advanced: bool = False
    claim: str | None = None
    measure_verdict: str | None = None
    measure_digest: str | None = None
    measure_path: str | None = None
    advanced_at: str | None = None


@dataclass
class PhaseLedger:
    """Filesystem-backed ledger under a directory."""

    root: Path
    phases: tuple[str, ...] = DEFAULT_PHASES
    states: dict[str, PhaseState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        if not self.states:
            self.states = {p: PhaseState(name=p) for p in self.phases}

    @classmethod
    def open(cls, root: str | Path, phases: tuple[str, ...] = DEFAULT_PHASES) -> "PhaseLedger":
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        (root_path / "measures").mkdir(exist_ok=True)
        (root_path / "claims").mkdir(exist_ok=True)
        ledger_path = root_path / "ledger.json"
        if ledger_path.is_file():
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            states = {
                name: PhaseState(**raw)
                for name, raw in data.get("states", {}).items()
            }
            phase_list = tuple(data.get("phases", list(phases)))
            for p in phase_list:
                if p not in states:
                    states[p] = PhaseState(name=p)
            return cls(root=root_path, phases=phase_list, states=states)
        ledger = cls(root=root_path, phases=phases)
        ledger.save()
        return ledger

    def save(self) -> None:
        payload = {
            "phases": list(self.phases),
            "states": {k: asdict(v) for k, v in self.states.items()},
        }
        path = self.root / "ledger.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def record_claim(self, phase: str, claim: str) -> Path:
        """Record a claim. Invalidates any prior measure and advance for the phase.

        A new claim is never trusted until a fresh measure covers it; stale
        PASS verdicts from an earlier claim must not authorize advance.
        """
        self._require_phase(phase)
        claim_path = self.root / "claims" / f"{phase}.json"
        body = {"phase": phase, "claim": claim, "recorded_at": _utc_now()}
        claim_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        st = self.states[phase]
        st.claim = claim
        st.advanced = False
        st.advanced_at = None
        # Invalidate prior measure so advance cannot reuse a stale PASS.
        st.measure_verdict = None
        st.measure_digest = None
        st.measure_path = None
        self.save()
        return claim_path

    def record_measure(self, phase: str, observations: dict[str, Any]) -> MeasureResult:
        """Run measurer, persist capture, update state. Does not advance."""
        self._require_phase(phase)
        obs = dict(observations)
        obs.setdefault("phase", phase)
        result = measure(obs)
        stamp = _utc_now().replace(":", "").replace("+00:00", "Z")
        measure_path = self.root / "measures" / f"{phase}-{stamp}-{result.verdict}.json"
        capture = {
            "recorded_at": _utc_now(),
            "phase": phase,
            "observations": obs,
            "result": result.to_dict(),
        }
        measure_path.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # also write latest pointer for the phase
        latest = self.root / "measures" / f"{phase}-latest.json"
        latest.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        st = self.states[phase]
        st.measure_verdict = result.verdict
        st.measure_digest = result.observation_digest
        st.measure_path = str(measure_path.relative_to(self.root)).replace("\\", "/")
        # a new measure invalidates a prior advance
        st.advanced = False
        st.advanced_at = None
        self.save()
        return result

    def advance(self, phase: str) -> PhaseState:
        """Advance phase only if latest measure is PASS and prior phases advanced.

        Fail-closed: measure must exist, be PASS, and (when a claim is set)
        cover that same claim text — not a superseded claim.
        """
        self._require_phase(phase)
        idx = self.phases.index(phase)
        for prior in self.phases[:idx]:
            if not self.states[prior].advanced:
                raise AdvanceError(
                    f"cannot advance {phase!r}: prior phase {prior!r} is not advanced"
                )
        st = self.states[phase]
        if st.measure_verdict is None:
            raise AdvanceError(
                f"cannot advance {phase!r}: no measure recorded (fail-closed)"
            )
        if st.measure_verdict != "PASS":
            raise AdvanceError(
                f"cannot advance {phase!r}: measure verdict is {st.measure_verdict!r}, not PASS"
            )
        # G-MISSING-CAPTURE: ledger.json PASS is not enough without the capture file.
        latest = self.root / "measures" / f"{phase}-latest.json"
        if not latest.is_file():
            raise AdvanceError(
                f"cannot advance {phase!r}: missing latest measure capture (fail-closed)"
            )
        # G-CLAIM-MATCH: measured claim must match current claim if both set.
        capture = json.loads(latest.read_text(encoding="utf-8"))
        if st.claim is not None:
            measured_claim = capture.get("observations", {}).get("claim")
            if measured_claim is not None and measured_claim != st.claim:
                raise AdvanceError(
                    f"cannot advance {phase!r}: measure covers claim "
                    f"{measured_claim!r} but current claim is {st.claim!r}"
                )
        # Capture must itself record PASS (not only state fields).
        capture_verdict = capture.get("result", {}).get("verdict")
        if capture_verdict != "PASS":
            raise AdvanceError(
                f"cannot advance {phase!r}: latest capture verdict is "
                f"{capture_verdict!r}, not PASS"
            )
        st.advanced = True
        st.advanced_at = _utc_now()
        self.save()
        return st

    def status_text(self) -> str:
        lines = ["phaseledger status", f"root: {self.root}", "phases:"]
        for p in self.phases:
            st = self.states[p]
            adv = "ADVANCED" if st.advanced else "pending"
            ver = st.measure_verdict or "NO_MEASURE"
            lines.append(f"  - {p}: {adv} | measure={ver}")
            if st.measure_path:
                lines.append(f"      capture: {st.measure_path}")
            if st.claim:
                lines.append(f"      claim: {st.claim}")
        return "\n".join(lines) + "\n"

    def _require_phase(self, phase: str) -> None:
        if phase not in self.phases:
            raise ValueError(f"unknown phase {phase!r}; known: {list(self.phases)}")


class AdvanceError(RuntimeError):
    """Raised when phase advance is refused (fail-closed)."""
