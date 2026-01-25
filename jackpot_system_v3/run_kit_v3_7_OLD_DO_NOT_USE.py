#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_kit_v3_7.py — FINALIZED v3.7 ENGINE CONTROLLER
--------------------------------------------------
Authoritative runner for My Best Odds v3.7

STABLE EXECUTION CONTRACT:
- Does NOT reference generate_forecast
- Executes engine via _run_for_date ONLY
- Immune to import shadowing and method drift
"""

import os
import sys
import json
import importlib
from datetime import datetime, timedelta

# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------
# EXPLICIT ENGINE LOAD (NO SHADOWING)
# ---------------------------------------------------------
engine_module = importlib.import_module("core.v3_7.engine_core_v3_7")
MyBestOddsEngineV37 = engine_module.MyBestOddsEngineV37

# ---------------------------------------------------------
# OUTPUT HELPERS
# ---------------------------------------------------------
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
def main():
    if len(sys.argv) < 5:
        print("\nUsage:")
        print("  python -m core.v3_7.run_kit_v3_7 KIT START END SUBSCRIBER_JSON\n")
        sys.exit(1)

    KITNAME    = sys.argv[1]
    START_DATE = sys.argv[2]
    END_DATE   = sys.argv[3]
    SUB_PATH   = sys.argv[4]

    # ---------------------------------------------------------
    # LOAD SUBSCRIBER
    # ---------------------------------------------------------
    try:
        with open(SUB_PATH, "r", encoding="utf-8") as f:
            subscriber = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load subscriber JSON: {e}")
        sys.exit(1)

    print(f"\n[RUNNING V3.7 ENGINE] {KITNAME}: {START_DATE} → {END_DATE}\n")

    # ---------------------------------------------------------
    # RUN ENGINE (HARD-CONTRACT)
    # ---------------------------------------------------------
    engine = MyBestOddsEngineV37(config={})
    rows = []

    start = datetime.strptime(START_DATE, "%Y-%m-%d").date()
    end   = datetime.strptime(END_DATE, "%Y-%m-%d").date()

    cur = start
    while cur <= end:
        day_rows = engine._run_for_date(cur.strftime("%Y-%m-%d"), subscriber)
        if day_rows:
            rows.extend(day_rows)
        cur += timedelta(days=1)

    print(f"[INFO] Total rows generated: {len(rows)}")

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------
    folder_name = f"{KITNAME}_{START_DATE}_to_{END_DATE}"
    out_folder = os.path.join(PROJECT_ROOT, "core", "v3_7", "output", folder_name)
    os.makedirs(out_folder, exist_ok=True)

    csv_path   = os.path.join(out_folder, "forecast.csv")
    json_path  = os.path.join(out_folder, "forecast.json")
    audit_path = os.path.join(out_folder, "audit_preview.json")

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
    print(f"[OUTPUT] {out_folder}")
    print("\n[READY] Files are SENTINEL-ready and Option-C compliant.\n")

if __name__ == "__main__":
    main()
