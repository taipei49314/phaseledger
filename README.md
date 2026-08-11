# phaseledger

> **Local-first phase ledger.** Every phase advance requires a fresh deterministic measurer verdict.  
> Claims are not trusted until measured.

[![CI](https://github.com/taipei49314/phaseledger/actions/workflows/ci.yml/badge.svg)](https://github.com/taipei49314/phaseledger/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#honest-status)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/taipei49314/phaseledger)

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
# clone then install (editable)
git clone https://github.com/taipei49314/phaseledger.git
cd phaseledger
pip install -e .

python -m phaseledger --help
python -m phaseledger init --ledger .phaseledger
python -m phaseledger measure fixtures/complete.json
python -m phaseledger measure fixtures/incomplete.json
python -m phaseledger status --ledger .phaseledger
```

Without install, from repo root: `PYTHONPATH=. python -m phaseledger ...`

## Tests / CI

```bash
python -m unittest discover -s tests -v
python -m phaseledger doctor
```

### Latest results (recorded 2026-08-11)

| Check | Result |
|-------|--------|
| **GitHub visibility** | **Public** — https://github.com/taipei49314/phaseledger |
| **CI workflow** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) on every push/PR to `main` |
| **Latest CI run** | **success** — [actions/runs/31479371096](https://github.com/taipei49314/phaseledger/actions/runs/31479371096) (`3e6570b`, README evidence commit also green) |
| **CI matrix** | Python **3.10**, **3.11**, **3.12** (ubuntu-latest) — all green |
| **CI steps (each Python)** | `pip install -e .` → unit tests → `doctor` → CLI smoke (`init` / `measure` complete+incomplete exit 4 / `ncycle` / `maintenance` / `verify`) |
| **CI package job** | sdist + wheel build — green |
| **Local unit suite** | **`Ran 99 tests` … `OK`** (stdlib `unittest`, no extra test deps) |
| **Incomplete fixture** | exit code **4**, verdict **`INCOMPLETE`** (fail-closed; never treated as pass) |
| **User-path smoke** | claim → measure → advance × plan/implement/test; re-claim plan **cascades** later phases to pending; export/import/verify PASS |

Badge at the top of this README tracks live CI status.

### Re-run locally

```bash
python -m unittest discover -s tests -v
python -m phaseledger doctor
python scripts/run_regression.py
```

## Gate invariants

Capability line **G** rules live in [INVARIANTS.md](INVARIANTS.md).  
Cycle records: [CYCLE-001](CYCLE-001.md) … [CYCLE-010](CYCLE-010.md).  
Operator notes: [AGENTS.md](AGENTS.md) · [SECURITY.md](SECURITY.md).  
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

Pre-alpha vertical slice — **public**, **CI green**, **not** third-party audited:

| Area | Status |
|------|--------|
| Measurer | PASS/FAIL/UNKNOWN/INCOMPLETE; `schema_version`; `--strict`; boundary fixtures |
| Ledger | claim → measure → advance; re-claim/**re-measure cascade** on later phases; `events.jsonl` |
| Integrity | `verify`, refuse codes (`NO_MEASURE`, `CLAIM_MISMATCH`, …), export/import bundle |
| Ops CLI | `init`, `status`, `history`, `ncycle`, `maintenance`, `doctor` |
| Tests | **99** unit tests; CI on 3.10–3.12; doctor self-check |
| External audit | none |
| Network at measure time | not required |

Missing observation is never treated as pass. This README is a claim; the fixtures, tests, and CI logs are the evidence.

## License

Apache-2.0
