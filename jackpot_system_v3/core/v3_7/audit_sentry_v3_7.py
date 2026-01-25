"""
audit_sentry_v3_7.py

My Best Odds – SENTRY v3.7 Auditor
----------------------------------

This tool validates every row in a v3.7 forecast file to ensure
STRICT Option-C compliance and full audit integrity.

Usage:
    python core/v3_7/audit_sentry_v3_7.py output/<KIT>/<forecast.json>

It verifies:
    - All required Option-C fields are present
    - Numeric values are valid
    - Play-Type fields are present
    - Legend fields exist
    - No NULL values for required fields
    - sentry_ready + option_c_pass must both be TRUE
"""

from __future__ import annotations
import json
import sys

# ---------------------------------------------------------------------------
# Required fields for v3.7 (Option-C)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "game_code",
    "forecast_date",
    "draw_time",
    "number",

    "confidence_score",
    "win_odds_1_in",

    "primary_play_type",
    "bob_suggestion",
    "play_flag",
    "legend_code",
    "legend_text",
    "rubik_notes",

    "pattern_tags",
    "sum",
    "engine_source",

    "option_c_pass",
    "sentry_ready",
]


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def audit_row(row: dict, index: int):
    """
    Validate a single forecast row.
    Returns a list of errors (empty list = row is clean)
    """
    errors = []

    # Missing or null fields
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"Missing field: {field}")
            continue
        if row[field] is None:
            errors.append(f"Null field: {field}")

    # Validate confidence_score
    try:
        c = float(row.get("confidence_score", -1))
        if not (0 <= c <= 100):
            errors.append(f"Invalid confidence_score: {c}")
    except:
        errors.append("confidence_score not numeric")

    # Validate win_odds_1_in
    try:
        o = float(row.get("win_odds_1_in", -1))
        if o <= 0:
            errors.append(f"Invalid win_odds_1_in: {o}")
    except:
        errors.append("win_odds_1_in not numeric")

    # Option-C compliance flags
    if row.get("option_c_pass") is not True:
        errors.append("Option-C flag is FALSE")

    if row.get("sentry_ready") is not True:
        errors.append("sentry_ready flag is FALSE")

    # Pattern tags must be a list
    if not isinstance(row.get("pattern_tags", []), list):
        errors.append("pattern_tags is not a list")

    return errors


# ---------------------------------------------------------------------------
# Main Audit Runner
# ---------------------------------------------------------------------------

def run_audit(path: str):
    rows = load_json(path)

    print(f"\n[SENTRY v3.7] VALIDATING: {path}")
    print(f"Rows detected: {len(rows)}\n")

    all_errors = []

    for i, row in enumerate(rows):
        row_errors = audit_row(row, i)
        if row_errors:
            all_errors.append((i, row_errors))

    # -----------------------------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------------------------
    if not all_errors:
        print("✔ SENTRY PASSED — All rows are fully compliant.\n")
        return

    # -----------------------------------------------------------------------
    # FAILURE REPORT
    # -----------------------------------------------------------------------
    print("❌ SENTRY FAILED — Issues Detected!\n")

    for idx, errs in all_errors:
        print(f"Row #{idx}:")
        for err in errs:
            print(f"  - {err}")
        print("")

    print("\nPlease fix upstream logic and rerun the engine.\n")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nUsage:")
        print("  python core/v3_7/audit_sentry_v3_7.py output/<KIT>/<forecast.json>\n")
        sys.exit(1)

    run_audit(sys.argv[1])
