"""Export / import a ledger directory as a portable JSON bundle (CYCLE-006).

Local-first: no network. Import fails closed if verify would fail after restore.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .ledger import PhaseLedger

BUNDLE_VERSION = 1


def export_bundle(ledger_root: str | Path, out_path: str | Path) -> Path:
    """Serialize ledger.json, events.jsonl, claims, and measures into one JSON file."""
    root = Path(ledger_root)
    ledger = PhaseLedger.open(root)
    v = ledger.verify()
    if not v.ok:
        raise ValueError(f"cannot export: verify FAIL: {v.reasons}")

    measures: dict[str, Any] = {}
    measures_dir = root / "measures"
    if measures_dir.is_dir():
        for p in sorted(measures_dir.glob("*.json")):
            try:
                measures[p.name] = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"cannot export: corrupt measure file {p.name}: {e}"
                ) from e

    claims: dict[str, Any] = {}
    claims_dir = root / "claims"
    if claims_dir.is_dir():
        for p in sorted(claims_dir.glob("*.json")):
            try:
                claims[p.name] = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"cannot export: corrupt claim file {p.name}: {e}"
                ) from e

    events_raw = ""
    events_path = root / "events.jsonl"
    if events_path.is_file():
        events_raw = events_path.read_text(encoding="utf-8")

    try:
        ledger_obj = json.loads((root / "ledger.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"cannot export: ledger.json corrupt: {e}") from e

    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "ledger": ledger_obj,
        "events_jsonl": events_raw,
        "claims": claims,
        "measures": measures,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def import_bundle(bundle_path: str | Path, dest_root: str | Path) -> PhaseLedger:
    """Restore a bundle into dest_root; fail if post-import verify is not PASS."""
    try:
        data = json.loads(Path(bundle_path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"bundle JSON corrupt: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("bundle must be a JSON object")
    ver = data.get("bundle_version")
    if ver != BUNDLE_VERSION:
        raise ValueError(f"unsupported bundle_version: {ver!r}")
    if "ledger" not in data:
        raise ValueError("bundle missing required key 'ledger' (fail-closed)")
    if not isinstance(data["ledger"], dict):
        raise ValueError("bundle 'ledger' must be an object (fail-closed)")
    claims = data.get("claims") or {}
    measures = data.get("measures") or {}
    if not isinstance(claims, dict) or not isinstance(measures, dict):
        raise ValueError("bundle claims/measures must be objects (fail-closed)")

    dest = Path(dest_root)
    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f"destination not empty: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "measures").mkdir(exist_ok=True)
    (dest / "claims").mkdir(exist_ok=True)

    try:
        (dest / "ledger.json").write_text(
            json.dumps(data["ledger"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (dest / "events.jsonl").write_text(data.get("events_jsonl") or "", encoding="utf-8")

        for name, obj in claims.items():
            if not isinstance(obj, dict):
                raise ValueError(f"claim {name!r} must be an object")
            (dest / "claims" / name).write_text(
                json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        for name, obj in measures.items():
            if not isinstance(obj, dict):
                raise ValueError(f"measure {name!r} must be an object")
            (dest / "measures" / name).write_text(
                json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

        ledger = PhaseLedger.open(dest)
        v = ledger.verify()
        if not v.ok:
            raise ValueError(f"import verify FAIL: {v.reasons}")
        return ledger
    except Exception:
        # fail closed: remove partial import on any error after dest created
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        raise
