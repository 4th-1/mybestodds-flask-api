#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIBE_v3_7.py — Corrected for My Best Odds v3.7 Engine
-------------------------------------------------------

This version has been updated to match the REAL v3.7 engine output.
Old v3.6 columns removed.
New v3.7 fields added.
wls_rank removed.
Posterior, Kelly, ML, Jackpot removed.
"""

import argparse
import json
import os
import sys
from typing import List, Dict, Any, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# v3.7 REQUIRED COLUMN FAMILIES (FINAL / ENGINE-ACCURATE)
# ---------------------------------------------------------------------------

IDENTITY_COLUMNS = [
    "game_code",
    "forecast_date",
    "draw_time",
    "number"
]

OVERLAY_COLUMNS = [
    "overlay_score"
]

RUBIK_COLUMNS = [
    "play_type",
    "play_type_rubix",
    "rubik_code",
    "rubik_bucket"
]

BOB_COLUMNS = [
    "bob_action",
    "bob_note"
]

CONFIDENCE_COLUMNS = [
    "confidence_score",
    "confidence_band",
    "confidence_pct"
]

MBO_ODDS_COLUMNS = [
    "mbo_odds",
    "mbo_odds_text",
    "mbo_odds_band",
    "wls"
]

HITLOG_COLUMNS = [
    "hit_type_book",
    "hit_type_book3",
    "hit_type_bosk"
]

# Optional fields
OPTIONAL_COLUMNS = [
    "moon_phase",
    "zodiac_sign",
    "numerology_code",
    "planetary_hour",
    "sum",
    "sum_range",
    "priority",
    "lane",
    "delta_pattern"
]

REQUIRED_FAMILIES: Dict[str, List[str]] = {
    "identity": IDENTITY_COLUMNS,
    "overlay": OVERLAY_COLUMNS,
    "rubix": RUBIK_COLUMNS,
    "bob": BOB_COLUMNS,
    "confidence": CONFIDENCE_COLUMNS,
    "mbo_odds": MBO_ODDS_COLUMNS,
    "hits": HITLOG_COLUMNS
}

MASTER_REQUIRED_COLUMNS = set(sum(REQUIRED_FAMILIES.values(), []))
OPTIONAL_COLUMN_SET = set(OPTIONAL_COLUMNS)

COLUMN_FAMILY_MAP: Dict[str, str] = {}
for fam, cols in REQUIRED_FAMILIES.items():
    for c in cols:
        COLUMN_FAMILY_MAP[c] = fam
for c in OPTIONAL_COLUMNS:
    COLUMN_FAMILY_MAP[c] = "optional"

FORECAST_FILENAME = "forecast.csv"
PER_KIT_REPORT_FILENAME = "scribe_column_report.csv"
PER_KIT_SUMMARY_FILENAME = "scribe_alignment_summary.txt"
MASTER_SUMMARY_FILENAME = "scribe_master_summary_v3_7.json"

# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def _log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg)


def find_kit_folders(root: str, kit_pattern: str = None) -> List[str]:
    kits: List[str] = []
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
# AUDIT LOGIC
# ---------------------------------------------------------------------------

def audit_kit_columns(kit_path: str, verbose: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
    kit_name = os.path.basename(kit_path)
    forecast_path = os.path.join(kit_path, FORECAST_FILENAME)

    rows: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {
        "kit_name": kit_name,
        "kit_path": kit_path,
        "columns_in_csv": 0,
        "missing_required_count": 0,
        "unexpected_count": 0,
        "optional_present_count": 0,
        "families_missing": {}
    }

    if not os.path.isfile(forecast_path):
        summary["missing_required_count"] = len(MASTER_REQUIRED_COLUMNS)
        summary["families_missing"] = REQUIRED_FAMILIES
        return rows, summary, True

    df = pd.read_csv(forecast_path, nrows=0)
    actual_cols = list(df.columns)
    actual_set = set(actual_cols)

    missing_required = sorted(MASTER_REQUIRED_COLUMNS - actual_set)
    unexpected = sorted(
        col for col in actual_cols
        if col not in MASTER_REQUIRED_COLUMNS and col not in OPTIONAL_COLUMN_SET
    )
    optional_present = sorted(col for col in actual_cols if col in OPTIONAL_COLUMN_SET)

    summary["columns_in_csv"] = len(actual_cols)
    summary["missing_required_count"] = len(missing_required)
    summary["unexpected_count"] = len(unexpected)
    summary["optional_present_count"] = len(optional_present)

    fam_missing = {}
    for fam, cols in REQUIRED_FAMILIES.items():
        missing = [c for c in cols if c in missing_required]
        if missing:
            fam_missing[fam] = missing
    summary["families_missing"] = fam_missing

    for idx, col in enumerate(actual_cols):
        fam = COLUMN_FAMILY_MAP.get(col, "UNEXPECTED")
        rows.append({
            "column_name": col,
            "position": idx,
            "present": True,
            "family": fam,
            "note": (
                "REQUIRED" if col in MASTER_REQUIRED_COLUMNS
                else "OPTIONAL" if col in OPTIONAL_COLUMN_SET
                else "UNEXPECTED"
            )
        })

    for col in missing_required:
        fam = COLUMN_FAMILY_MAP.get(col, "UNKNOWN")
        rows.append({
            "column_name": col,
            "position": None,
            "present": False,
            "family": fam,
            "note": "MISSING_REQUIRED"
        })

    return rows, summary, len(missing_required) > 0

# ---------------------------------------------------------------------------
# REPORT WRITERS
# ---------------------------------------------------------------------------

def write_per_kit_report(kit_path: str, rows: List[Dict[str, Any]]) -> None:
    out = os.path.join(kit_path, PER_KIT_REPORT_FILENAME)
    pd.DataFrame(rows).to_csv(out, index=False)


def write_per_kit_summary(kit_path: str, summary: Dict[str, Any]) -> None:
    out = os.path.join(kit_path, PER_KIT_SUMMARY_FILENAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))


def write_master_summary(audit_dir: str, master_summary: Dict[str, Any]) -> None:
    out = os.path.join(audit_dir, MASTER_SUMMARY_FILENAME)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="SCRIBE_v3_7 – Schema auditor for v3.7 engine outputs.")
    parser.add_argument("--root", default="./output")
    parser.add_argument("--kit-pattern", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    audit_dir = os.path.dirname(os.path.abspath(__file__))

    print("===== SCRIBE_v3_7 (Final Engine-Aligned Version) =====")
    print(f"Root: {root}")

    kits = find_kit_folders(root, args.kit_pattern)
    if not kits:
        print("No kits found.")
        return 0

    master_summary = {
        "root": root,
        "kits_audited": 0,
        "kits": {},
        "total_missing_required": 0,
        "total_unexpected": 0,
        "any_missing_required": False
    }

    any_missing_required = False

    for kit in kits:
        print(f"Auditing: {os.path.basename(kit)}")

        rows, summary, has_missing = audit_kit_columns(kit, verbose=args.verbose)

        master_summary["kits_audited"] += 1
        master_summary["kits"][summary["kit_name"]] = summary
        master_summary["total_missing_required"] += summary["missing_required_count"]
        master_summary["total_unexpected"] += summary["unexpected_count"]

        if has_missing:
            any_missing_required = True

        if not args.dry_run:
            write_per_kit_report(kit, rows)
            write_per_kit_summary(kit, summary)

    master_summary["any_missing_required"] = any_missing_required

    if not args.dry_run:
        write_master_summary(audit_dir, master_summary)

    print(json.dumps(master_summary, indent=2))

    if any_missing_required:
        print("SCRIBE completed with missing required columns.")
        return 1

    print("SCRIBE completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
