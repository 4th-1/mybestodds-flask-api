#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_zodiac_alignment_score_v3_7.py
--------------------------------------
Backfill ZODIAC_DAY and ZODIAC_ALIGNMENT_SCORE for all v3.7 kits
using the universal + JDS hybrid zodiac engine.

Usage (run from project root):
    python repair_zodiac_alignment_score_v3_7.py
"""

import os
import sys
import json
import pandas as pd

# ---------------------------------------------------------
# ENSURE /core IS ALWAYS IMPORTABLE
# ---------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
CORE_DIR = os.path.join(PROJECT_ROOT, "core")

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

# Correct import (local to /core)
from overlay_engine_v3_7 import zodiac_sign_from_date


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------
KITS_ROOT = os.path.join(PROJECT_ROOT, "kits")
SUMMARY_FILE = os.path.join(PROJECT_ROOT, "repair_zodiac_alignment_summary_v3_7.json")


# ---------------------------------------------------------
# MAIN REPAIR LOGIC
# ---------------------------------------------------------
def main() -> int:

    if not os.path.isdir(KITS_ROOT):
        print(f"[FATAL] Kits directory not found: {KITS_ROOT}")
        return 1

    print("===============================================")
    print("  BEGINNING ZODIAC ALIGNMENT SCORE REPAIR v3.7")
    print("===============================================")
    print(f"Kits root: {KITS_ROOT}\n")

    summary = {
        "kits_root": KITS_ROOT,
        "kits_processed": 0,
        "kits_skipped": 0,
        "details": {}
    }

    for entry in os.scandir(KITS_ROOT):
        if not entry.is_dir():
            continue
        if entry.name.startswith("__"):
            continue  # skip __pycache__

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

        # -------------------------------
        # LOAD FORECAST
        # -------------------------------
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

        # -------------------------------
        # Ensure required columns exist
        # -------------------------------
        if "ZODIAC_DAY" not in df.columns:
            df["ZODIAC_DAY"] = ""

        if "ZODIAC_ALIGNMENT_SCORE" not in df.columns:
            df["ZODIAC_ALIGNMENT_SCORE"] = pd.NA

        if "DRAW_DATE" not in df.columns:
            print("  ❌ DRAW_DATE column missing; cannot compute zodiac.")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": "DRAW_DATE column missing",
            }
            continue

        # -------------------------------
        # COMPUTE ZODIAC VALUES
        # -------------------------------
        dates = pd.to_datetime(df["DRAW_DATE"], errors="coerce")

        repaired_rows = 0
        total_rows = len(df)

        for idx, date_obj in dates.items():
            if pd.isna(date_obj):
                continue  # skip invalid draw dates

            try:
                sign, weight = zodiac_sign_from_date(date_obj)
            except Exception as e:
                print(f"  [WARN] Row {idx}: zodiac computation failed: {e}")
                continue

            df.at[idx, "ZODIAC_DAY"] = sign
            df.at[idx, "ZODIAC_ALIGNMENT_SCORE"] = weight
            repaired_rows += 1

        # -------------------------------
        # SAVE REPAIRED CSV
        # -------------------------------
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

        print(f"  ✔ ZODIAC_DAY & ZODIAC_ALIGNMENT_SCORE repaired for {kit_name} "
              f"({repaired_rows}/{total_rows} rows updated)")

        summary["kits_processed"] += 1
        summary["details"][kit_name] = {
            "status": "OK",
            "rows": int(total_rows),
            "rows_repaired": int(repaired_rows),
        }

    # -------------------------------
    # WRITE SUMMARY JSON
    # -------------------------------
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n===============================================")
    print("  🎉 ZODIAC ALIGNMENT SCORE REPAIR COMPLETE")
    print(f"  Summary written to: {SUMMARY_FILE}")
    print("===============================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
