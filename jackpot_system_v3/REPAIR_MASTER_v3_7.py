#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
REPAIR_MASTER_v3_7.py
---------------------------------
Unified repair script for My Best Odds v3.7.

Goals:
- Fix dtype issues causing Predictive Core "Buffer dtype mismatch" errors.
- Normalize GAME, DRAW_DATE, DRAW_TIME, NUMBER to clean string (object) dtype.
- Convert jackpot NUMBER values like "[3, 18, 24, 41, 55]" into "0318244155".
- Preserve correct formatting for Cash3 / Cash4 numbers (3/4-digit, zero-padded).
- Skip internal folders like __pycache__.
- Produce a JSON summary of repairs applied.

Run from project root:
    python REPAIR_MASTER_v3_7.py
"""

import os
import re
import json
import pandas as pd

KITS_ROOT = "kits"
SUMMARY_FILE = "repair_master_summary_v3_7.json"


def _is_jackpot_game(game: str) -> bool:
    """Return True if the game is a jackpot type (Mega, Powerball, Cash4Life)."""
    if not game:
        return False
    g = game.strip().lower()
    return any(keyword in g for keyword in [
        "mega",      # Mega Millions
        "power",     # Powerball
        "cash4life", # Cash 4 Life
        "cash 4 life"
    ])


def _normalize_cash_number(game: str, number: str) -> str:
    """
    Normalize NUMBER for Cash3 / Cash4 daily games.
    - Remove non-digits.
    - Zero-pad to 3 digits for Cash3.
    - Zero-pad to 4 digits for Cash4.
    """
    if number is None:
        number = ""
    s = str(number).strip()

    digits_only = re.sub(r"\D", "", s)
    if digits_only == "":
        digits_only = "0"

    g = (game or "").strip().lower()

    if "cash3" in g or "cash 3" in g:
        return f"{int(digits_only):03d}"

    if "cash4" in g or "cash 4" in g:
        return f"{int(digits_only):04d}"

    # For other games, just return digits only
    return digits_only


def _normalize_jackpot_number(number: str) -> str:
    """
    Normalize jackpot NUMBER values.

    Handles formats like:
        "[3, 18, 24, 41, 55]"
        "[03, 18, 24, 41, 55]"
        "3, 18, 24, 41, 55"
        "3 18 24 41 55"

    Output:
        "0318244155"
    """
    if number is None:
        return ""

    s = str(number).strip()

    # If it already looks like a concatenated digit string with no separators,
    # just strip non-digits and return.
    if "[" not in s and "]" not in s and "," not in s and " " not in s:
        digits_only = re.sub(r"\D", "", s)
        return digits_only

    # Remove brackets
    s = s.replace("[", "").replace("]", "")

    # Split on commas or whitespace
    parts = re.split(r"[,\s]+", s)
    balls = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not re.search(r"\d", p):
            continue
        try:
            n = int(re.sub(r"\D", "", p))
            balls.append(f"{n:02d}")
        except ValueError:
            # Ignore any weird fragment that can't be turned into int
            continue

    return "".join(balls)


def repair_forecast(path: str, kit_name: str) -> dict:
    """
    Load a forecast.csv file, normalize critical columns, and write back.
    Returns a dict describing what was changed.
    """
    report = {
        "kit": kit_name,
        "file": path,
        "rows": 0,
        "columns": 0,
        "jackpot_rows_fixed": 0,
        "cash_rows_fixed": 0,
        "columns_forced_to_str": [],
    }

    try:
        df = pd.read_csv(path)
    except Exception as e:
        report["error"] = f"Failed to read CSV: {e}"
        return report

    report["rows"] = len(df)
    report["columns"] = len(df.columns)

    # Force these to string if they exist
    critical_cols = ["GAME", "DRAW_DATE", "DRAW_TIME", "NUMBER"]
    for col in critical_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
            report["columns_forced_to_str"].append(col)

    # DRAW_DATE cleanup (remove time / .0 junk)
    if "DRAW_DATE" in df.columns:
        df["DRAW_DATE"] = (
            df["DRAW_DATE"]
            .astype(str)
            .str.replace(" 00:00:00", "", regex=False)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

    # DRAW_TIME cleanup (just strip whitespace; leave format as-is for now)
    if "DRAW_TIME" in df.columns:
        df["DRAW_TIME"] = df["DRAW_TIME"].astype(str).str.strip()

    # Normalization for NUMBER:
    if "GAME" in df.columns and "NUMBER" in df.columns:
        jackpot_mask = df["GAME"].apply(_is_jackpot_game)
        daily_mask = ~jackpot_mask

        # Jackpot rows with list-like NUMBER, e.g. "[3, 18, 24, 41, 55]"
        jackpot_indices = df.index[jackpot_mask].tolist()
        cash_indices = df.index[daily_mask].tolist()

        # Jackpot normalization
        for idx in jackpot_indices:
            original = df.at[idx, "NUMBER"]
            fixed = _normalize_jackpot_number(original)
            df.at[idx, "NUMBER"] = fixed
        report["jackpot_rows_fixed"] = len(jackpot_indices)

        # Cash3 / Cash4 normalization
        for idx in cash_indices:
            game = df.at[idx, "GAME"]
            original = df.at[idx, "NUMBER"]
            fixed = _normalize_cash_number(game, original)
            df.at[idx, "NUMBER"] = fixed
        report["cash_rows_fixed"] = len(cash_indices)

    # Final enforcement of object dtype for critical columns
    for col in critical_cols:
        if col in df.columns:
            df[col] = df[col].astype(object)

    try:
        df.to_csv(path, index=False, encoding="utf-8-sig")
    except Exception as e:
        report["error"] = f"Failed to write CSV: {e}"
        return report

    return report


def main():
    root = os.path.abspath(KITS_ROOT)
    if not os.path.isdir(root):
        print(f"[FATAL] Kits folder not found: {root}")
        return

    print("\n====================================================")
    print("  REPAIR_MASTER_v3_7 — Unified Forecast Repair")
    print("====================================================\n")
    print(f"Kits root: {root}\n")

    summary = {
        "kits_root": root,
        "kits_processed": [],
    }

    for entry in os.scandir(root):
        if not entry.is_dir():
            continue

        kit_name = entry.name

        # Skip Python internal / cache folders
        if kit_name.startswith("__"):
            continue

        forecast_path = os.path.join(entry.path, "forecast.csv")
        if not os.path.isfile(forecast_path):
            print(f"[SKIP] No forecast.csv in {entry.path}")
            continue

        print(f"[REPAIR] Processing kit: {kit_name}")
        report = repair_forecast(forecast_path, kit_name)
        summary["kits_processed"].append(report)

    # Write JSON summary
    out_path = os.path.join(os.path.abspath("."), SUMMARY_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n====================================================")
    print("  🎉 REPAIR_MASTER_v3_7 COMPLETE")
    print("  Summary written to:", SUMMARY_FILE)
    print("====================================================\n")


if __name__ == "__main__":
    main()
