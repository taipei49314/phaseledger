# CYCLE-010 — Blind-spot audit: fail-closed errors + regression tests

## Claim

Probe untested failure paths. Replace raw `JSONDecodeError` / `KeyError` leaks with explicit fail-closed `ValueError` / `SystemExit` messages for: corrupt `ledger.json` on open, corrupt measure files on export, missing bundle `ledger` key on import, invalid observation JSON on CLI measure. Import verify-fail continues to delete partial dest. Add `tests/test_blindspots.py`.

## Findings fixed

| Blind spot | Before | After |
|------------|--------|-------|
| `PhaseLedger.open` corrupt JSON | `JSONDecodeError` | `ValueError` |
| export junk measure JSON | `JSONDecodeError` | `ValueError` |
| import missing `ledger` | `KeyError` | `ValueError` |
| CLI measure bad JSON | `JSONDecodeError` | `SystemExit` with message |
| import verify fail | dest removed | still removed; broader try/except cleanup |
