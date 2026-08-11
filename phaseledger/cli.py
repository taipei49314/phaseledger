"""CLI for phaseledger: measure, claim, advance, status, verify, ncycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .ledger import AdvanceError, PhaseLedger
from .measure import measure
from .ncycle import run_n_cycles


def _load_json(path: Path) -> dict[str, Any]:
    # utf-8-sig strips a BOM if a Windows editor left one; content is otherwise UTF-8.
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"observation file must be a JSON object: {path}")
    return data


def cmd_measure(args: argparse.Namespace) -> int:
    obs = _load_json(Path(args.observations))
    strict = bool(getattr(args, "strict", False))
    if args.ledger:
        ledger = PhaseLedger.open(args.ledger)
        phase = args.phase or obs.get("phase")
        if not phase:
            print(
                "error: --phase required when --ledger is set and observations lack phase",
                file=sys.stderr,
            )
            return 2
        result = ledger.record_measure(str(phase), obs, strict=strict)
    else:
        result = measure(obs, strict=strict)
    text = result.format_text()
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    # exit codes: PASS=0, FAIL=1, UNKNOWN=3, INCOMPLETE=4
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 3, "INCOMPLETE": 4}.get(result.verdict, 1)


def cmd_claim(args: argparse.Namespace) -> int:
    ledger = PhaseLedger.open(args.ledger)
    path = ledger.record_claim(args.phase, args.claim)
    print(f"claim recorded: {path}")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    ledger = PhaseLedger.open(args.ledger)
    try:
        st = ledger.advance(args.phase)
    except AdvanceError as e:
        print(f"ADVANCE_REFUSED: {e}", file=sys.stderr)
        return 1
    print(f"ADVANCED: {st.name} at {st.advanced_at} (measure={st.measure_verdict})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = PhaseLedger.open(args.ledger)
    sys.stdout.write(ledger.status_text())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    ledger = PhaseLedger.open(args.ledger)
    result = ledger.verify()
    text = result.format_text()
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if result.ok else 1


def cmd_ncycle(args: argparse.Namespace) -> int:
    result = run_n_cycles(args.dir, count=args.count)
    text = result.format_text()
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if result.ok else 1


def cmd_history(args: argparse.Namespace) -> int:
    ledger = PhaseLedger.open(args.ledger)
    text = ledger.history_text()
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if "ERROR:" not in text else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phaseledger",
        description="Local-first phase ledger: measure before advance.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    m = sub.add_parser("measure", help="Run the deterministic measurer on an observation file")
    m.add_argument("observations", help="Path to JSON observation file")
    m.add_argument("--ledger", help="Optional ledger dir to record the measure")
    m.add_argument("--phase", help="Phase name (overrides observations.phase when recording)")
    m.add_argument("--out", help="Write measure text capture to this path")
    m.add_argument(
        "--strict",
        action="store_true",
        help="Strict measure: empty checks are FAIL (not UNKNOWN)",
    )
    m.set_defaults(func=cmd_measure)

    c = sub.add_parser("claim", help="Record a claim for a phase (not trusted until measured)")
    c.add_argument("--ledger", required=True, help="Ledger directory")
    c.add_argument("--phase", required=True, help="Phase name")
    c.add_argument("--claim", required=True, help="Claim text")
    c.set_defaults(func=cmd_claim)

    a = sub.add_parser("advance", help="Advance phase only if latest measure is PASS")
    a.add_argument("--ledger", required=True, help="Ledger directory")
    a.add_argument("--phase", required=True, help="Phase name")
    a.set_defaults(func=cmd_advance)

    s = sub.add_parser("status", help="Show phase ledger status")
    s.add_argument("--ledger", required=True, help="Ledger directory")
    s.set_defaults(func=cmd_status)

    v = sub.add_parser("verify", help="Verify ledger.json vs measure captures (integrity)")
    v.add_argument("--ledger", required=True, help="Ledger directory")
    v.add_argument("--out", help="Write verify text to this path")
    v.set_defaults(func=cmd_verify)

    n = sub.add_parser(
        "ncycle",
        help="Run N sequential mini-cycles (claim→measure→advance×phases); fail-closed",
    )
    n.add_argument(
        "--dir",
        required=True,
        help="Directory to hold mini-0..mini-(N-1) ledgers",
    )
    n.add_argument("--count", type=int, default=5, help="Number of mini-cycles (default 5)")
    n.add_argument("--out", help="Write ncycle report to this path")
    n.set_defaults(func=cmd_ncycle)

    h = sub.add_parser("history", help="Show append-only events.jsonl history")
    h.add_argument("--ledger", required=True, help="Ledger directory")
    h.add_argument("--out", help="Write history text to this path")
    h.set_defaults(func=cmd_history)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
