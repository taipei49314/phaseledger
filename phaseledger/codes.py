"""Stable refuse / status codes (CYCLE-009)."""

from __future__ import annotations

# Advance refuse codes — keep in sync with AdvanceError raises and docs.
ADVANCE_CODES = (
    "PRIOR_NOT_ADVANCED",
    "NO_MEASURE",
    "NON_PASS_MEASURE",
    "MISSING_CAPTURE",
    "CAPTURE_CORRUPT",
    "CLAIM_MISMATCH",
    "CAPTURE_NON_PASS",
    "DIGEST_MISMATCH",
)

ADVANCE_SUCCESS = "ADVANCED"

MEASURE_VERDICTS = ("PASS", "FAIL", "UNKNOWN", "INCOMPLETE")
