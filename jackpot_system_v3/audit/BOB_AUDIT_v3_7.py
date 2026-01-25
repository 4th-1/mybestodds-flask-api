#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BOB_AUDIT_v3_7.py
-----------------
Best Odds Bonus (BOB) rule + structure validator for My Best Odds v3.7.

Role:
- Validate the presence and correctness of BOB columns:
    * bob_action
    * bob_note
- Optionally (if available) cross-check BOB with:
    * play_type
    * rubik_bucket
    * confidence_score
    * posterior_p
    * mbo_odds

BOB concepts:
- BOB is the internal smart-checker that:
    * Adds backup coverage when the pattern justifies it
    * Prevents under-playing strong signals
    * Avoids over-BOB when unnecessary

Actions (codes):
- STRAIGHT_ONLY         → "Straight Only (No BOB)"
- ADD_BOX               → "Add Box for Safety"
- ADD_BACK_PAIR         → "Add Back Pair Only"
- ADD_1OFF              → "Add 1-Off"
- BOB_STRONG_COMBO      → "BOB Strong: Add Combo (High Return)"

Outputs, per kit:
- bob_issues.csv

Outputs, global (under ./audit):
- bob_summary_v3_7.json

Exit codes:
- 0 → only WARN/INFO issues
- 1 → any ERROR-level issues (missing columns, unknown actions, etc.)

Usage (from C:\MyBestOdds\jackpot_system_v3):

    python .\audit\BOB_AUDIT_v3_7.py --root .\output --verbose
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
PER_KIT_ISSUES_FILENAME = "bob_issues.csv"
MASTER_SUMMARY_FILENAME = "bob_summary_v3_7.json"

# Required BOB columns for the v3.7 schema
BOB_REQUIRED_COLUMNS = [
    "bob_action",
    "bob_note",
]

# Allowed codes for bob_action
ALLOWED_BOB_ACTIONS = {
    "STRAIGHT_ONLY",   # Straight only, no extra BOB coverage
    "ADD_BOX",         # Add Box for safety
    "ADD_BACK_PAIR",   # Add Back Pair only
    "ADD_1OFF",        # Add 1-Off backup
    "BOB_STRONG_COMBO" # Strong signal: add Combo (high return)
}

# Optional context columns that allow deeper rule checks
OPTIONAL_CONTEXT_COLUMNS = [
    "play_type",
    "rubik_bucket",
    "confidence_score",
    "posterior_p",
    "mbo_odds",
]

# Buckets that generally justify stronger or additional BOB
HIGH_RETURN_BUCKETS = {
    "High-Return",
    "Delta-High",
    "Advantaged",
}

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
# BOB rule helpers
# ---------------------------------------------------------------------------

def normalize_confidence(value) -> float:
    """
    Normalize confidence_score to 0-1 range if possible.

    - If value is between 0 and 1 -> treat directly.
    - If value is between 0 and 100 -> divide by 100.
    - Otherwise, return -1 to indicate "unknown scale".
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

def is_high_confidence(row) -> bool:
    c = normalize_confidence(row.get("confidence_score"))
    return c >= 0.70 if c >= 0 else False

def is_medium_confidence(row) -> bool:
    c = normalize_confidence(row.get("confidence_score"))
    return 0.40 <= c < 0.70 if c >= 0 else False

def is_low_confidence(row) -> bool:
    c = normalize_confidence(row.get("confidence_score"))
    return 0.0 <= c < 0.40 if c >= 0 else False

def has_strong_posterior(row) -> bool:
    """
    Basic heuristic: posterior_p >= 0.010 is strong enough to justify BOB_STRONG_COMBO.
    """
    val = row.get("posterior_p")
    if pd.isna(val):
        return False
    try:
        f = float(val)
    except (TypeError, ValueError):
        return False
    return f >= 0.010

def is_high_return_bucket(row) -> bool:
    b = row.get("rubik_bucket")
    return b in HIGH_RETURN_BUCKETS

# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_bob_structure(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Validate presence of BOB columns and basic structure.
    """
    issues: List[Dict[str, Any]] = []

    for col in BOB_REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append({
                "severity": "ERROR",
                "type": "MISSING_COLUMN",
                "column": col,
                "message": f"Required BOB column '{col}' is missing.",
                "kit_path": kit_path,
                "row_index": None,
            })

    return issues

