# CYCLE-001 — Gate (G) invariant pack

| Field | Value |
|-------|--------|
| **Capability line** | **G (Gate)** only |
| **Repo** | `phaseledger` only (no other projects) |
| **Status** | complete when plan/implement/test measures are PASS |

## Claim

Document gate invariants and enforce them with tests on the shipped ledger path: re-claim invalidates prior measure; advance refuses claim≠measured-claim; refuse advance when latest measure capture is missing even if state says PASS; refuse non-PASS verdicts and out-of-order phases.

## Not in this cycle

- Capability lines **M / L / C / O** (not claimed done)
- greenwash / RepoPassport / stateweaver / nelson-stack / any other repo

## What changed (outcome)

- Added [INVARIANTS.md](INVARIANTS.md) with stable gate IDs mapped to tests
- `PhaseLedger.advance` fail-closed on **missing `{phase}-latest.json`** and requires capture file verdict `PASS`
- Extended `tests/test_ledger.py`: reclaim, claim-match, missing-capture, FAIL verdict, out-of-order
- README links invariants + this cycle record

## Re-run

```bash
cd /path/to/phaseledger
set PYTHONPATH=.
python -m unittest discover -s tests -v
python -m phaseledger measure fixtures/complete.json
python -m phaseledger measure fixtures/incomplete.json
python -m phaseledger measure fixtures/cycle001-plan.json
```

## Invariants covered

See [INVARIANTS.md](INVARIANTS.md): G-RECLAIM-INVALIDATES, G-CLAIM-MATCH, G-ORDER, G-PASS-ONLY, G-NO-MEASURE, G-MISSING-CAPTURE.
