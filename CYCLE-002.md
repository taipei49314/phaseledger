# CYCLE-002 — Heavy gate / fuzz / N-cycle / verify

| Field | Value |
|-------|--------|
| **Scope** | `phaseledger` only (no other repos) |
| **Focus** | Gate depth (≥10 variants), measure fuzz fail-closed, N=5 mini-cycles, verify after corruption, local regression script |
| **Status** | complete when plan/implement/test measures PASS |

## Claim

Deliver a heavy in-repo integrity cycle: multi-invariant gate matrix with regression guards, fixed-seed measure fuzz that never treats incomplete observations as PASS, five sequential mini-cycles via shipped `ncycle`, and `verify` that FAILs on corrupt ledger/capture and PASSes after honest restore.

## Not in this cycle

- greenwash / RepoPassport / stateweaver / nelson-stack / other repos
- GitHub Actions / external users / multi-day wall-clock hang
- Full mutation-testing product (regression-guard tests only)

## What landed

- `PhaseLedger.verify()` / CLI `verify`
- `run_n_cycles` / CLI `ncycle --count 5`
- `tests/test_gate_matrix.py` (≥12 gate cases + reclaim regression guard)
- `tests/test_measure_fuzz.py` (fixed-seed fuzz)
- `tests/test_verify.py`, `tests/test_ncycle.py`
- `scripts/run_regression.py`
- Updated `INVARIANTS.md`

## Re-run

```bash
cd /path/to/phaseledger
set PYTHONPATH=.
python scripts/run_regression.py
python -m phaseledger ncycle --dir .ncycle-runs --count 5
python -m phaseledger verify --ledger .phaseledger
python -m phaseledger measure fixtures/complete.json
python -m phaseledger measure fixtures/incomplete.json
```

## Mini-cycle semantics

Each mini-cycle `i` uses a fresh ledger at `<dir>/mini-i`, runs claim→measure→advance for `plan`, `implement`, `test`, then `verify`. First failure aborts overall NCYCLE with FAIL.
