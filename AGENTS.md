# AGENTS.md — working in phaseledger

## Rules

1. **Measurer-first.** Claims are not trusted until measured.
2. **Fail-closed.** Missing observation / capture is never PASS.
3. **Deterministic.** Same observations → same verdict and digest.
4. **Local-first.** No mandatory network for measure/verify.
5. **Keep failures.** Do not rewrite NO-GO as success.
6. **This repo only** unless the human explicitly expands scope.

## Before advancing a change

```bash
set PYTHONPATH=.
python -m unittest discover -s tests -v
python -m phaseledger doctor
```

## Phases

`plan` → `implement` → `test` — each needs claim → measure → advance.

## Codes

See `phaseledger/codes.py` and `docs/MEASURE_BOUNDARIES.md`.
