# Invariants — Gate (G) + integrity (CYCLE-001 / CYCLE-002)

This cycle set hardens **gate** and **integrity** depth inside `phaseledger` only.
Lines M / L / C / O are not claimed fully complete beyond what is implemented here.

## Gate (G)

| ID | Rule | Test |
|----|------|------|
| **G-NO-MEASURE** | No measure → advance refused | `test_gate01_no_measure_refused` |
| **G-INCOMPLETE** | INCOMPLETE measure → advance refused | `test_gate02_incomplete_refused` |
| **G-FAIL** | FAIL measure → advance refused | `test_gate03_fail_verdict_refused` |
| **G-UNKNOWN** | UNKNOWN measure → advance refused | `test_gate04_unknown_verdict_refused` |
| **G-RECLAIM-INVALIDATES** | re-claim clears measure fields; stale PASS cannot advance | `test_gate05_reclaim_invalidates_measure`, `test_regression_guard_reclaim_must_clear_measure_fields` |
| **G-CLAIM-MATCH** | measured claim must match current claim | `test_gate06_claim_mismatch_refused` |
| **G-MISSING-CAPTURE** | PASS in state without latest file → refuse | `test_gate07_missing_latest_capture_refused` |
| **G-ORDER-IMPLEMENT** | implement before plan advanced → refuse | `test_gate08_out_of_order_implement_refused` |
| **G-ORDER-TEST** | test before plan advanced → refuse | `test_gate09_out_of_order_test_refused` |
| **G-CAPTURE-VERDICT** | latest capture verdict must be PASS | `test_gate10_capture_verdict_tamper_refused` |
| **G-REMEASURE-CLEARS-ADVANCE** | new measure clears advanced | `test_gate11_remeasure_clears_advanced` |
| **G-PASS-AUTHORIZE** | PASS + capture → advance allowed | `test_gate12_pass_then_authorize` |

## Measurer fail-closed (fuzz)

| ID | Rule | Test |
|----|------|------|
| **M-FUZZ-NO-PASS-INCOMPLETE** | Fixed-seed random partial observations never yield PASS | `test_fuzz_missing_keys_never_pass`, `test_fuzz_empty_and_partial_never_pass` |
| **M-INCOMPLETE-NO-ADVANCE** | Incomplete measure cannot authorize advance | `test_incomplete_not_advance_authorizing_via_ledger` |

## Integrity (verify)

| ID | Rule | Test |
|----|------|------|
| **V-HEALTHY** | Consistent ledger+captures → VERIFY PASS | `test_verify_healthy_pass` |
| **V-CORRUPT-LEDGER** | Corrupt ledger.json → VERIFY FAIL | `test_verify_corrupt_ledger_json_fail` |
| **V-MISSING-CAPTURE** | Missing latest capture with measure set → FAIL | `test_verify_missing_capture_fail` |
| **V-RESTORE** | Honest re-measure restores VERIFY PASS | `test_verify_restored_after_remeasure` |

## N-cycle

| ID | Rule | Test |
|----|------|------|
| **N-FIVE-PASS** | 5 sequential mini-cycles all PASS | `test_five_mini_cycles_pass`, `test_cli_ncycle_five` |
| **N-FAIL-CLOSED** | Bad measure aborts N-cycle | `test_ncycle_fails_closed_on_bad_measure` |

## Operating rule

```
claim → measure → advance
verify re-reads disk (ledger.json + *-latest.json)
ncycle: N × (plan→implement→test) fail-closed
```

## Measurer schema (CYCLE-003)

| ID | Rule | Test |
|----|------|------|
| **M-SCHEMA-1** | schema_version 1 / "1" / "1.0" accepted | `test_schema_version_1_pass`, `test_schema_version_string_1_pass` |
| **M-SCHEMA-UNSUPPORTED** | other schema_version → FAIL | `test_unsupported_schema_fail` |
| **M-STRICT-EMPTY-CHECKS** | strict=True + empty checks → FAIL (not UNKNOWN) | `test_strict_empty_checks_fail` |
| **M-CHECK-NAME** | empty check name → FAIL | `test_empty_check_name_fail` |

## Ledger history (CYCLE-003)

| ID | Rule | Test |
|----|------|------|
| **L-EVENTS-APPEND** | claim/measure/advance append events.jsonl; prior lines kept | `test_events_append_only_claim_measure_advance` |
| **L-HISTORY-CLI** | history lists events | `test_history_text_lists_events`, `test_cli_history` |
| **L-VERIFY-EVENTS** | advanced phases must appear in events.jsonl | `test_verify_requires_advance_in_event_log` |

## Advance refuse codes (CYCLE-005)

| Code | Meaning | Test |
|------|---------|------|
| `NO_MEASURE` | no measure | `test_code_no_measure` |
| `PRIOR_NOT_ADVANCED` | prior phase pending | `test_code_prior_not_advanced` |
| `NON_PASS_MEASURE` | measure not PASS | `test_code_non_pass_measure` |
| `MISSING_CAPTURE` | latest file gone | `test_code_missing_capture` |
| `CLAIM_MISMATCH` | claim ≠ measured | `test_code_claim_mismatch` |
| `CAPTURE_NON_PASS` | capture verdict not PASS | `test_code_capture_non_pass` |
| `DIGEST_MISMATCH` | state digest ≠ capture | `test_code_digest_mismatch` |
| `CAPTURE_CORRUPT` | unreadable capture | `test_code_capture_corrupt` |

Boundary matrix: [docs/MEASURE_BOUNDARIES.md](docs/MEASURE_BOUNDARIES.md)

## Local regression

```bash
python scripts/run_regression.py
# or
python -m unittest discover -s tests -v
```
