#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
run_kit_v3_7.py — v3.7 ENGINE RUNNER (LOCKED)

This runner ONLY calls the public engine API:
    MyBestOddsEngineV37.generate_forecast()

There are NO fallbacks, NO legacy calls, and
NO references to _run_for_date.
"""

import os
import sys
import json

# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------
# ENGINE IMPORT (EXPLICIT)
# ---------------------------------------------------------
from core.v3_7.engine_core_v3_7 import MyBestOddsEngineV37


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    if len(sys.argv) != 5:
        print("\nUsage:")
        print("  python core/v3_7/run_kit_v3_7.py KIT START_DATE END_DATE SUBSCRIBER_JSON\n")
        sys.exit(1)

    KITNAME    = sys.argv[1]
    START_DATE = sys.argv[2]
    END_DATE   = sys.argv[3]
    SUB_PATH   = sys.argv[4]

    # Load subscriber
    try:
        with open(SUB_PATH, "r", encoding="utf-8") as f:
            subscriber = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load subscriber JSON: {e}")
        sys.exit(1)

    print(f"\n[RUNNING V3.7 ENGINE] {KITNAME}: {START_DATE} -> {END_DATE}\n")

    # -----------------------------------------------------
    # RUN ENGINE (SINGLE ENTRY POINT)
    # -----------------------------------------------------
    engine = MyBestOddsEngineV37(config={})
    rows = engine.generate_forecast(START_DATE, END_DATE, subscriber)

    print(f"[INFO] Total rows generated: {len(rows)}")

    # -----------------------------------------------------
    # POST-ENGINE FILTERING (NEW SELECTIVITY LOGIC)
    # -----------------------------------------------------
    try:
        from core.v3_7.post_engine_filter_v3_7 import apply_selectivity_filter, generate_filter_report
        import pandas as pd
        
        if rows:
            # Convert to DataFrame for filtering
            df = pd.DataFrame(rows)
            
            # Apply selectivity filter
            df_filtered = apply_selectivity_filter(df)
            
            # Generate filtering report
            filter_report = generate_filter_report(df_filtered)
            print(f"\n[POST-ENGINE FILTER REPORT]\n{filter_report}")
            
            # Convert back to list of dicts
            rows = df_filtered.to_dict('records')
            
    except Exception as e:
        print(f"[WARNING] Post-engine filtering failed: {e}")
        print("[INFO] Continuing with unfiltered results...")

    print(f"[INFO] Final rows after filtering: {len(rows)}")

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    # Extract subscriber name from path (e.g., BOOK3_TEST0001 from BOOK3_TEST0001.json)
    subscriber_name = os.path.splitext(os.path.basename(SUB_PATH))[0]
    folder_name = f"{subscriber_name}_{START_DATE}_to_{END_DATE}"
    out_folder = os.path.join(PROJECT_ROOT, "core", "v3_7", "output", folder_name)
    os.makedirs(out_folder, exist_ok=True)

    csv_path   = os.path.join(out_folder, "forecast.csv")
    json_path  = os.path.join(out_folder, "forecast.json")
    audit_path = os.path.join(out_folder, "audit_preview.json")

    # CSV
    if rows:
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=sorted({k for r in rows for k in r})
            )
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

    save_json(json_path, rows)
    save_json(audit_path, rows)

    print("[SUCCESS] Base v3.7 forecast generated.")
    print(f"[OUTPUT] {out_folder}\n")


if __name__ == "__main__":
    main()
