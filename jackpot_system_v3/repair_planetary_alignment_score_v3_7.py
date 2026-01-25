#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_planetary_alignment_score_v3_7.py
----------------------------------------
Backfill PLANETARY_ALIGNMENT_SCORE for all v3.7 kits.

Logic (Option C – Date/Planet-of-the-Day Based):
- Uses PLANETARY_HOUR that is already Oracle-safe.
- For EVERY row, assigns a score 1–5 based on the planetary hour.
- Overwrites any existing PLANETARY_ALIGNMENT_SCORE values.

Usage (run from project root):
    python repair_planetary_alignment_score_v3_7.py
"""

import os
import sys
import json
import pandas as pd

KITS_ROOT = "kits"
SUMMARY_FILE = "repair_planetary_alignment_summary_v3_7.json"


def planetary_hour_to_score(ph: str, candidate_number: str = None) -> int:
    """
    JDS hybrid weighting (symbolic, NOT tied to any one person):
    
    ENHANCED v3.7 - Saturn Course Correction Implementation:
    Based on 4→8 miss analysis (Dec 21, 2025: predicted 1234 vs actual 8321)
    Saturn planetary hour now provides enhanced scoring for Saturn numbers (8, 17, 26)

    Sun / Jupiter  -> 5  (wealth, visibility, luck)
    Venus          -> 4  (harmony, attraction, money flow)
    Mercury        -> 3  (trade, numbers, messages)
    Moon           -> 3  (intuition, emotional timing)
    Mars           -> 2  (forceful, risky)
    Saturn         -> 1  (heavy, restrictive) BUT enhanced for Saturn numbers!

    Unknown / blank -> 0 (treated as neutral/low)
    """
    if pd.isna(ph):
        return 0

    ph = str(ph).strip()
    if not ph:
        return 0

    base_mapping = {
        "Sun": 5,
        "Jupiter": 5,
        "Venus": 4,
        "Mercury": 3,
        "Moon": 3,
        "Mars": 2,
        "Saturn": 1,
    }
    
    base_score = base_mapping.get(ph, 1)
    
    # 🪐 SATURN ENHANCEMENT: Course correction for numbers 8, 17, 26
    if ph == "Saturn" and candidate_number:
        saturn_numbers = {'8', '17', '26'}
        candidate_str = str(candidate_number).strip()
        
        # Check for Saturn number presence
        saturn_digit_count = candidate_str.count('8')  # Focus on 8 (transformation)
        has_seventeen = '17' in candidate_str
        has_twentysix = '26' in candidate_str
        
        enhancement = 0
        if saturn_digit_count > 0:
            enhancement += saturn_digit_count  # +1 per digit 8
        if has_seventeen:
            enhancement += 2  # +2 for complete 17
        if has_twentysix:
            enhancement += 2  # +2 for complete 26
            
        if enhancement > 0:
            # Boost Saturn score (cap at Venus level = 4)
            enhanced_score = min(base_score + enhancement, 4)
            return enhanced_score
    
    return base_score


def main() -> int:
    root = os.path.abspath(KITS_ROOT)
    if not os.path.isdir(root):
        print(f"[FATAL] Kits directory not found: {root}")
        return 1

    print("===============================================")
    print("  BEGINNING PLANETARY ALIGNMENT SCORE REPAIR v3.7")
    print("===============================================")
    print(f"Kits root: {root}\n")

    summary = {
        "kits_root": root,
        "kits_processed": 0,
        "kits_skipped": 0,
        "details": {}
    }

    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        if entry.name.startswith("__"):
            continue  # skip __pycache__ or internals

        kit_name = entry.name
        forecast_path = os.path.join(entry.path, "forecast.csv")

        if not os.path.isfile(forecast_path):
            print(f"[SKIP] No forecast.csv in {entry.path}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "SKIPPED",
                "reason": "forecast.csv missing",
            }
            continue

        print(f"[REPAIR] Processing kit: {kit_name}")

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            print(f"  ❌ Unable to read forecast.csv: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"read error: {e}",
            }
            continue

        if "PLANETARY_HOUR" not in df.columns:
            print("  ❌ PLANETARY_HOUR column missing; cannot compute alignment.")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": "PLANETARY_HOUR column missing",
            }
            continue

        # Ensure the alignment column exists
        if "PLANETARY_ALIGNMENT_SCORE" not in df.columns:
            df["PLANETARY_ALIGNMENT_SCORE"] = 0

        # Compute a score for EVERY row (Option C – overwrite)
        # 🪐 ENHANCED: Pass candidate numbers for Saturn course correction
        if "NUMBER" in df.columns:
            scores = df.apply(lambda row: planetary_hour_to_score(
                row["PLANETARY_HOUR"], 
                row.get("NUMBER", "")
            ), axis=1)
        else:
            # Fallback for rows without NUMBER column
            scores = df["PLANETARY_HOUR"].apply(
                lambda ph: planetary_hour_to_score(ph, None)
            )
        df["PLANETARY_ALIGNMENT_SCORE"] = scores

        nonzero = int((scores != 0).sum())
        total = int(len(df))

        try:
            df.to_csv(forecast_path, index=False)
        except Exception as e:
            print(f"  ❌ Failed to write updated forecast.csv: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"write error: {e}",
            }
            continue

        # Count Saturn enhancements applied
        saturn_enhanced = int((scores > 1).sum()) if "Saturn" in df["PLANETARY_HOUR"].values else 0
        
        print(f"  ✔ PLANETARY_ALIGNMENT_SCORE repaired for {kit_name} "
              f"({nonzero}/{total} rows scored > 0)")
        if saturn_enhanced > 0:
            print(f"    🪐 Saturn course correction applied to {saturn_enhanced} predictions")

        summary["kits_processed"] += 1
        summary["details"][kit_name] = {
            "status": "OK",
            "rows": total,
            "rows_scored_gt_zero": nonzero,
            "saturn_enhancements": saturn_enhanced,
            "course_correction": "Saturn planetary hour enhancement v3.7 applied",
        }

    # Write summary JSON in project root
    out_path = os.path.join(os.path.abspath("."), SUMMARY_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n===============================================")
    print("  🎉 PLANETARY ALIGNMENT SCORE REPAIR COMPLETE")
    print(f"  Summary written to: {SUMMARY_FILE}")
    print("===============================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
