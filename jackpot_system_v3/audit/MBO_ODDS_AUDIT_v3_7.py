#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MBO_ODDS_AUDIT_v3_7.py
----------------------
My Best Odds "1-in-X" score validator for My Best Odds v3.7.

Checks:
- mbo_odds        (numeric X)
- mbo_odds_text   ("1-in-X")
- mbo_odds_band   (🟩, 🟨, 🤎, 🚫)

Optional cross-checks:
- wls             (WinLikelihoodScore)
- confidence_score

Band rules:
    X in [1, 50]      -> 🟩
    X in [51, 150]    -> 🟨
    X in [151, 300]   -> 🤎
    X >= 301          -> 🚫

WLS relationship:
- WLS approximates a probability p.
- If 0 <= wls <= 1      -> p = wls
- If 0 <= wls <= 100    -> p = wls / 100
- Expected odds ≈ 1 / p, compared to mbo_odds with sanity thresholds.

Outputs, per kit:
- mbo_odds_issues.csv

Outputs, global (under ./audit):
- mbo_odds_summary_v3_7.json

Exit codes:
- 0 → only WARN/INFO issues
- 1 → any ERROR-level issues

Usage (from C:\MyBestOdds\jackpot_system_v3):

    python .\audit\MBO_ODDS_AUDIT_v3_7.py --root .\output --verbose
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
PER_KIT_ISSUES_FILENAME = "mbo_odds_issues.csv"
MASTER_SUMMARY_FILENAME = "mbo_odds_summary_v3_7.json"

REQUIRED_COLUMNS = [
    "mbo_odds",
    "mbo_odds_text",
    "mbo_odds_band",
]

OPTIONAL_COLUMNS = [
    "wls",
    "confidence_score",
]

ALLOWED_BANDS = {"🟩", "🟨", "🤎", "🚫"}

# Band thresholds for X in "1-in-X"
def expected_band_from_x(x: float) -> str:
    if x < 1:
        return "UNKNOWN"
    if 1 <= x <= 50:
        return "🟩"
    if 51 <= x <= 150:
        return "🟨"
    if 151 <= x <= 300:
        return "🤎"
    if x >= 301:
        return "🚫"
    return "UNKNOWN"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg)

def find_kit_folders(root: str, kit_pattern: str = None) -> List[str]:
    """
    Discover kit folders under the given root that contain a forecast.csv file.
    """
    kits = []
    if not os.path.isdir(root):
        return kits

    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        if kit_pattern and kit_pattern not in entry.name:
            continue
        forecast_path = os.path.join(entry.path, FORECAST_FILENAME)
        if os.path.isfile(forecast_path):
            kits.append(entry.path)

    return sorted(kits)

def normalize_wls(value) -> float:
    """
    Normalize WLS to a probability in [0,1] if possible.

    - If 0 <= value <= 1   -> treat as probability.
    - If 0 <= value <= 100 -> divide by 100.
    - Otherwise            -> return -1 to indicate invalid/unknown.
    """
    if pd.isna(value):
        return -1.0
    try:
        f = float(value)
    except (TypeError, ValueError):
        return -1.0

    if 0.0 <= f <= 1.0:
        return f
    if 0.0 <= f <= 100.0:
        return f / 100.0

    return -1.0

# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_structure(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Ensure required MBO columns exist.
    """
    issues: List[Dict[str, Any]] = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append({
                "severity": "ERROR",
                "type": "MISSING_COLUMN",
                "column": col,
                "message": f"Required MBO column '{col}' is missing.",
                "kit_path": kit_path,
                "row_index": None,
            })
    return issues

def validate_rows(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Row-level validation of mbo_odds, mbo_odds_text, mbo_odds_band,
    and optional WLS consistency.
    """
    issues: List[Dict[str, Any]] = []

    has_wls = "wls" in df.columns

    for idx, row in df.iterrows():
        raw_odds = row.get("mbo_odds")
        odds_text = row.get("mbo_odds_text")
        band = row.get("mbo_odds_band")

        # 1. Check mbo_odds numeric and >= 1
        if pd.isna(raw_odds):
            issues.append({
                "severity": "ERROR",
                "type": "EMPTY_MBO_ODDS",
                "column": "mbo_odds",
                "message": "mbo_odds is empty.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        try:
            odds_val = float(raw_odds)
        except (TypeError, ValueError):
            issues.append({
                "severity": "ERROR",
                "type": "NON_NUMERIC_MBO_ODDS",
                "column": "mbo_odds",
                "message": f"Non-numeric mbo_odds '{raw_odds}'.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        if odds_val < 1:
            issues.append({
                "severity": "ERROR",
                "type": "INVALID_MBO_ODDS_RANGE",
                "column": "mbo_odds",
                "message": f"mbo_odds '{odds_val}' is < 1. Expected X >= 1.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })

        # 2. Check mbo_odds_text formatting and consistency
        if pd.isna(odds_text) or str(odds_text).strip() == "":
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_MBO_ODDS_TEXT",
                "column": "mbo_odds_text",
                "message": "mbo_odds_text is empty.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
        else:
            text_str = str(odds_text).strip()
            if not text_str.startswith("1-in-"):
                issues.append({
                    "severity": "ERROR",
                    "type": "BAD_MBO_ODDS_TEXT_FORMAT",
                    "column": "mbo_odds_text",
                    "message": (
                        f"mbo_odds_text '{text_str}' does not start with '1-in-'."
                    ),
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })
            else:
                # extract numeric part
                try:
                    text_num_part = text_str[len("1-in-"):]
                    text_num_val = float(text_num_part)
                    # loose equality check (within 1)
                    if abs(text_num_val - odds_val) > 1.0:
                        issues.append({
                            "severity": "WARN",
                            "type": "MBO_ODDS_TEXT_MISMATCH",
                            "column": "mbo_odds_text",
                            "message": (
                                f"mbo_odds_text '{text_str}' numeric part {text_num_val} "
                                f"does not closely match mbo_odds {odds_val}."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })
                except Exception:
                    issues.append({
                        "severity": "ERROR",
                        "type": "MBO_ODDS_TEXT_PARSE_ERROR",
                        "column": "mbo_odds_text",
                        "message": (
                            f"Could not parse numeric portion of mbo_odds_text '{text_str}'."
                        ),
                        "kit_path": kit_path,
                        "row_index": int(idx),
                    })

        # 3. Check band presence and mapping from X
        if pd.isna(band) or str(band).strip() == "":
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_MBO_ODDS_BAND",
                "column": "mbo_odds_band",
                "message": "mbo_odds_band is empty.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
        else:
            band_str = str(band).strip()
            if band_str not in ALLOWED_BANDS:
                issues.append({
                    "severity": "ERROR",
                    "type": "INVALID_MBO_ODDS_BAND",
                    "column": "mbo_odds_band",
                    "message": (
                        f"Invalid mbo_odds_band '{band_str}'. "
                        f"Allowed bands: {sorted(ALLOWED_BANDS)}"
                    ),
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })
            else:
                expected_band = expected_band_from_x(odds_val)
                if expected_band != "UNKNOWN" and band_str != expected_band:
                    # Hard mismatches (e.g., 1-in-30 with 🚫) → ERROR
                    if (
                        (expected_band == "🟩" and band_str in {"🤎", "🚫"}) or
                        (expected_band == "🚫" and band_str in {"🟩", "🟨"})
                    ):
                        issues.append({
                            "severity": "ERROR",
                            "type": "MBO_ODDS_BAND_MISMATCH",
                            "column": "mbo_odds_band",
                            "message": (
                                f"Band '{band_str}' does not match odds X={odds_val}; "
                                f"expected '{expected_band}'."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })
                    else:
                        # Borderline / soft mismatches → WARN
                        issues.append({
                            "severity": "WARN",
                            "type": "MBO_ODDS_BAND_MISMATCH_SOFT",
                            "column": "mbo_odds_band",
                            "message": (
                                f"Soft mismatch: band '{band_str}' vs odds X={odds_val}; "
                                f"expected '{expected_band}'."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })

        # 4. Optional WLS sanity checks
        if has_wls:
            wls_val = row.get("wls")
            p = normalize_wls(wls_val)
            if p > 0:
                # expected odds from WLS
                try:
                    expected_x = 1.0 / p
                except ZeroDivisionError:
                    expected_x = float("inf")

                # Compare on a rough tolerance basis
                if expected_x > 0 and odds_val > 0:
                    ratio = odds_val / expected_x
                    # If extremely far apart (over 10x), flag
                    if ratio > 10 or ratio < 0.1:
                        issues.append({
                            "severity": "WARN",
                            "type": "MBO_WLS_INCONSISTENT",
                            "column": "mbo_odds",
                            "message": (
                                f"MBO odds X={odds_val} is highly inconsistent with "
                                f"WLS-implied X≈{expected_x:.1f} (ratio={ratio:.2f})."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })

                    # Hard error if they are wildly contradictory for strong signals
                    if p >= 0.01 and odds_val > 5000:
                        issues.append({
                            "severity": "ERROR",
                            "type": "MBO_TOO_PESSIMISTIC_FOR_WLS",
                            "column": "mbo_odds",
                            "message": (
                                f"WLS={wls_val} (p≈{p:.4f}) suggests much better than "
                                f"1-in-{odds_val}. Check conversion."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })
                    if p <= 0.0001 and odds_val < 500:
                        issues.append({
                            "severity": "WARN",
                            "type": "MBO_TOO_OPTIMISTIC_FOR_WLS",
                            "column": "mbo_odds",
                            "message": (
                                f"WLS={wls_val} (p≈{p:.6f}) suggests worse than "
                                f"1-in-{odds_val}. Check conversion."
                            ),
                            "kit_path": kit_path,
                            "row_index": int(idx),
                        })

    return issues

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def write_per_kit_issues(kit_path: str, issues: List[Dict[str, Any]]) -> None:
    """
    Write mbo_odds_issues.csv for a kit.
    """
    out_path = os.path.join(kit_path, PER_KIT_ISSUES_FILENAME)
    if not issues:
        df = pd.DataFrame([{
            "severity": "INFO",
            "type": "NO_ISSUES",
            "column": None,
            "message": "No MBO odds issues detected by MBO_ODDS_AUDIT_v3_7.",
            "kit_path": kit_path,
            "row_index": None,
        }])
    else:
        df = pd.DataFrame(issues)
    df.to_csv(out_path, index=False)

def write_master_summary(audit_dir: str, summary: Dict[str, Any]) -> None:
    """
    Write mbo_odds_summary_v3_7.json.
    """
    out_path = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MBO_ODDS_AUDIT_v3_7 – My Best Odds '1-in-X' score validator"
    )
    parser.add_argument(
        "--root",
        default=os.path.join(".", "output"),
        help="Root folder containing kit subfolders (default: ./output)"
    )
    parser.add_argument(
        "--kit-pattern",
        default=None,
        help="Only audit kit folders whose names contain this substring."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks but do not write per-kit CSVs or master JSON."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional details to console."
    )

    args = parser.parse_args()
    root = os.path.abspath(args.root)
    audit_dir = os.path.dirname(os.path.abspath(__file__))

    print("====================================================")
    print(" MBO_ODDS_AUDIT_v3_7 – My Best Odds '1-in-X' Validator")
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
        print("[WARN] No kit folders with forecast.csv found under root.")
        return 0

    print(f"Found {len(kit_paths)} kit(s).")
    print("")

    master_summary: Dict[str, Any] = {
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
            if not args.dry_run:
                write_per_kit_issues(kit_path, issues)
            master_summary["kits"][kit_name] = {
                "issues": len(issues),
                "errors": len(issues),
            }
            master_summary["kits_audited"] += 1
            master_summary["total_issues"] += len(issues)
            master_summary["total_errors"] += len(issues)
            continue

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            issues = [{
                "severity": "ERROR",
                "type": "LOAD_ERROR",
                "column": None,
                "message": f"Could not load CSV: {e}",
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
            continue

        issues: List[Dict[str, Any]] = []

        # Structural
        struct_issues = validate_structure(df, kit_path)
        issues.extend(struct_issues)

        # Row-level only if structure is present
        if not struct_issues:
            row_issues = validate_rows(df, kit_path)
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
    print(" MBO_ODDS_AUDIT_v3_7 SUMMARY")
    print("====================================================")
    print(json.dumps(master_summary, indent=2))
    print("")

    if master_summary["total_errors"] > 0:
        print("[RESULT] MBO_ODDS_AUDIT_v3_7 completed with ERRORS.")
        return 1

    print("[RESULT] MBO_ODDS_AUDIT_v3_7 completed successfully (no ERROR-level issues).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    