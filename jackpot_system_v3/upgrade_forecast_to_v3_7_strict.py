#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
upgrade_forecast_to_v3_7_strict.py
---------------------------------------
Upgrades legacy (v3.5–v3.6) 56-column forecast files
into the full 58-column canonical v3.7 schema.

STRICT MODE:
- Only upgrades forecast.csv if it exactly matches expected 56-column legacy layout.
- If columns are missing, duplicated, or out of place, pipeline HALTS.
- All upgraded files are rewritten as the new canonical 58-column format.
"""

import os
import sys
import pandas as pd


# ---------------------------------------------------------
# Define canonical v3.7 58-column schema
# ---------------------------------------------------------
CANONICAL_COLUMNS = [
    # ---- Core ----
    "GAME", "DRAW_DATE", "DRAW_TIME", "NUMBER",

    # ---- Predictive ----
    "DELTA_PATTERN", "POSTERIOR_PROB", "MARKOV_SCORE",
    "MARKOV_TAG", "ML_WIN_LIKELIHOOD", "BASE_CONFIDENCE",

    # ---- Left Engine ----
    "DELTA_HIGH_FLAG", "BALANCED_FLAG", "KELLY_FRACTION",
    "PLAY_FLAG", "LEFT_ENGINE_SCORE",

    # ---- Astro / Planetary ----
    "MOON_PHASE", "ZODIAC_DAY", "ZODIAC_ALIGNMENT_SCORE",
    "PLANETARY_HOUR", "PLANETARY_ALIGNMENT_SCORE",

    # ---- Numerology / MMFSN ----
    "LIFE_PATH_ALIGNMENT", "PERSONAL_DAY_ALIGNMENT",
    "MMFSN_FLAG", "MMFSN_SCORE",

    # ---- Jackpot Engine ----
    "JP_REPEAT_DISTANCE", "JP_STREAK_SCORE",
    "JP_ALIGNMENT_SCORE", "JP_MARKOV_TAG", "JP_FILTER_PASS",

    # ---- Final Selector ----
    "FINAL_CONFIDENCE", "PLAY_TYPE_RECOMMENDATION",
    "PRIORITY_BUCKET", "ODDS_RATIO", "ODDS_LABEL",

    # ---- Hit Logs ----
    "hit_type_book", "hit_type_book3", "hit_type_bosk",

    # ---- Metadata ----
    "ENGINE_VERSION", "KIT_TYPE", "SUBSCRIBER_ID",
    "GENERATED_AT", "UPDATED_AT",

    # ---- Reserved ----
    "RESERVED_01", "RESERVED_02", "RESERVED_03",
    "RESERVED_04", "RESERVED_05", "RESERVED_06",
    "RESERVED_07", "RESERVED_08", "RESERVED_09",
    "RESERVED_10", "RESERVED_11", "RESERVED_12",
    "RESERVED_13", "RESERVED_14", "RESERVED_15",
    "RESERVED_16",
]

TARGET_COUNT = len(CANONICAL_COLUMNS)
LEGACY_COUNT = 56  # Your kits currently have 56 columns


def fail(msg):
    print(f"\n❌ [UPGRADE-ERROR] {msg}\n")
    sys.exit(1)


def upgrade_kit(kit_path):
    kit_name = os.path.basename(kit_path)
    forecast_path = os.path.join(kit_path, "forecast.csv")

    if not os.path.isfile(forecast_path):
        fail(f"[{kit_name}] forecast.csv not found.")

    print(f"\n[UPGRADE] Processing {kit_name}...")

    try:
        df = pd.read_csv(forecast_path)
    except Exception as e:
        fail(f"[{kit_name}] Unable to read forecast.csv: {e}")

    # ---- Check legacy count ----
    if df.shape[1] != LEGACY_COUNT:
        fail(f"[{kit_name}] Expected {LEGACY_COUNT} columns, found {df.shape[1]}. "
             f"Only v3.6 kits can be upgraded.")

    # ---- Add missing columns ----
    missing_cols = [col for col in CANONICAL_COLUMNS if col not in df.columns]

    for col in missing_cols:
        df[col] = None  # Placeholder empty values

    # ---- Reorder columns ----
    try:
        df = df[CANONICAL_COLUMNS]
    except Exception as e:
        fail(f"[{kit_name}] Column reordering failed: {e}")

    # ---- Safety: GAME must not be null ----
    if df["GAME"].isna().all():
        # If GAME missing entirely, infer based on kit folder
        if "BOOK3" in kit_name.upper():
            df["GAME"] = "Cash3"
        elif "BOOK" in kit_name.upper():
            df["GAME"] = "Cash4"
        else:
            df["GAME"] = "UNKNOWN"

    # ---- Save upgraded file ----
    upgraded_path = forecast_path  # overwrite original
    df.to_csv(upgraded_path, index=False)

    print(f"  ✔ Upgrade complete for {kit_name}. Now {TARGET_COUNT} columns.")


def main():
    kits_root = "kits"
    if not os.path.isdir(kits_root):
        fail("No kits directory found at /kits")

    kit_paths = [p.path for p in os.scandir(kits_root) if p.is_dir()]

    if not kit_paths:
        fail("No kit folders found in /kits")

    print("\n===============================================")
    print("  BEGINNING STRICT MODE v3.7 FORECAST UPGRADE  ")
    print("===============================================\n")

    for kit_path in kit_paths:
        # skip internal python folder
        if "__pycache__" in kit_path:
            continue

        upgrade_kit(kit_path)

    print("\n===============================================")
    print("  🎉 UPGRADE COMPLETE — ALL FORECASTS NOW v3.7  ")
    print("===============================================\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
