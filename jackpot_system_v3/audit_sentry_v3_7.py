"""
audit_sentry_v3_7.py

My Best Odds – SENTRY v3.7 Auditor
----------------------------------

This tool verifies that EVERY forecast row produced by engine v3.7
meets strict Option-C + SENTRY compliance.

Run:
    python audit_sentry_v3_7.py path/to/forecast.json
"""

from __future__ import annotations
import json
import sys

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


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def audit_row(row: dict, index: int):
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"Missing field: {field}")
        elif row[field] is None:
            errors.append(f"Null field: {field}")

    # Confidence sanity
    try:
        c = float(row.get("confidence_score", -1))
        if not (0 <= c <= 100):
            errors.append("Invalid confidence_score range")
    except:
        errors.append("confidence_score not numeric")

    # Win odds sanity
    try:
        o = float(row.get("win_odds_1_in", -1))
        if o <= 0:
            errors.append("Invalid win_odds_1_in")
    except:
        errors.append("win_odds_1_in not numeric")

    if row.get("option_c_pass") is not True:
        errors.append("Option-C did NOT pass")

    if row.get("sentry_ready") is not True:
        errors.append("Row NOT marked sentry_ready")

    return errors


def run_audit(path: str):
    rows = load_json(path)
    print(f"\n[SENTRY v3.7] Auditing file: {path}")
    print(f"Total rows: {len(rows)}")

    all_errors = []
    for i, row in enumerate(rows):
        row_errors = audit_row(row, i)
        if row_errors:
            all_errors.append((i, row, row_errors))

    if not all_errors:
        print("\n[SENTRY PASSED] ✔  All rows are fully compliant.\n")
        return

    print("\n❌ SENTRY FAILED — ERRORS FOUND!\n")
    for idx, row, errs in all_errors:
        print(f"Row #{idx}:")
        for e in errs:
            print(f"   - {e}")
        print("")

    print("Fix errors and rerun the engine.\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nUsage:")
        print("  python audit_sentry_v3_7.py output/<KIT>/<file>.json\n")
        sys.exit(1)

    run_audit(sys.argv[1])
