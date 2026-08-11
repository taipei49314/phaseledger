# CYCLE-007 — Doctor self-check + capability scoreboard

| Field | Value |
|-------|--------|
| **Scope** | phaseledger only |
| **Line** | O (ops) + honest scoreboard |

## Claim

Add `phaseledger doctor` which checks required files, key invariant tokens, and runs the full unittest suite. Prints an honest G/M/L/C/O scoreboard (not inflated to complete).

## Re-run

```bash
python -m phaseledger doctor
python -m phaseledger doctor --out doctor-report.txt
```
