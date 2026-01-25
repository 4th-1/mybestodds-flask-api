#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fix_missing_core_fields_v3_7.py
---------------------------------------
Restores DRAW_DATE and NUMBER in upgraded v3.7 forecast.csv files
by pulling them from the original v3.6 forecasts in ./output.

- Reads each kit from ./kits/<KIT_NAME>/forecast.csv (58-col v3.7)
- Reads matching original from ./output/<KIT_NAME>/forecast.csv (legacy)
- Copies draw_date -> DRAW_DATE
- Copies number/NUMBER -> NUMBER (encoded, spaces removed)
- Normalizes GAME, DRAW_DATE, NUMBER as string dtype
- Overwrites ./kits/<KIT_NAME>/forecast.csv with fixed version
"""

import os
import sys
import pandas as pd

KITS_ROOT = "kits"
LEGACY_ROOT = "output"


def fail(msg: str):
    print(f"\n❌ [FIX-ERROR] {msg}\n")
    sys.exit(1)


def find_column(df, candidates):
    """
    Return the first column name in df that matches one of the candidates.
    Case-sensitive list, but we try a few variants.
    """
    for c in candidates:
        if c in df.columns:
            return c
    return None


def fix_one_kit(kit_name: str):
    kit_path = os.path.join(KITS_ROOT, kit_name)
    new_forecast_path = os.path.join(kit_path, "forecast.csv")

    original_path = os.path.join(LEGACY_ROOT, kit_name, "forecast.csv")

    if not os.path.isfile(new_forecast_path):
        print(f"[SKIP] No forecast.csv in kits/{kit_name}")
        return

    if not os.path.isfile(original_path):
        print(f"[WARN] No original forecast.csv in output/{kit_name} — cannot restore core fields.")
        return

    print(f"\n[FIX] Processing kit: {kit_name}")
    try:
        df_new = pd.read_csv(new_forecast_path)
    except Exception as e:
        print(f"  ❌ Unable to read v3.7 forecast.csv: {e}")
        return

    try:
        df_old = pd.read_csv(original_path)
    except Exception as e:
        print(f"  ❌ Unable to read original forecast.csv: {e}")
        return

    if len(df_new) != len(df_old):
        print(f"  ❌ Row count mismatch: new={len(df_new)}, old={len(df_old)}. Skipping kit.")
        return

    # -------------------------
    # Restore DRAW_DATE
    # -------------------------
    date_col = find_column(df_old, ["DRAW_DATE", "draw_date", "DrawDate", "DATE", "date"])
    if date_col is None:
        print("  ⚠ No draw_date-like column found in original file. DRAW_DATE will remain as-is.")
    else:
        df_new["DRAW_DATE"] = df_old[date_col]
        print(f"  ✔ Restored DRAW_DATE from original column '{date_col}'")

    # -------------------------
    # Restore NUMBER (encoded)
    # -------------------------
    num_col = find_column(df_old, ["NUMBER", "number", "Number", "NUM", "num"])
    if num_col is None:
        print("  ⚠ No number-like column found in original file. NUMBER will remain as-is.")
    else:
        # Pull original numbers, strip spaces, convert to string
        nums = df_old[num_col].astype(str).str.strip()
        # Remove internal spaces so multi-digit jackpots become concatenated strings
        nums = nums.str.replace(" ", "", regex=False)

        # Assign directly for now (game-specific zero-padding could be added later if needed)
        df_new["NUMBER"] = nums
        print(f"  ✔ Restored NUMBER from original column '{num_col}' (spaces removed)")

    # -------------------------
    # Normalize dtypes for core keys
    # -------------------------
    for col in ["GAME", "DRAW_DATE", "NUMBER"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].astype(str)
    print("  ✔ Normalized dtypes for GAME, DRAW_DATE, NUMBER")

    # -------------------------
    # Overwrite v3.7 forecast.csv
    # -------------------------
    try:
        df_new.to_csv(new_forecast_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"  ❌ Failed to write updated forecast.csv: {e}")
        return

    print("  ✅ Fixed forecast.csv written for", kit_name)


def main():
    if not os.path.isdir(KITS_ROOT):
        fail(f"No kits directory found at: {KITS_ROOT}")

    kit_dirs = [d.name for d in os.scandir(KITS_ROOT) if d.is_dir() and "__pycache__" not in d.name]

    if not kit_dirs:
        fail("No kit folders found under ./kits")

    print("\n===============================================")
    print("  BEGINNING CORE FIELD FIX v3.7 (DRAW_DATE / NUMBER)")
    print("===============================================\n")

    for kit_name in sorted(kit_dirs):
        fix_one_kit(kit_name)

    print("\n===============================================")
    print("  🎉 CORE FIELD FIX COMPLETE — RE-RUN PIPELINE  ")
    print("===============================================\n")


if __name__ == "__main__":
    main()
