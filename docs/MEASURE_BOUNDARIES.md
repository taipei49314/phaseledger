# Measure boundary matrix (CYCLE-005)

All cases drive the shipped `phaseledger.measure.measure` function.

| Case | Input shape | Expected verdict |
|------|-------------|------------------|
| All required + checks pass | complete fixture | `PASS` |
| Missing any required key | drop one of REQUIRED_KEYS | `INCOMPLETE` |
| Empty mapping | `{}` | `INCOMPLETE` |
| artifact_present false | bool false | `FAIL` |
| invalid sha256 | wrong length / non-hex | `FAIL` |
| empty checks (default) | `checks: []` | `UNKNOWN` |
| empty checks strict | `strict=True` | `FAIL` |
| check passed false | named check | `FAIL` |
| empty check name | `name: "  "` | `FAIL` |
| whitespace phase/claim | `"   "` | `FAIL` |
| schema_version 1 | int/str 1 / 1.0 | `PASS` (if else ok) |
| schema_version unsupported | e.g. 99 | `FAIL` |
| non-bool artifact_present | string/number | `FAIL` |
| checks not a list | object | `FAIL` |

## Advance refuse codes (stable)

| Code | When |
|------|------|
| `PRIOR_NOT_ADVANCED` | Earlier phase not advanced |
| `NO_MEASURE` | No measure recorded |
| `NON_PASS_MEASURE` | Latest measure not PASS |
| `MISSING_CAPTURE` | `{phase}-latest.json` missing |
| `CAPTURE_CORRUPT` | Latest capture unreadable / no result |
| `CLAIM_MISMATCH` | Claim text ≠ measured claim |
| `CAPTURE_NON_PASS` | Capture verdict not PASS |
| `DIGEST_MISMATCH` | State digest ≠ capture digest |
| `ADVANCED` | Success token (not a refuse) |

Re-run: `python -m unittest tests.test_refuse_codes tests.test_measure_schema -v`
