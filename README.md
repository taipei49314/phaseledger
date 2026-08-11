# phaseledger

> **Local-first phase ledger.** Every phase advance requires a fresh deterministic measurer verdict.  
> Claims are not trusted until measured.

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#honest-status)

Aligned with [Nelson Stack](https://github.com/taipei49314/nelson-stack) principles:

- **Deterministic first** — same observations → same verdict
- **Evidence over vibe** — claims without measures do not advance phases
- **Fail-closed** — missing observation is `INCOMPLETE`, never a pass
- **Local-first** — offline measure step; no network required
- **Keep the failures** — non-PASS verdicts remain in the ledger

## The rule

```
Models / authors may CLAIM.
Only the MEASURER may VERDICT.
A phase advances only when a measure for that phase exists and is PASS.
```

## Measurer-first

The first substantive deliverable is the **measurer**: pure function from observations → one of:

| Verdict | Meaning |
|---------|---------|
| `PASS` | All required observations present and consistent with the claim |
| `FAIL` | Observations present and contradict the claim |
| `UNKNOWN` | Observations present but insufficient to decide |
| `INCOMPLETE` | Required observation keys missing (fail-closed) |

Behavior claims are **not** trusted until a measurer run for the claim exists.

## Phases

Default phases: `plan` → `implement` → `test`.

Each advance must carry a measurer capture. The ledger records:

1. claim (what was asserted)
2. measure (verdict + observation digest)
3. advance (only if measure is `PASS`)

## Install / run

```bash
# from repo root, no install required
python -m phaseledger --help
python -m phaseledger measure fixtures/complete.json
python -m phaseledger measure fixtures/incomplete.json
python -m phaseledger status --ledger .phaseledger
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Gate invariants

Capability line **G** rules live in [INVARIANTS.md](INVARIANTS.md).  
Cycle records: [CYCLE-001](CYCLE-001.md) … [CYCLE-008](CYCLE-008.md).  
Measure boundaries: [docs/MEASURE_BOUNDARIES.md](docs/MEASURE_BOUNDARIES.md).

```bash
python -m phaseledger init --ledger .phaseledger
python -m phaseledger maintenance --ledger .phaseledger --steps 5
python -m phaseledger ncycle --dir .ncycle-runs --count 5
python -m phaseledger verify --ledger .phaseledger
python -m phaseledger history --ledger .phaseledger
python -m phaseledger export --ledger .phaseledger --out evidence/bundle.json
python -m phaseledger import --bundle evidence/bundle.json --ledger .restored
python -m phaseledger measure fixtures/complete.json --strict
python scripts/run_regression.py
python -m phaseledger doctor
```

## Honest status

Pre-alpha vertical slice:

- Measurer core + CLI: implemented (`schema_version`, `--strict` in CYCLE-003)
- Phase ledger + append-only `events.jsonl` + `history` (CYCLE-003)
- Gate invariants (G): CYCLE-001 / CYCLE-002
- External audit: none
- Network at measure time: not required
- Capability lines M / L: partially deepened in CYCLE-003 (not fully complete)
- C / O: not claimed

Missing observation is never treated as pass. This README is a claim; the fixtures and tests are the evidence.

## License

Apache-2.0
