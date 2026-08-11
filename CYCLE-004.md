# CYCLE-004 — Init + same-ledger maintenance runner

| Field | Value |
|-------|--------|
| **Scope** | `phaseledger` only |
| **Lines** | **O** (ops/maintenance) + **C** (init CLI surface) partial |
| **Status** | complete when suite green |

## Claim

Add `init` and a **same-ledger** maintenance runner (`maintenance --steps N`) that re-claims, re-measures (strict), re-advances all phases N times, verifies after each step, and appends to `events.jsonl` — fail-closed on first failure.

## Difference from ncycle

| | ncycle | maintenance |
|--|--------|-------------|
| Ledger | fresh `mini-0..N` | **one** ledger |
| History | isolated | cumulative append-only |
| Purpose | isolation / parallelism of proof | long-cycle maintenance simulation |

## Re-run

```bash
python -m phaseledger init --ledger .phaseledger
python -m phaseledger maintenance --ledger .phaseledger --steps 5
python -m phaseledger history --ledger .phaseledger
python -m unittest discover -s tests -v
```
