# Security policy (pre-alpha)

## Scope

`phaseledger` is a **local** evidence/gate tool. It is not a multi-tenant cloud service.

## Threat notes

- Ledger directories are trusted as operator-controlled storage.
- `verify` / advance digests detect simple tamper of captures vs state; they are not a cryptographic attestation chain.
- Import of bundles should only use files you trust; malformed JSON is rejected fail-closed.
- Do not feed untrusted paths into `--ledger` on multi-user machines without isolation.

## Reporting

Open a GitHub issue on `taipei49314/phaseledger` with a minimal reproduction. Do not file dependency/RCE claims without a local PoC against this package.

## Status

No third-party audit. Treat as research / pre-alpha.
