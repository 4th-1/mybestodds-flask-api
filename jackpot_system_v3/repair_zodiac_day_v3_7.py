#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_zodiac_day_v3_7.py
--------------------------------------------
Repairs missing ZODIAC_DAY values for all kits.
Computes the correct zodiac sign based on DRAW_DATE.
"""

import os
import sys
import pandas as pd
from datetime import datetime


KITS_ROOT = "kits"


# -----------------------------------------------------
# Zodiac lookup table (date ranges)
# -----------------------------------------------------
ZODIAC_RANGES = [
    ("Capricorn",  (12, 22), (1, 19)),
    ("Aquarius",   (1, 20),  (2, 18)),
    ("Pisces",     (2, 19),  (3, 20)),
    ("Aries",      (3, 21),  (4, 19)),
    ("Taurus",     (4, 20),  (5, 20)),
    ("Gemini",     (5, 21),  (6, 20)),
    ("Cancer",     (6, 21),  (7, 22)),
    ("Leo",        (7, 23),  (8, 22)),
    ("Virgo",      (8, 23),  (9, 22)),
    ("Libra",      (9, 23),  (10, 22)),
    ("Scorpio",    (10, 23), (11, 21)),
    ("Sagittarius",(11, 22), (12, 21))
]


def zodiac_from_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return "UNKNOWN"

    m, day = d.month, d.day

    for sign, start, end in ZODIAC_RANGES:
        sm, sd = start
        em, ed = end

        if (m == sm and day >= sd) or (m == em and day <= ed) or \
           (sm > em and (m == sm or m == em)):  # Capricorn year wrap
            return sign

    return "UNKNOWN"


# -----------------------------------------------------
# Main repair function
# -----------------------------------------------------
def repair_kit(kit_path):
    forecast_path = os.path.join(kit_path, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_path}")
        return

    print(f"[REPAIR] Processing: {kit_path}")

    df = pd.read_csv(forecast_path)

    # Compute zodiac signs
    df["ZODIAC_DAY"] = df["DRAW_DATE"].apply(zodiac_from_date)

    # Write back
    df.to_csv(forecast_path, index=False)

    print(f"  ✔ Zodiac signs repaired for {os.path.basename(kit_path)}")


# -----------------------------------------------------
# Script entry point
# -----------------------------------------------------
def main():
    print("\n===============================================")
    print("  BEGINNING ZODIAC DAY REPAIR v3.7")
    print("===============================================\n")

    for p in os.scandir(KITS_ROOT):
        if p.is_dir() and not p.name.startswith("__"):
            repair_kit(p.path)

    print("\n===============================================")
    print("  🎉 ZODIAC DAY REPAIR COMPLETE")
    print("  You can now re-run the pipeline.")
    print("===============================================\n")


if __name__ == "__main__":
    main()
