"""
jackpot_ingest_v3_7.py
-----------------------

Right-side (Jackpot) ingest module for v3.7

Games covered:
    • Mega Millions
    • Powerball
    • Cash4Life

Design:
    • Reads history from a shared location:
          ..\shared_history\ga_results
    • Prefers CSV files if they exist:
          mega_history.csv
          powerball_history.csv
          cash4life_history.csv
    • If CSVs are missing, falls back to parsing the
      TXT files in the Sorted folder (the ones you dragged over).

Output:
    build_jackpot_history_context() -> dict:
        {
            "mega_millions": <DataFrame>,
            "powerball": <DataFrame>,
            "cash4life": <DataFrame>,
        }

All scores / odds remain CONFIDENCE-based.
No WLS / WinLikelihoodScore logic is used here.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd

# -------------------------------------------------------------------
# Shared root helper (matches left-engine shared_history layout)
# -------------------------------------------------------------------

def _get_shared_root(project_root: Optional[str] = None) -> str:
    """
    Returns the absolute path to the shared jackpot history root:
        ..\\shared_history\\ga_results
    relative to the given project_root (or this file).
    """
    if project_root is None:
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, "..", ".."))

    shared_root = os.path.abspath(
        os.path.join(project_root, "..", "shared_history", "ga_results")
    )
    return shared_root


# -------------------------------------------------------------------
# CSV LOADERS
# -------------------------------------------------------------------

def _load_csv_if_exists(path: str) -> Optional[pd.DataFrame]:
    """Return DataFrame if CSV exists, otherwise None."""
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Normalize date column name & type if present
        for col in ("draw_date", "date", "Draw Date"):
            if col in df.columns:
                df["draw_date"] = pd.to_datetime(df[col]).dt.date
                break
        return df
    return None


# -------------------------------------------------------------------
# TXT PARSERS (for Sorted folder)
# -------------------------------------------------------------------

def _parse_powerball_txt(path: str) -> pd.DataFrame:
    """
    Parse a Powerball TXT export similar to:
        Powerball    9/1/2025        25 23 8 40 53   5
    """
    rows = []
    if not os.path.exists(path):
        return pd.DataFrame()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip header
            if "Draw Date" in line or "Winning Numbers" in line:
                continue

            parts = line.split()
            # Expect at least: Game, Date, n1..n5, PB
            if len(parts) < 8:
                continue
            game_token = parts[0]
            date_token = parts[1]
            if "/" not in date_token:
                # not a real draw row
                continue

            try:
                draw_date = datetime.strptime(date_token, "%m/%d/%Y").date()
            except ValueError:
                # Unexpected date format, skip
                continue

            nums = parts[2:]
            # Last token is Powerball
            pb = nums[-1]
            main_nums = nums[:-1]
            if len(main_nums) != 5:
                # malformed row
                continue

            try:
                n1, n2, n3, n4, n5 = (int(x) for x in main_nums)
                bonus = int(pb)
            except ValueError:
                continue

            rows.append(
                {
                    "game": "POWERBALL",
                    "draw_date": draw_date,
                    "n1": n1,
                    "n2": n2,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "bonus": bonus,
                }
            )

    return pd.DataFrame(rows)


def _parse_cash4life_txt(path: str) -> pd.DataFrame:
    """
    Parse a Cash4Life TXT export similar to:
        Cash4Life    9/1/2025        "10,24,27,42,51"        4
    or:
        Cash4Life    9/2/2025        1 4 35 45 55    3
    """
    rows = []
    if not os.path.exists(path):
        return pd.DataFrame()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip header
            if "Draw Date" in line or "Winning Numbers" in line:
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            game_token = parts[0]
            date_token = parts[1]
            if "/" not in date_token:
                # malformed or continuation row
                continue

            try:
                draw_date = datetime.strptime(date_token, "%m/%d/%Y").date()
            except ValueError:
                continue

            # The remainder of the line after game + date contains 5 mains + 1 cash ball.
            # We rebuild by removing the first 2 tokens, then normalizing commas/quotes.
            remainder = " ".join(parts[2:])
            remainder = remainder.replace(",", " ")
            remainder = remainder.replace('"', " ").replace("“", " ").replace("”", " ")
            nums = [tok for tok in remainder.split() if tok.strip()]

            if len(nums) < 6:
                # not enough tokens
                continue

            # Last token = cash ball, previous 5 = main numbers
            cb = nums[-1]
            mains = nums[-6:-1] if len(nums) > 6 else nums[:-1]

            if len(mains) != 5:
                continue

            try:
                n1, n2, n3, n4, n5 = (int(x) for x in mains)
                bonus = int(cb)
            except ValueError:
                continue

            rows.append(
                {
                    "game": "CASH4LIFE",
                    "draw_date": draw_date,
                    "n1": n1,
                    "n2": n2,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "bonus": bonus,
                }
            )

    return pd.DataFrame(rows)


def _parse_mega_txt(path: str) -> pd.DataFrame:
    """
    Parse a Mega Millions TXT export similar to:
        Mega Millions  9/10/2025      01 10 24 47 58   4
    We treat it just like Powerball: 5 mains + 1 mega ball.
    """
    rows = []
    if not os.path.exists(path):
        return pd.DataFrame()

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "Draw Date" in line or "Winning Numbers" in line:
                continue

            parts = line.split()
            if len(parts) < 8:
                continue

            # Mega Millions name is usually 2 tokens "Mega" "Millions"
            # so we need to find the date token by scanning for the first token with a '/'
            date_idx = None
            for idx, tok in enumerate(parts):
                if "/" in tok:
                    date_idx = idx
                    break
            if date_idx is None or date_idx == len(parts) - 1:
                continue

            date_token = parts[date_idx]
            try:
                draw_date = datetime.strptime(date_token, "%m/%d/%Y").date()
            except ValueError:
                continue

            # Numbers come after the date token
            nums = parts[date_idx + 1 :]
            if len(nums) < 6:
                continue

            mb = nums[-1]
            mains = nums[:-1]

            if len(mains) != 5:
                # if extra noise, keep last 5 as mains
                mains = mains[-5:]
                if len(mains) != 5:
                    continue

            try:
                n1, n2, n3, n4, n5 = (int(x) for x in mains)
                bonus = int(mb)
            except ValueError:
                continue

            rows.append(
                {
                    "game": "MEGA_MILLIONS",
                    "draw_date": draw_date,
                    "n1": n1,
                    "n2": n2,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "bonus": bonus,
                }
            )

    return pd.DataFrame(rows)


# -------------------------------------------------------------------
# TOP-LEVEL CONTEXT BUILDER
# -------------------------------------------------------------------

def build_jackpot_history_context(project_root: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Build a clean jackpot history context for:

        • Mega Millions
        • Powerball
        • Cash4Life

    Data source priority per game:
        1) CSV in shared_history\\ga_results
        2) TXT in shared_history\\ga_results\\Sorted

    Returns:
        {
            "mega_millions": <DataFrame>,
            "powerball": <DataFrame>,
            "cash4life": <DataFrame>,
        }
    """
    shared_root = _get_shared_root(project_root)
    sorted_root = os.path.join(shared_root, "Sorted")

    if not os.path.exists(shared_root):
        raise FileNotFoundError(f"Shared jackpot history folder not found: {shared_root}")

    # --- Mega Millions ---
    mega_csv = os.path.join(shared_root, "mega_history.csv")
    mega_df = _load_csv_if_exists(mega_csv)
    if mega_df is None:
        # find Mega Millions txt
        mega_txt = None
        if os.path.exists(sorted_root):
            for fname in os.listdir(sorted_root):
                if "mega" in fname.lower():
                    mega_txt = os.path.join(sorted_root, fname)
                    break
        if mega_txt is None:
            mega_df = pd.DataFrame()
        else:
            mega_df = _parse_mega_txt(mega_txt)

    # --- Powerball ---
    power_csv = os.path.join(shared_root, "powerball_history.csv")
    power_df = _load_csv_if_exists(power_csv)
    if power_df is None:
        power_txt = None
        if os.path.exists(sorted_root):
            for fname in os.listdir(sorted_root):
                if "powerball" in fname.lower():
                    power_txt = os.path.join(sorted_root, fname)
                    break
        if power_txt is None:
            power_df = pd.DataFrame()
        else:
            power_df = _parse_powerball_txt(power_txt)

    # --- Cash4Life ---
    c4l_csv = os.path.join(shared_root, "cash4life_history.csv")
    c4l_df = _load_csv_if_exists(c4l_csv)
    if c4l_df is None:
        c4l_txt = None
        if os.path.exists(sorted_root):
            for fname in os.listdir(sorted_root):
                if "cash4life" in fname.lower():
                    c4l_txt = os.path.join(sorted_root, fname)
                    break
        if c4l_txt is None:
            c4l_df = pd.DataFrame()
        else:
            c4l_df = _parse_cash4life_txt(c4l_txt)

    # Normalize column ordering if frames are non-empty
    def _normalize(df: pd.DataFrame, game_label: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["game", "draw_date", "n1", "n2", "n3", "n4", "n5", "bonus"])
        df = df.copy()
        df["game"] = game_label
        cols = ["game", "draw_date", "n1", "n2", "n3", "n4", "n5", "bonus"]
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols].sort_values("draw_date").reset_index(drop=True)

    mega_df = _normalize(mega_df, "MEGA_MILLIONS")
    power_df = _normalize(power_df, "POWERBALL")
    c4l_df = _normalize(c4l_df, "CASH4LIFE")

    return {
        "mega_millions": mega_df,
        "powerball": power_df,
        "cash4life": c4l_df,
    }


# -------------------------------------------------------------------
# SMOKE TEST
# -------------------------------------------------------------------

if __name__ == "__main__":
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ctx = build_jackpot_history_context(project_root=here)

    print("\n=== JACKPOT HISTORY CONTEXT v3.7 ===")
    for key, df in ctx.items():
        print(f"\n[{key}] rows = {len(df)}")
        print(df.head())
    print("\n✓ jackpot_ingest_v3_7.py smoke test completed.\n")
