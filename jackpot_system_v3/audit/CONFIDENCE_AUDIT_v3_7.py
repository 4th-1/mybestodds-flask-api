#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CONFIDENCE_AUDIT_v3_7.py
------------------------
Confidence score + band validator for My Best Odds v3.7.

Checks:
- confidence_score
- confidence_band

Logic:
- Validates numeric score and range
- Normalizes score to 0-1
- Ensures band (🟩, 🟨, 🤎, 🚫) matches thresholds:

    >= 0.70    -> 🟩
    0.40-0.69  -> 🟨
    0.20-0.39  -> 🤎
    < 0.20     -> 🚫

Outputs, per kit:
- confidence_issues.csv

Outputs, global (under ./audit):
- confidence_summary_v3_7.json

Exit codes:
- 0 → only WARN/INFO issues
- 1 → any ERROR-level issues

Usage (from C:\MyBestOdds\jackpot_system_v3):

    python .\audit\CONFIDENCE_AUDIT_v3_7.py --root .\output --verbose
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
PER_KIT_ISSUES_FILENAME = "confidence_issues.csv"
MASTER_SUMMARY_FILENAME = "confidence_summary_v3_7.json"

REQUIRED_COLUMNS = [
    "confidence_score",
    "confidence_band",
]

ALLOWED_BANDS = {"🟩", "🟨", "🤎", "🚫"}

# Thresholds for normalized (0-1) confidence
GREEN_MIN = 0.70
YELLOW_MIN = 0.40
TAN_MIN = 0.20
# Below TAN_MIN is 🚫

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

# ---------------------------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------------------------

def normalize_confidence(value) -> float:
    """
    Normalize confidence_score to 0-1 range if possible.

    - If value is between 0 and 1 -> treat as already normalized.
    - If value is between 0 and 100 -> divide by 100.
    - Otherwise -> return -1.0 to indicate invalid.
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

def expected_band_from_conf(norm_conf: float) -> str:
    """
    Map normalized confidence to band emoji.
    """
    if norm_conf < 0:
        return "UNKNOWN"
    if norm_conf >= GREEN_MIN:
        return "🟩"
    if norm_conf >= YELLOW_MIN:
        return "🟨"
    if norm_conf >= TAN_MIN:
        return "🤎"
    return "🚫"

# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_structure(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Ensure required columns exist.
    """
    issues: List[Dict[str, Any]] = []

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append({
                "severity": "ERROR",
                "type": "MISSING_COLUMN",
                "column": col,
                "message": f"Required confidence column '{col}' is missing.",
                "kit_path": kit_path,
                "row_index": None,
            })

    return issues

def validate_rows(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Row-level validation of confidence score + band mapping.
    Only run if structure is OK.
    """
    issues: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        raw_val = row.get("confidence_score")
        band = row.get("confidence_band")

        # 1. Check numeric
        if pd.isna(raw_val):
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_CONFIDENCE_SCORE",
                "column": "confidence_score",
                "message": "confidence_score is empty.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        try:
            f = float(raw_val)
        except (TypeError, ValueError):
            issues.append({
                "severity": "ERROR",
                "type": "NON_NUMERIC_CONFIDENCE",
                "column": "confidence_score",
                "message": f"Non-numeric confidence_score '{raw_val}'.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        # 2. Normalize and check range
        norm = normalize_confidence(raw_val)
        if norm < 0:
            issues.append({
                "severity": "ERROR",
                "type": "OUT_OF_RANGE_CONFIDENCE",
                "column": "confidence_score",
                "message": (
                    f"confidence_score '{raw_val}' is outside expected ranges "
                    "[0-1] or [0-100]."
                ),
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        # 3. Band presence
        if pd.isna(band) or str(band).strip() == "":
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_CONFIDENCE_BAND",
                "column": "confidence_band",
                "message": "confidence_band is empty; banding not applied.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        band_str = str(band).strip()

        if band_str not in ALLOWED_BANDS:
            issues.append({
                "severity": "ERROR",
                "type": "INVALID_CONFIDENCE_BAND",
                "column": "confidence_band",
                "message": (
                    f"Invalid confidence_band '{band_str}'. "
                    f"Allowed bands: {sorted(ALLOWED_BANDS)}"
                ),
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue

        # 4. Mapping correctness
        expected_band = expected_band_from_conf(norm)

        if expected_band == "UNKNOWN":
            # Already handled by OUT_OF_RANGE above, but safe-guard
            continue

        if band_str != expected_band:
            # Serious mismatches (strong scoring but skip band, etc.) → ERROR
            if (
                (expected_band == "🟩" and band_str in {"🤎", "🚫"}) or
                (expected_band == "🚫" and band_str in {"🟩", "🟨"})
            ):
                issues.append({
                    "severity": "ERROR",
                    "type": "CONFIDENCE_BAND_MISMATCH",
                    "column": "confidence_band",
                    "message": (
                        f"Band '{band_str}' does not match score {raw_val} (normalized {norm:.3f}); "
                        f"expected '{expected_band}'."
                    ),
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })
            else:
                # Mild mismatches → WARN (e.g., borderline scoring)
                issues.append({
                    "severity": "WARN",
                    "type": "CONFIDENCE_BAND_MISMATCH_SOFT",
                    "column": "confidence_band",
                    "message": (
                        f"Soft mismatch: band '{band_str}' vs score {raw_val} "
                        f"(normalized {norm:.3f}); expected '{expected_band}'."
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
    Write confidence_issues.csv for a kit.
    """
    out_path = os.path.join(kit_path, PER_KIT_ISSUES_FILENAME)
    if not issues:
        df = pd.DataFrame([{
            "severity": "INFO",
            "type": "NO_ISSUES",
            "column": None,
            "message": "No confidence issues detected by CONFIDENCE_AUDIT_v3_7.",
            "kit_path": kit_path,
            "row_index": None,
        }])
    else:
        df = pd.DataFrame(issues)
    df.to_csv(out_path, index=False)

def write_master_summary(audit_dir: str, summary: Dict[str, Any]) -> None:
    """
    Write confidence_summary_v3_7.json.
    """
    out_path = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="CONFIDENCE_AUDIT_v3_7 – Confidence score + band validator"
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
    print(" CONFIDENCE_AUDIT_v3_7 – Confidence Validator")
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

        # Row-level if structure OK
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
    print(" CONFIDENCE_AUDIT_v3_7 SUMMARY")
    print("====================================================")
    print(json.dumps(master_summary, indent=2))
    print("")

    if master_summary["total_errors"] > 0:
        print("[RESULT] CONFIDENCE_AUDIT_v3_7 completed with ERRORS.")
        return 1

    print("[RESULT] CONFIDENCE_AUDIT_v3_7 completed successfully (no ERROR-level issues).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
