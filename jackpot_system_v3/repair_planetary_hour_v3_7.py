#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_planetary_alignment_score_v3_7.py
----------------------------------------
Backfills PLANETARY_ALIGNMENT_SCORE for all v3.7 kits.

This uses the same universal weighting engine from overlay_engine_v3_7
and guarantees Oracle compliance.

Usage (run from project root):
    python repair_planetary_alignment_score_v3_7.py
"""

import os
import sys
import json
import pandas as pd

# We import from core because overlay_engine_v3_7.py lives in /core
from core.overlay_engine_v3_7 import planetary_weight_for_hour


KITS_ROOT = "kits"
SUMMARY_FILE = "repair_planetary_alignment_summary_v3_7.json"


def compute_planetary_alignment_scores(df):
    """
    Computes PLANETARY_ALIGNMENT_SCORE using planetary_weight_for_hour()
    for each row's PLANETARY_HOUR value.
    """

    scores = []
    for idx, row in df.iterrows():
        planet = str(row.get("PLANETARY_HOUR", "")).strip()

        try:
            weight = planetary_weight_for_hour(planet)
        except Exception:
            weight = None

        scores.append(weight)

    return scores


def main() -> int:
    root = os.path.abspath(KITS_ROOT)
    if not os.path.isdir(root):
        print(f"[FATAL] Kits directory not found: {root}")
        return 1

    print("===============================================")
    print(" BEGINNING PLANETARY ALIGNMENT SCORE REPAIR v3.7")
    print("===============================================\n")
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

        # Ensure column exists
        if "PLANETARY_ALIGNMENT_SCORE" not in df.columns:
            df["PLANETARY_ALIGNMENT_SCORE"] = pd.NA

        # Compute new alignment scores
        try:
            scores = compute_planetary_alignment_scores(df)
        except Exception as e:
            print(f"  ❌ Failed to compute planetary alignment scores: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"compute error: {e}",
            }
            continue

        df["PLANETARY_ALIGNMENT_SCORE"] = scores

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

        print(f"  ✔ PLANETARY_ALIGNMENT_SCORE repaired for {kit_name}")

        summary["kits_processed"] += 1
        summary["details"][kit_name] = {
            "status": "OK",
            "rows": int(len(df)),
        }

    # Write summary file
    summary_path = os.path.join(os.path.abspath("."), SUMMARY_FILE)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n===============================================")
    print(" 🎉 PLANETARY ALIGNMENT SCORE REPAIR COMPLETE")
    print(f" Summary written to: {SUMMARY_FILE}")
    print("===============================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
