#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
core_dtype_patch_v3_7.py
---------------------------------------
Hard-normalizes GAME, DRAW_DATE, NUMBER for all kits so that:

- NUMBER is always a zero-padded string for Cash3 / Cash4
- NUMBER is always a string (object dtype) for all games
- GAME, DRAW_DATE are forced to string
- NaNs are removed from the grouping keys
"""

import os
import sys
import re
import pandas as pd

KITS_ROOT = "kits"


def fail(msg: str):
    print(f"\n❌ [DTYPE-PATCH-ERROR] {msg}\n")
    sys.exit(1)


def normalize_number_for_row(game: str, number: str) -> str:
    """
    Normalize NUMBER according to game type.
    """
    if number is None:
        number = ""
    s = str(number).strip()

    # Remove non-digits
    digits_only = re.sub(r"\D", "", s)

    g = (game or "").strip().lower()

    # Cash 3 -> 3 digits
    if "cash3" in g:
        if digits_only == "":
            digits_only = "0"
        return f"{int(digits_only):03d}"

    # Cash 4 -> 4 digits
    if "cash4" in g:
        if digits_only == "":
            digits_only = "0"
        return f"{int(digits_only):04d}"

    # Jackpot games: leave concatenated digits
    return digits_only


def patch_one_kit(kit_name: str):
    kit_path = os.path.join(KITS_ROOT, kit_name)
    forecast_path = os.path.join(kit_path, "forecast.csv")

    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in kits/{kit_name}")
        return

    print(f"\n[DTYPE-PATCH] Processing kit: {kit_name}")

    try:
        df = pd.read_csv(forecast_path)
    except Exception as e:
        print(f"  ❌ Unable to read forecast.csv: {e}")
        return

    # Ensure required fields exist:
    for col in ["GAME", "DRAW_DATE", "NUMBER"]:
        if col not in df.columns:
            print(f"  ⚠ Column '{col}' missing. Skipping.")
            return

    # Normalize GAME and DRAW_DATE
    df["GAME"] = df["GAME"].astype(str).fillna("").str.strip()
    df["DRAW_DATE"] = df["DRAW_DATE"].astype(str).fillna("").str.strip()

    # Normalize NUMBER based on game
    df["NUMBER"] = df.apply(
        lambda row: normalize_number_for_row(row["GAME"], row["NUMBER"]),
        axis=1
    )

    # Final type enforcement
    df["GAME"] = df["GAME"].astype(str)
    df["DRAW_DATE"] = df["DRAW_DATE"].astype(str)
    df["NUMBER"] = df["NUMBER"].astype(str)

    try:
        df.to_csv(forecast_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"  ❌ Failed to write updated forecast.csv: {e}")
        return

    print("  ✅ Dtype + NUMBER normalization complete for", kit_name)


def main():
    if not os.path.isdir(KITS_ROOT):
        fail(f"No kits directory found at: {KITS_ROOT}")

    kit_dirs = [
        d.name for d in os.scandir(KITS_ROOT)
        if d.is_dir() and "__pycache__" not in d.name
    ]

    if not kit_dirs:
        fail("No kit folders found under ./kits")

    print("\n====================================================")
    print("  BEGINNING CORE DTYPE + NUMBER PATCH v3.7")
    print("====================================================\n")

    for kit_name in sorted(kit_dirs):
        patch_one_kit(kit_name)

    print("\n====================================================")
    print("  🎉 CORE DTYPE PATCH COMPLETE — RE-RUN PIPELINE   ")
    print("====================================================\n")


if __name__ == "__main__":
    main()
