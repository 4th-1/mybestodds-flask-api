#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SENTINEL_v3_7.py
----------------
Hit validation + rule enforcement scaffold for My Best Odds v3.7.

Role:
- Validate the presence and correctness of hitlog columns:
    * hit_type_book
    * hit_type_book3
    * hit_type_bosk

- Optionally (if present) cross-check against:
    * game
    * draw_date
    * draw_time
    * number
    * winning_number_book
    * winning_number_book3
    * winning_number_bosk

Outputs per kit:
- sentinel_issues.csv

Outputs global:
- sentinel_summary_v3_7.json

Usage:
    python .\audit\SENTINEL_v3_7.py --root .\output --verbose
"""

import argparse
import json
import os
import sys
from typing import List, Dict, Any

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

FORECAST_FILENAME = "forecast.csv"
PER_KIT_ISSUES_FILENAME = "sentinel_issues.csv"
MASTER_SUMMARY_FILENAME = "sentinel_summary_v3_7.json"

# Required hitlog columns in the v3.7 schema
REQUIRED_HIT_COLUMNS = [
    "hit_type_book",
    "hit_type_book3",
    "hit_type_bosk",
]

# Allowed hit_type values
ALLOWED_HIT_TYPES = {
    "NO_HIT",
    "STRAIGHT",
    "BOX",
    "STRAIGHT_BOX",
    "PAIR",
    "FRONT_PAIR",
    "BACK_PAIR",
    "ONE_OFF",
    "TRIPLE",
    "QUAD",
    "OTHER",
}

# Optional context columns (if present, deeper rules apply)
OPTIONAL_CONTEXT_COLUMNS = [
    "game",
    "draw_date",
    "draw_time",
    "number",
    "winning_number_book",
    "winning_number_book3",
    "winning_number_bosk",
]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg)

def find_kit_folders(root: str, kit_pattern: str = None) -> List[str]:
    """
    Discover kit folders under the given root that contain forecast.csv.
    """
    kits = []
    if not os.path.isdir(root):
        return kits

    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        if kit_pattern and kit_pattern not in entry.name:
            continue
        forecast_path = os.path.join(entry.path, "forecast.csv")
        if os.path.isfile(forecast_path):
            kits.append(entry.path)

    return sorted(kits)

# ---------------------------------------------------------------------------
# Core Validation Logic
# ---------------------------------------------------------------------------

def validate_hit_structure(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """Validate required hit columns exist."""
    issues = []
    for col in REQUIRED_HIT_COLUMNS:
        if col not in df.columns:
            issues.append({
                "severity": "ERROR",
                "type": "MISSING_HIT_COLUMN",
                "column": col,
                "message": f"Required hitlog column '{col}' is missing.",
                "kit_path": kit_path,
                "row_index": None,
            })
    return issues


def validate_hit_rows(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """Row-level validation of hit type values (only if columns exist)."""
    issues = []
    
    has_game = "game" in df.columns
    has_number = "number" in df.columns

    for idx, row in df.iterrows():
        for col in REQUIRED_HIT_COLUMNS:
            val = row.get(col)

            # If empty → warn but not an error
            if pd.isna(val) or str(val).strip() == "":
                issues.append({
                    "severity": "WARN",
                    "type": "EMPTY_HIT_TYPE",
                    "column": col,
                    "message": f"{col} is empty; this row is unclassified.",
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })
                continue

            hit_str = str(val).strip()

            if hit_str not in ALLOWED_HIT_TYPES:
                issues.append({
                    "severity": "ERROR",
                    "type": "INVALID_HIT_TYPE",
                    "column": col,
                    "message": f"Invalid {col}='{hit_str}'. Allowed: {sorted(ALLOWED_HIT_TYPES)}",
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })
                continue

            # Optional deeper logic:
            if hit_str != "NO_HIT" and (has_game and has_number):
                num = str(row["number"])
                game = str(row["game"])

                if game.lower() == "cash3" and len(num) != 3:
                    issues.append({
                        "severity": "WARN",
                        "type": "INVALID_LENGTH_FOR_CASH3",
                        "column": "number",
                        "message": f"Cash3 expects 3 digits but number='{num}'.",
                        "kit_path": kit_path,
                        "row_index": int(idx),
                    })

                if game.lower() == "cash4" and len(num) != 4:
                    issues.append({
                        "severity": "WARN",
                        "type": "INVALID_LENGTH_FOR_CASH4",
                        "column": "number",
                        "message": f"Cash4 expects 4 digits but number='{num}'.",
                        "kit_path": kit_path,
                        "row_index": int(idx),
                    })

    return issues

# ---------------------------------------------------------------------------
# Output Writers
# ---------------------------------------------------------------------------

def write_per_kit_issues(kit_path: str, issues: List[Dict[str, Any]]):
    """Writes sentinel_issues.csv to the kit folder."""
    out_path = os.path.join(kit_path, PER_KIT_ISSUES_FILENAME)
    df = pd.DataFrame(issues) if issues else pd.DataFrame([{
        "severity": "INFO",
        "type": "NO_ISSUES",
        "column": None,
        "message": "No issues detected by Sentinel.",
        "kit_path": kit_path,
        "row_index": None,
    }])
    df.to_csv(out_path, index=False)


def write_master_summary(audit_dir: str, summary: Dict[str, Any]):
    """Writes sentinel_summary_v3_7.json to the audit folder."""
    out_path = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="SENTINEL_v3_7 – Hit Validator")
    parser.add_argument("--root", default="./output",
                        help="Root folder containing kit subfolders")
    parser.add_argument("--kit-pattern", default=None,
                        help="Only audit kit folders containing this substring")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run checks without writing output files")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose console output")

    args = parser.parse_args()
    root = os.path.abspath(args.root)
    audit_dir = os.path.dirname(os.path.abspath(__file__))

    print("====================================================")
    print(" SENTINEL_v3_7 – Hit Validator")
    print("====================================================")
    print(f"Root folder : {root}")
    print(f"Kit pattern : {args.kit_pattern or 'ALL'}")
    print(f"Dry run     : {args.dry_run}")
    print("")

    if not os.path.isdir(root):
        print(f"[FATAL] Root folder does not exist: {root}")
        return 1

    kit_paths = find_kit_folders(root, args.kit_pattern)
    if not kit_paths:
        print("[WARN] No kits found containing forecast.csv")
        return 0

    print(f"Found {len(kit_paths)} kit(s).")
    print("")

    master_summary = {
        "root": root,
        "kits_audited": 0,
        "total_issues": 0,
        "total_errors": 0,
        "kits": {}
    }

    for kit_path in kit_paths:
        kit_name = os.path.basename(kit_path)
        print(f"Auditing kit: {kit_name}")

        forecast_path = os.path.join(kit_path, FORECAST_FILENAME)

        if not os.path.isfile(forecast_path):
            issues = [{
                "severity": "ERROR",
                "type": "MISSING_FORECAST",
                "column": None,
                "message": f"Missing forecast.csv in: {kit_path}",
                "kit_path": kit_path,
                "row_index": None,
            }]
            if not args.dry_run:
                write_per_kit_issues(kit_path, issues)

            master_summary["kits"][kit_name] = {
                "issues": len(issues),
                "errors": len(issues),
            }
            master_summary["kits_audited"] += 1
            master_summary["total_issues"] += len(issues)
            master_summary["total_errors"] += len(issues)
            print("")
            continue

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            issues = [{
                "severity": "ERROR",
                "type": "LOAD_ERROR",
                "column": None,
                "message": f"Unable to load forecast.csv: {e}",
                "kit_path": kit_path,
                "row_index": None,
            }]
            if not args.dry_run:
                write_per_kit_issues(kit_path, issues)

            master_summary["kits"][kit_name] = {
                "issues": len(issues),
                "errors": len(issues),
            }
            master_summary["kits_audited"] += 1
            master_summary["total_issues"] += len(issues)
            master_summary["total_errors"] += len(issues)
            print("")
            continue

        issues = []

        # 1. Structural checks
        struct = validate_hit_structure(df, kit_path)
        issues.extend(struct)

        # 2. Row-level checks
        if not struct:
            row_issues = validate_hit_rows(df, kit_path)
            issues.extend(row_issues)

        errors = sum(1 for i in issues if i["severity"] == "ERROR")

        if not args.dry_run:
            write_per_kit_issues(kit_path, issues)

        master_summary["kits"][kit_name] = {
            "issues": len(issues),
            "errors": errors,
        }
        master_summary["kits_audited"] += 1
        master_summary["total_issues"] += len(issues)
        master_summary["total_errors"] += errors

        print(f"  -> issues={len(issues)}, errors={errors}")
        print("")

    if not args.dry_run:
        write_master_summary(audit_dir, master_summary)

    print("====================================================")
    print(" SENTINEL_v3_7 SUMMARY")
    print("====================================================")
    print(json.dumps(master_summary, indent=2))
    print("")

    if master_summary["total_errors"] > 0:
        print("[RESULT] SENTINEL_v3_7 completed with ERRORS.")
        return 1

    print("[RESULT] SENTINEL_v3_7 completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
