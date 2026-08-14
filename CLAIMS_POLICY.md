# Claims policy

This repository may claim only what a measurer run on a clean checkout has produced.

## Allowed statements

- A named observation file produced one of: PASS, FAIL, UNKNOWN, INCOMPLETE.
- A phase advance produced ADVANCED or a refuse code from phaseledger.codes.ADVANCE_CODES.
- VERIFY PASS is local file integrity of ledger.json plus measure captures. It is not Unasked VERIFIED.
- Exit codes for measure: 0 = PASS, 1 = FAIL, 3 = UNKNOWN, 4 = INCOMPLETE. Usage / I/O errors use 2.
- A green doctor or maturity run is evidence about this checkout.

## Forbidden statements

phaseledger never reports VERIFIED, SECURE, PRODUCTION_READY, AUDITED, or INDEPENDENT as a verdict or as a derived claim.

A fresh PASS authorizes only that phase advance in that ledger. It does not attest a person, an organization, or a third-party audit.

VERIFY PASS is local file integrity, not Unasked VERIFIED.

## Residual

One operator can write a complete observation file, record claim then measure then advance for every phase, and still obtain ADVANCED. That result remains a local ledger event. External independence is an audit responsibility, not a phaseledger output.
