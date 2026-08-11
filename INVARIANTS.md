# Gate invariants (capability line **G**)

Cycle scope: **G (Gate)** only. Lines M / L / C / O are not claimed complete here.

These rules are enforced by the shipped `PhaseLedger` in `phaseledger/ledger.py`.
Each invariant has a stable id mapped to a unittest that drives the real ledger path.

| ID | Rule | Test |
|----|------|------|
| **G-RECLAIM-INVALIDATES** | `record_claim` clears advance **and** prior measure fields. Advance after re-claim without a fresh measure must raise `AdvanceError`. | `test_reclaim_invalidates_prior_measure_for_advance` |
| **G-CLAIM-MATCH** | Advance requires the latest measure capture’s observation `claim` to equal the current phase claim when both are set. Tampered claim text must refuse advance. | `test_advance_refuses_measure_for_different_claim` |
| **G-ORDER** | A later phase cannot advance while any prior phase is not advanced. | `test_implement_requires_prior_plan` |
| **G-PASS-ONLY** | Only measure verdict `PASS` authorizes advance; `INCOMPLETE` / `FAIL` / `UNKNOWN` refuse. | `test_advance_on_incomplete_refused`, `test_advance_on_fail_verdict_refused` |
| **G-NO-MEASURE** | Advance with no measure recorded is refused (fail-closed). | `test_advance_without_measure_refused` |
| **G-MISSING-CAPTURE** | If state claims a PASS measure but `{phase}-latest.json` is missing, advance is refused (fail-closed; no self-certify from ledger.json alone). | `test_advance_refuses_missing_latest_capture` |

## Operating rule

```
claim → measure → advance
```

- Claims are not trusted until measured.
- Re-claim invalidates any prior measure for that phase.
- Missing observation / missing capture is never treated as pass.