def validate_bob_rows(df: pd.DataFrame, kit_path: str) -> List[Dict[str, Any]]:
    """
    Validate row-level BOB codes and apply rule logic where context is available.
    Only called if required columns are present.
    """
    issues: List[Dict[str, Any]] = []

    has_play_type = "play_type" in df.columns
    has_rubik_bucket = "rubik_bucket" in df.columns
    has_conf = "confidence_score" in df.columns
    has_posterior = "posterior_p" in df.columns

    for idx, row in df.iterrows():
        action = row.get("bob_action")
        note = row.get("bob_note")

        # --- Structural checks ---

        if pd.isna(action) or str(action).strip() == "":
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_BOB_ACTION",
                "column": "bob_action",
                "message": "bob_action is empty; engine may not have evaluated BOB.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })
            continue  # can't validate content rules without action

        action_str = str(action).strip()

        if action_str not in ALLOWED_BOB_ACTIONS:
            issues.append({
                "severity": "ERROR",
                "type": "INVALID_BOB_ACTION",
                "column": "bob_action",
                "message": (
                    f"Unknown bob_action '{action_str}'. "
                    f"Allowed: {sorted(ALLOWED_BOB_ACTIONS)}"
                ),
                "kit_path": kit_path,
                "row_index": int(idx),
            })

        if pd.isna(note) or str(note).strip() == "":
            issues.append({
                "severity": "WARN",
                "type": "EMPTY_BOB_NOTE",
                "column": "bob_note",
                "message": "bob_note is empty; subscribers will not see explanation.",
                "kit_path": kit_path,
                "row_index": int(idx),
            })

        # --- Rule checks (only if we have enough context) ---

        if not (has_play_type or has_rubik_bucket or has_conf or has_posterior):
            continue  # no context to apply deeper rules

        play_type = str(row.get("play_type")) if has_play_type else None
        bucket = str(row.get("rubik_bucket")) if has_rubik_bucket else None

        high_conf = is_high_confidence(row) if has_conf else False
        med_conf = is_medium_confidence(row) if has_conf else False
        low_conf = is_low_confidence(row) if has_conf else False
        strong_post = has_strong_posterior(row) if has_posterior else False
        high_bucket = is_high_return_bucket(row) if has_rubik_bucket else False

        # 1) Straight + high signal but STRAIGHT_ONLY → potential missed BOB
        if play_type == "Straight" and action_str == "STRAIGHT_ONLY":
            if high_bucket and (high_conf or strong_post):
                issues.append({
                    "severity": "WARN",
                    "type": "POTENTIAL_MISSED_BOB",
                    "column": "bob_action",
                    "message": (
                        "Straight + high-return bucket + strong signal "
                        "but bob_action is STRAIGHT_ONLY. Consider ADD_BOX or BOB_STRONG_COMBO."
                    ),
                    "kit_path": kit_path,
                    "row_index": int(idx),
                })

        # 2) Box / StrBox with aggressive BOB (may be overshooting)
        if play_type in ("Box", "StrBox"):
            if action_str in ("ADD_BOX", "ADD_1OFF", "BOB_STRONG_COMBO"):
                if low_conf and not high_bucket:
                    issues.append({
                        "severity": "WARN",
                        "type": "OVERAGGRESSIVE_BOB",
                        "column": "bob_action",
                        "message": (
                            "Box/StrBox with low confidence and non-high-return bucket "
                            "using aggressive BOB action. Check BOB thresholds."
                        ),
                        "kit_path": kit_path,
                        "row_index": int(idx),
                    })

        # 3) BOB_STRONG_COMBO should be rare and strongly justified
        if action_str == "BOB_STRONG_COMBO":
            if not (high_bucket and (high_conf or strong_post)):
                issues.append({
                    "severity": "WARN",
                    "type": "WEAK_BOB_STRONG_COMBO_JUSTIFICATION",
                    "column": "bob_action",
                    "message": (
                        "BOB_STRONG_COMBO used without clear high-return bucket and strong signal. "
                        "Review thresholds for this action."
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
    Write bob_issues.csv for a kit.
    """
    out_path = os.path.join(kit_path, PER_KIT_ISSUES_FILENAME)
    if not issues:
        df = pd.DataFrame([{
            "severity": "INFO",
            "type": "NO_ISSUES",
            "column": None,
            "message": "No BOB issues detected by BOB_AUDIT_v3_7.",
            "kit_path": kit_path,
            "row_index": None,
        }])
    else:
        df = pd.DataFrame(issues)
    df.to_csv(out_path, index=False)

def write_master_summary(audit_dir: str, summary: Dict[str, Any]) -> None:
    """
    Write bob_summary_v3_7.json in the audit folder.
    """
    out_path = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="BOB_AUDIT_v3_7 – Best Odds Bonus rule/structure validator"
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
        help="Run checks but do not write per-kit CSV or master JSON."
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
    print(" BOB_AUDIT_v3_7 – Best Odds Bonus Validator")
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

        # 1) Structural BOB presence checks
        struct_issues = validate_bob_structure(df, kit_path)
        issues.extend(struct_issues)

        # 2) If structure OK, do row-level rule checks
        if not struct_issues:
            row_issues = validate_bob_rows(df, kit_path)
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
    print(" BOB_AUDIT_v3_7 SUMMARY")
    print("====================================================")
    print(json.dumps(master_summary, indent=2))
    print("")

    if master_summary["total_errors"] > 0:
        print("[RESULT] BOB_AUDIT_v3_7 completed with ERRORS.")
        return 1

    print("[RESULT] BOB_AUDIT_v3_7 completed successfully (no ERROR-level issues).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
