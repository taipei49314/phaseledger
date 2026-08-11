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
        events = root_path / "events.jsonl"
        if not events.is_file():
            events.write_text("", encoding="utf-8")
        ledger_path = root_path / "ledger.json"
        if ledger_path.is_file():
            try:
                data = json.loads(ledger_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"ledger.json corrupt (fail-closed): {e}") from e
            if not isinstance(data, dict):
                raise ValueError("ledger.json must be a JSON object (fail-closed)")
            raw_states = data.get("states", {})
            if not isinstance(raw_states, dict):
                raise ValueError("ledger.json states must be an object (fail-closed)")
            states: dict[str, PhaseState] = {}
            for name, raw in raw_states.items():
                if not isinstance(raw, dict):
                    raise ValueError(
                        f"ledger.json states[{name!r}] must be an object (fail-closed)"
                    )
                try:
                    states[name] = PhaseState(**raw)
                except TypeError as e:
                    raise ValueError(
                        f"ledger.json states[{name!r}] invalid fields (fail-closed): {e}"
                    ) from e
            phase_list = tuple(data.get("phases", list(phases)))
            for p in phase_list:
                if p not in states:
                    states[p] = PhaseState(name=p)
            return cls(root=root_path, phases=phase_list, states=states)
        ledger = cls(root=root_path, phases=phases)
        ledger.save()
        return ledger

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append-only event log (JSONL). Never rewrites prior lines."""
        record = {
            "at": _utc_now(),
            "type": event_type,
            **payload,
        }
        path = self.root / "events.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        path = self.root / "events.jsonl"
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"events.jsonl line {line_no} corrupt: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"events.jsonl line {line_no} is not an object")
            events.append(obj)
        return events

    def history_text(self) -> str:
        lines = ["phaseledger history", f"root: {self.root}", "events:"]
        try:
            events = self.read_events()
        except ValueError as e:
            return f"phaseledger history\nroot: {self.root}\nERROR: {e}\n"
        if not events:
            lines.append("  (none)")
        for i, ev in enumerate(events):
            et = ev.get("type", "?")
            phase = ev.get("phase", "")
            extra = ""
            if et == "claim":
                extra = f" claim={ev.get('claim', '')!r}"
            elif et == "measure":
                extra = f" verdict={ev.get('verdict', '')}"
            elif et == "advance":
                extra = f" advanced_at={ev.get('advanced_at', '')}"
            lines.append(f"  [{i}] {ev.get('at', '')} {et} {phase}{extra}")
        return "\n".join(lines) + "\n"

    def save(self) -> None:
        payload = {
            "phases": list(self.phases),
            "states": {k: asdict(v) for k, v in self.states.items()},
        }
        path = self.root / "ledger.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _clear_phase_progress(self, phase: str, *, clear_claim: bool = False) -> None:
        """Clear measure/advance for a phase (optionally claim text)."""
        st = self.states[phase]
        if clear_claim:
            st.claim = None
        st.advanced = False
        st.advanced_at = None
        st.measure_verdict = None
        st.measure_digest = None
        st.measure_path = None

    def _cascade_invalidate_later_phases(self, phase: str) -> tuple[str, ...]:
        """Invalidate all phases after ``phase`` (process integrity).

        If an earlier phase is re-claimed or re-measured, later ADVANCED phases
        must not remain trusted — they were produced under a superseded plan.
        """
        idx = self.phases.index(phase)
        cleared: list[str] = []
        for later in self.phases[idx + 1 :]:
            st = self.states[later]
            if (
                st.advanced
                or st.measure_verdict is not None
                or st.measure_path is not None
                or st.claim is not None
            ):
                self._clear_phase_progress(later, clear_claim=True)
                cleared.append(later)
        return tuple(cleared)

    def record_claim(self, phase: str, claim: str) -> Path:
        """Record a claim. Invalidates prior measure/advance for this phase and later ones.

        A new claim is never trusted until a fresh measure covers it; stale
        PASS verdicts from an earlier claim must not authorize advance.
        Later phases cascade-clear so a re-plan cannot leave implement/test ADVANCED.
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
        cascaded = self._cascade_invalidate_later_phases(phase)
        self.save()
        self._append_event(
            "claim",
            {"phase": phase, "claim": claim, "cascaded_invalidate": list(cascaded)},
        )
        return claim_path

    def record_measure(
        self,
        phase: str,
        observations: dict[str, Any],
        *,
        strict: bool = False,
    ) -> MeasureResult:
        """Run measurer, persist capture, update state. Does not advance.

        Also cascade-invalidates later phases (same reason as re-claim).
        """
        self._require_phase(phase)
        obs = dict(observations)
        obs.setdefault("phase", phase)
        result = measure(obs, strict=strict)
        stamp = _utc_now().replace(":", "").replace("+00:00", "Z")
        measure_path = self.root / "measures" / f"{phase}-{stamp}-{result.verdict}.json"
        capture = {
            "recorded_at": _utc_now(),
            "phase": phase,
            "observations": obs,
            "result": result.to_dict(),
            "strict": strict,
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
        cascaded = self._cascade_invalidate_later_phases(phase)
        self.save()
        self._append_event(
            "measure",
            {
                "phase": phase,
                "verdict": result.verdict,
                "digest": result.observation_digest,
                "path": st.measure_path,
                "strict": strict,
                "cascaded_invalidate": list(cascaded),
            },
        )
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
                    f"cannot advance {phase!r}: prior phase {prior!r} is not advanced",
                    code="PRIOR_NOT_ADVANCED",
                )
        st = self.states[phase]
        if st.measure_verdict is None:
            raise AdvanceError(
                f"cannot advance {phase!r}: no measure recorded (fail-closed)",
                code="NO_MEASURE",
            )
        if st.measure_verdict != "PASS":
            raise AdvanceError(
                f"cannot advance {phase!r}: measure verdict is {st.measure_verdict!r}, not PASS",
                code="NON_PASS_MEASURE",
            )
        # G-MISSING-CAPTURE: ledger.json PASS is not enough without the capture file.
        latest = self.root / "measures" / f"{phase}-latest.json"
        if not latest.is_file():
            raise AdvanceError(
                f"cannot advance {phase!r}: missing latest measure capture (fail-closed)",
                code="MISSING_CAPTURE",
            )
        try:
            capture = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise AdvanceError(
                f"cannot advance {phase!r}: latest capture corrupt: {e}",
                code="CAPTURE_CORRUPT",
            ) from e
        # G-CLAIM-MATCH: measured claim must match current claim if both set.
        if st.claim is not None:
            measured_claim = capture.get("observations", {}).get("claim")
            if measured_claim is not None and measured_claim != st.claim:
                raise AdvanceError(
                    f"cannot advance {phase!r}: measure covers claim "
                    f"{measured_claim!r} but current claim is {st.claim!r}",
                    code="CLAIM_MISMATCH",
                )
        # Capture must itself record PASS (not only state fields).
        cap_result = capture.get("result") if isinstance(capture, dict) else None
        if not isinstance(cap_result, dict):
            raise AdvanceError(
                f"cannot advance {phase!r}: latest capture missing result object",
                code="CAPTURE_CORRUPT",
            )
        capture_verdict = cap_result.get("verdict")
        if capture_verdict != "PASS":
            raise AdvanceError(
                f"cannot advance {phase!r}: latest capture verdict is "
                f"{capture_verdict!r}, not PASS",
                code="CAPTURE_NON_PASS",
            )
        # Digest in state must match capture (tamper detection).
        cap_digest = cap_result.get("observation_digest")
        if (
            st.measure_digest is not None
            and cap_digest is not None
            and st.measure_digest != cap_digest
        ):
            raise AdvanceError(
                f"cannot advance {phase!r}: state digest != capture digest",
                code="DIGEST_MISMATCH",
            )
        st.advanced = True
        st.advanced_at = _utc_now()
        self.save()
        self._append_event(
            "advance",
            {
                "phase": phase,
                "advanced_at": st.advanced_at,
                "verdict": st.measure_verdict,
                "code": "ADVANCED",
            },
        )
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

    def verify(self) -> "VerifyResult":
        """Re-read ledger.json + latest captures; refuse inconsistent or advanced-without-PASS state.

        Fail-closed: any integrity problem yields verdict FAIL (ok=False).
        Does not trust in-memory objects alone — reloads from disk when present.
        """
        reasons: list[str] = []
        ledger_path = self.root / "ledger.json"
        if not ledger_path.is_file():
            return VerifyResult(ok=False, verdict="FAIL", reasons=("missing ledger.json",))

        try:
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return VerifyResult(ok=False, verdict="FAIL", reasons=(f"ledger.json corrupt: {e}",))

        phases = tuple(data.get("phases", list(self.phases)))
        raw_states = data.get("states", {})
        if not isinstance(raw_states, dict):
            return VerifyResult(ok=False, verdict="FAIL", reasons=("ledger states not an object",))

        for phase in phases:
            st_raw = raw_states.get(phase)
            if not isinstance(st_raw, dict):
                reasons.append(f"{phase}: missing state object")
                continue
            advanced = bool(st_raw.get("advanced"))
            claim = st_raw.get("claim")
            measure_verdict = st_raw.get("measure_verdict")
            measure_digest = st_raw.get("measure_digest")
            latest = self.root / "measures" / f"{phase}-latest.json"

            if measure_verdict is not None and not latest.is_file():
                reasons.append(f"{phase}: measure_verdict set but latest capture missing")
                continue

            if advanced and measure_verdict != "PASS":
                reasons.append(
                    f"{phase}: advanced but measure_verdict is {measure_verdict!r}, not PASS"
                )

            if not latest.is_file():
                if advanced:
                    reasons.append(f"{phase}: advanced but latest capture missing")
                continue

            try:
                capture = json.loads(latest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                reasons.append(f"{phase}: latest capture corrupt: {e}")
                continue

            cap_result = capture.get("result") if isinstance(capture, dict) else None
            if not isinstance(cap_result, dict):
                reasons.append(f"{phase}: latest capture missing result object")
                continue

            cap_verdict = cap_result.get("verdict")
            if measure_verdict is not None and cap_verdict != measure_verdict:
                reasons.append(
                    f"{phase}: state measure_verdict {measure_verdict!r} != capture {cap_verdict!r}"
                )

            cap_digest = cap_result.get("observation_digest")
            if measure_digest is not None and cap_digest is not None and measure_digest != cap_digest:
                reasons.append(f"{phase}: state digest != capture digest")

            obs = capture.get("observations") if isinstance(capture, dict) else None
            if isinstance(obs, dict) and claim is not None:
                measured_claim = obs.get("claim")
                if measured_claim is not None and measured_claim != claim:
                    reasons.append(
                        f"{phase}: claim {claim!r} != measured claim {measured_claim!r}"
                    )

            if advanced and cap_verdict != "PASS":
                reasons.append(f"{phase}: advanced but capture verdict is {cap_verdict!r}")

        # Prior-phase ordering for advanced phases
        for i, phase in enumerate(phases):
            st_raw = raw_states.get(phase) or {}
            if not st_raw.get("advanced"):
                continue
            for prior in phases[:i]:
                prior_raw = raw_states.get(prior) or {}
                if not prior_raw.get("advanced"):
                    reasons.append(
                        f"{phase}: advanced while prior phase {prior!r} is not advanced"
                    )

        # Event log integrity: advanced phases must be recorded in events.jsonl.
        advanced_phases = {
            p
            for p, st_raw in raw_states.items()
            if isinstance(st_raw, dict) and st_raw.get("advanced")
        }
        events_path = self.root / "events.jsonl"
        if advanced_phases:
            if not events_path.is_file():
                reasons.append(
                    f"advanced phases missing from events.jsonl: {sorted(advanced_phases)}"
                )
            else:
                try:
                    events = self.read_events()
                except ValueError as e:
                    reasons.append(str(e))
                else:
                    advanced_in_log = {
                        e.get("phase") for e in events if e.get("type") == "advance"
                    }
                    missing_adv = advanced_phases - advanced_in_log
                    if missing_adv:
                        reasons.append(
                            f"advanced phases missing from events.jsonl: {sorted(missing_adv)}"
                        )
        elif events_path.is_file() and events_path.stat().st_size > 0:
            try:
                self.read_events()
            except ValueError as e:
                reasons.append(str(e))

        if reasons:
            return VerifyResult(ok=False, verdict="FAIL", reasons=tuple(reasons))
        return VerifyResult(ok=True, verdict="PASS", reasons=())

    def verify_text(self) -> str:
        result = self.verify()
        lines = [f"VERIFY: {result.verdict}", f"ok: {str(result.ok).lower()}"]
        if result.reasons:
            lines.append("reasons:")
            for r in result.reasons:
                lines.append(f"  - {r}")
        else:
            lines.append("reasons: (none)")
        return "\n".join(lines) + "\n"

    def _require_phase(self, phase: str) -> None:
        if phase not in self.phases:
            raise ValueError(f"unknown phase {phase!r}; known: {list(self.phases)}")


class AdvanceError(RuntimeError):
    """Raised when phase advance is refused (fail-closed).

    ``code`` is a stable machine-readable token (see INVARIANTS / CYCLE-005).
    """

    def __init__(self, message: str, code: str = "ADVANCE_REFUSED") -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"CODE={self.code} {self.message}"


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of ledger integrity verification."""

    ok: bool
    verdict: str
    reasons: tuple[str, ...] = ()

    def format_text(self) -> str:
        lines = [f"VERIFY: {self.verdict}", f"ok: {str(self.ok).lower()}"]
        if self.reasons:
            lines.append("reasons:")
            for r in self.reasons:
                lines.append(f"  - {r}")
        else:
            lines.append("reasons: (none)")
        return "\n".join(lines) + "\n"
