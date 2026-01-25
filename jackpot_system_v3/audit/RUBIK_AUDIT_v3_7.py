#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RUBIK_AUDIT_v3_7.py
-------------------
Rubik Play-Type & Grid Alignment Validator for My Best Odds v3.7.

Checks (per kit):
- play_type
- play_type_rubik
- rubik_code
- rubik_bucket

Outputs:
- rubik_issues.csv   (per-kit)
- rubik_summary_v3_7.json (global)

Interpretation:
- If columns are missing → ERROR
- If mappings are wrong → WARN/ERROR
- If valid → SUCCESS
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

RUBIK_REQUIRED_COLUMNS = [
    "play_type",
    "play_type_rubik",
    "rubik_code",
    "rubik_bucket",
]

ALLOWED_PLAY_TYPES = {
    "Straight", "Box", "StrBox", "Combo", "Front Pair", "Back Pair", "1-Off"
}

# Allowance for formatting of rubik_code (e.g., R1C3, BKT2, S4)
RUBIK_CODE_PREFIXES = ("R", "C", "B", "S")

# rubik_bucket typically takes alignment values such as:
ALLOWED_BUCKETS = {
    "High-Return",
    "Balanced",
    "Low-Return",
    "Delta-High",
    "Delta-Low",
    "Advantaged",
    "Neutral",
}

FORECAST_FILENAME = "forecast.csv"
PER_KIT_ISSUES_FILENAME = "rubik_issues.csv"
MASTER_SUMMARY_FILENAME = "rubik_summary_v3_7.json"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg)

def find_kit_folders(root: str, kit_pattern: str = None) -> List[str]:
    kits = []
    if not os.path.isdir(root):
        return kits

    for entry in os.scandir(root):
        if entry.is_dir():
            if kit_pattern and kit_pattern not in entry.name:
                continue
            forecast_path = os.path.join(entry.path, FORECAST_FILENAME)
            if os.path.isfile(forecast_path):
                kits.append(entry.path)

    return sorted(kits)

# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_rubik(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    issues = []

    # Check required columns
    for col in RUBIK_REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append({
                "severity": "ERROR",
                "type": "MISSING_COLUMN",
                "column": col,
                "message": f"Rubik column '{col}' is missing.",
                "kit_path": kit_path,
                "row_index": None,
            })
            # If a required column is missing, we cannot continue deeper Rubik validation
            return issues

    # Validate play_type
    for idx, val in df["play_type"].items():
        if pd.isna(val):
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_PLAY_TYPE",
                "column": "play_type",
                "message": "play_type is empty.",
                "kit_path": kit_path,
                "row_index": int(idx)
            })
            continue

        if val not in ALLOWED_PLAY_TYPES:
            issues.append({
                "severity": "ERROR",
                "type": "INVALID_PLAY_TYPE",
                "column": "play_type",
                "message": f"Invalid play_type '{val}'. Allowed: {sorted(ALLOWED_PLAY_TYPES)}",
                "kit_path": kit_path,
                "row_index": int(idx)
            })

    # Validate rubik_code
    for idx, val in df["rubik_code"].items():
        if pd.isna(val):
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_RUBIK_CODE",
                "column": "rubik_code",
                "message": "rubik_code is empty.",
                "kit_path": kit_path,
                "row_index": int(idx)
            })
            continue

        code_str = str(val)
        if not code_str.startswith(RUBIK_CODE_PREFIXES):
            issues.append({
                "severity": "ERROR",
                "type": "BAD_RUBIK_CODE_FORMAT",
                "column": "rubik_code",
                "message": (
                    f"rubik_code '{code_str}' does not start with expected prefixes "
                    f"{RUBIK_CODE_PREFIXES}."
                ),
                "kit_path": kit_path,
                "row_index": int(idx)
            })

    # Validate rubik_bucket
    for idx, val in df["rubik_bucket"].items():
        if pd.isna(val):
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_RUBIK_BUCKET",
                "column": "rubik_bucket",
                "message": "rubik_bucket is empty.",
                "kit_path": kit_path,
                "row_index": int(idx)
            })
            continue

        if val not in ALLOWED_BUCKETS:
            issues.append({
                "severity": "WARN",
                "type": "UNEXPECTED_BUCKET",
                "column": "rubik_bucket",
                "message": (
                    f"Unexpected bucket '{val}'. Expected values: {sorted(ALLOWED_BUCKETS)}"
                ),
                "kit_path": kit_path,
                "row_index": int(idx)
            })

    return issues

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def write_per_kit_issues(kit_path: str, issues: List[Dict[str, Any]]) -> None:
    out_path = os.path.join(kit_path, PER_KIT_ISSUES_FILENAME)
    df = pd.DataFrame(issues) if issues else pd.DataFrame([{
        "severity": "INFO",
        "type": "NO_ISSUES",
        "column": None,
        "message": "No Rubik issues detected.",
        "kit_path": kit_path,
        "row_index": None,
    }])
    df.to_csv(out_path, index=False)

def write_master_summary(audit_dir: str, summary: Dict[str, Any]) -> None:
    out_path = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="RUBIK_AUDIT_v3_7 – Rubik play-type/grid alignment validator"
    )
    parser.add_argument("--root", default=os.path.join(".", "output"))
    parser.add_argument("--kit-pattern", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    root = os.path.abspath(args.root)
    audit_dir = os.path.dirname(os.path.abspath(__file__))

    print("====================================================")
    print(" RUBIK_AUDIT_v3_7 – Play-Type & Rubik Alignment")
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
        print("[WARN] No kit folders found.")
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
                "type": "MISSING_FILE",
                "column": None,
                "message": f"Missing forecast file: {forecast_path}",
                "kit_path": kit_path,
                "row_index": None,
            }]
            write_per_kit_issues(kit_path, issues)
            master_summary["kits"][kit_name] = {"issues": 1, "errors": 1}
            master_summary["kits_audited"] += 1
            master_summary["total_issues"] += 1
            master_summary["total_errors"] += 1
            continue

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            issues = [{
                "severity": "ERROR",
                "type": "LOAD_ERROR",
                "message": f"Could not load CSV: {e}",
                "kit_path": kit_path,
                "row_index": None,
            }]
            write_per_kit_issues(kit_path, issues)
            master_summary["kits"][kit_name] = {"issues": 1, "errors": 1}
            master_summary["kits_audited"] += 1
            master_summary["total_issues"] += 1
            master_summary["total_errors"] += 1
            continue

        issues = validate_rubik(df, kit_path)
        errors = sum(1 for i in issues if i["severity"] == "ERROR")

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

    write_master_summary(audit_dir, master_summary)

    print("====================================================")
    print(" RUBIK_AUDIT_v3_7 SUMMARY")
    print("====================================================")
    print(json.dumps(master_summary, indent=2))
    print("")

    if master_summary["total_errors"] > 0:
        print("[RESULT] RUBIK_AUDIT_v3_7 completed with ERRORS.")
        return 1

    print("[RESULT] RUBIK_AUDIT_v3_7 completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
