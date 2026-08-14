# Threat model (pre-alpha)

## What this tool refuses

Refuse to advance a phase unless a fresh deterministic measure for that claim is PASS and the latest capture is present and consistent.

## Assets

- Ledger directories are operator-trusted storage.
- Observation files, ledger.json, {phase}-latest.json, and export bundles.

## Adversary

- Host user can rewrite ledger.json and captures.
- An agent can emit a complete observation file that matches its own claim.
- Import of an untrusted bundle.

## Mitigations in this repo

- Advance is fail-closed: missing / non-PASS / mismatched / missing-capture refuse with stable codes.
- verify re-reads disk and compares state to captures and the event log.
- Observation and capture digests detect simple tamper of recorded fields.
- Those digests are not a cryptographic attestation chain.
- Import refuses a non-empty destination and rolls back on verify fail.

## Residual

One operator can fabricate a complete PASS pipeline. phaseledger does not prove two people. Binding those observations to an independent examiner is the job of an external admission gate (charterlock / Unasked), not this ledger.

## Out of scope

- Replacing Unasked VERIFIED, charterlock exam admission, greenwash diff checks, or RepoPassport scenario replay
- Multi-tenant or remote attestation
- Network-required measure
