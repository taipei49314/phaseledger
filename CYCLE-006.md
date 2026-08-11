# CYCLE-006 — Portable ledger export/import bundle

| Field | Value |
|-------|--------|
| **Scope** | phaseledger only |
| **Line** | L (portability) + O (evidence move) |

## Claim

Export a **verify-PASS** ledger to a single JSON bundle; import into an empty directory and re-verify. Export refuses unhealthy ledgers; import refuses non-empty dest and rolls back on verify FAIL.

## CLI

```bash
python -m phaseledger export --ledger .phaseledger --out evidence/bundle.json
python -m phaseledger import --bundle evidence/bundle.json --ledger .restored
python -m phaseledger verify --ledger .restored
```
