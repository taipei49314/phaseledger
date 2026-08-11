# CYCLE-008 — Fixture-driven measure boundary matrix

| Field | Value |
|-------|--------|
| **Scope** | phaseledger only |
| **Line** | M |

## Claim

Materialize measure boundary cases as JSON under `fixtures/boundaries/` and drive them through the shipped `measure()` via a table-driven test. Each fixture carries `_expect` (and optional `_strict`).

## Re-run

```bash
python -m unittest tests.test_boundary_fixtures -v
```
