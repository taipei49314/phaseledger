# CYCLE-003 — Measurer schema/strict + Ledger event history

| Field | Value |
|-------|--------|
| **Scope** | `phaseledger` only |
| **Lines** | **M** (measurer depth) + **L** (append-only history) — not full M/L completion |
| **Status** | complete when plan/implement/test measures PASS |

## Claim

Deepen the measurer with optional `schema_version` and `--strict` (empty checks → FAIL), and deepen the ledger with an append-only `events.jsonl` history plus `history` CLI; verify fails if advanced phases are missing from the event log.

## Not in this cycle

- Other repos / greenwash / RepoPassport / stateweaver
- Distributed log, cloud, external users

## What landed

- `measure(..., strict=False)` + optional `schema_version` (supported: 1 / "1" / "1.0")
- CLI `measure --strict`
- `events.jsonl` on claim / measure / advance
- `PhaseLedger.history_text()` / CLI `history`
- verify checks advance events for advanced phases
- Tests: `test_measure_schema.py`, `test_history.py`

## Re-run

```bash
set PYTHONPATH=.
python -m unittest discover -s tests -v
python -m phaseledger measure fixtures/complete.json --strict
python -m phaseledger history --ledger .phaseledger
python scripts/run_regression.py
```
