#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_moon_phase_v3_7.py  (Oracle-Compliant)
--------------------------------------------
Rebuilds the MOON_PHASE column for all kits and formats
values to EXACTLY match ORACLE expectations.
"""

import os
import sys
import pandas as pd
from datetime import datetime


KITS_ROOT = "kits"

# -----------------------------------------------------
#  Precise moon phase calculator
# -----------------------------------------------------
def moon_phase_from_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return "UNKNOWN"

    known_full = datetime(2023, 1, 6)
    days = (dt - known_full).days % 29.53058867

    if days < 1.84566:
        return "NEW"
    elif days < 5.53699:
        return "WAXING_CRESCENT"
    elif days < 9.22831:
        return "FIRST_QUARTER"
    elif days < 12.91963:
        return "WAXING_GIBBOUS"
    elif days < 16.61096:
        return "FULL"
    elif days < 20.30228:
        return "WANING_GIBBOUS"
    elif days < 23.99361:
        return "LAST_QUARTER"
    elif days < 27.68493:
        return "WANING_CRESCENT"
    else:
        return "NEW"


# -----------------------------------------------------
#  Repair function
# -----------------------------------------------------
def repair_kit(kit_path):
    forecast_path = os.path.join(kit_path, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_path}")
        return

    print(f"[REPAIR] Processing: {kit_path}")

    df = pd.read_csv(forecast_path)

    # Step 1: Compute moon phases
    phases = df["DRAW_DATE"].apply(moon_phase_from_date)

    # Step 2: Replace underscores with spaces to match Oracle
    df["MOON_PHASE"] = phases.str.replace("_", " ")

    df.to_csv(forecast_path, index=False)
    print(f"  ✔ Moon phases repaired for {os.path.basename(kit_path)}")


# -----------------------------------------------------
#  Main runner
# -----------------------------------------------------
def main():
    print("\n===============================================")
    print("  BEGINNING MOON PHASE REPAIR v3.7 (ORACLE SAFE)")
    print("===============================================\n")

    for p in os.scandir(KITS_ROOT):
        if p.is_dir() and not p.name.startswith("__"):
            repair_kit(p.path)

    print("\n===============================================")
    print("  🎉 MOON PHASE REPAIR COMPLETE (Oracle-Compliant)")
    print("  You can now re-run the pipeline.")
    print("===============================================\n")


if __name__ == "__main__":
    main()
