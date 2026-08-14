# CYCLE-011 — Claims policy + threat model + maturity scoreboard

| Field | Value |
|-------|--------|
| **Scope** | phaseledger only |
| **Line** | O (honest closeout) + C (`maturity` CLI) |
| **Status** | complete when plan/implement/test measures PASS |

## Claim

Make the honest-status closeout machine-checked. Ship `CLAIMS_POLICY.md`, `THREAT_MODEL.md`, and `phaseledger maturity` that measures M0–M4 on this checkout. Green maturity is evidence about this tree, not Unasked `VERIFIED`.

## What landed

- `CLAIMS_POLICY.md` — closed claim vocabulary; forbidden `VERIFIED` / `SECURE` / `PRODUCTION_READY` / `AUDITED` / `INDEPENDENT`
- `THREAT_MODEL.md` — operator-trusted storage; digests are not attestation
- `phaseledger/maturity.py` + CLI `maturity` / `maturity --json`
- `tests/test_maturity.py`
- Doctor requires the new docs; invariants list M0–M4

## Not in this cycle

- Other repos / trust-meter adapter / custom phase sequences
- Cryptographic attestation, third-party audit, GitHub release

## Re-run

```bash
python -m phaseledger maturity
python -m phaseledger maturity --json
python -m unittest tests.test_maturity -v
python -m unittest discover -s tests -v
python -m phaseledger doctor
```
