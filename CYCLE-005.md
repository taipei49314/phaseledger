# CYCLE-005 — Structured refuse codes + measure boundary matrix

| Field | Value |
|-------|--------|
| **Scope** | phaseledger only |
| **Lines** | G (codes) + M (boundary matrix doc) |

## Claim

Advance refusals expose stable `AdvanceError.code` tokens (`NO_MEASURE`, `CLAIM_MISMATCH`, `DIGEST_MISMATCH`, …). Document the measure boundary matrix under `docs/MEASURE_BOUNDARIES.md`. Add digest mismatch gate on advance.

## Re-run

```bash
python -m unittest tests.test_refuse_codes -v
python -m unittest discover -s tests -v
```
