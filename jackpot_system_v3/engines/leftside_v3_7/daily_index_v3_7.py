"""
daily_index_v3_7.py
-----------------------------------------
Daily index builder for the v3.7 LEFT engine.

Goal:
    Take raw history (from left_ingest_v3_7.load_left_history)
    and build a consistent "daily index" table for Cash 3 / Cash 4.

Design:
    • Mirrors the structure-style used in v3.6 so Sentinel can cross-check.
    • Keeps all core derived fields in ONE place so score engines can stay lean.
    • Non-destructive: you can safely add more columns later without breaking callers.

Input expectation (from left_ingest_v3_7):
    Columns:
        date        (datetime.date)
        draw_time   (string: MIDDAY / EVENING / NIGHT)
        n1, n2, n3  (int)
        n4          (int, for Cash 4)
        digits      ("XYZ" or "WXYZ")

Main public entries:
    build_daily_index_context(c3_hist, c4_hist) -> dict
        {
            "cash3_daily": <DataFrame>,
            "cash4_daily": <DataFrame>,
        }

    build_daily_index(left_ctx_or_c3, cash4_history=None, lookback_days=365) -> dict
        • Wrapper used by left_ingest_v3_7 (and v3.6-style callers)
        • Accepts either a left_ctx dict or two DataFrames
        • Returns:
            {
                "cash3_daily": <DataFrame>,
                "cash4_daily": <DataFrame>,
                "combined_daily": <DataFrame>,
            }
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Any, Optional

import pandas as pd


# ---------------------------------------
# CONFIG (kept simple for now)
# ---------------------------------------

@dataclass
class DailyIndexConfig:
    game: str               # "cash3" or "cash4"
    lookback_days: int = 365  # window for basic frequency metrics


# ---------------------------------------
# CORE HELPERS
# ---------------------------------------

def _compute_basic_derived(df: pd.DataFrame, game: str) -> pd.DataFrame:
    """
    Compute core per-draw derived fields that are stable across versions:
        • sum_digits
        • unique_count
        • has_double / has_triple / has_quad
    """
    # Defensive copy
    df = df.copy()

    # Sum of digits
    if game.lower() == "cash3":
        df["sum_digits"] = df[["n1", "n2", "n3"]].sum(axis=1)
        digits_cols = ["n1", "n2", "n3"]
    else:
        df["sum_digits"] = df[["n1", "n2", "n3", "n4"]].sum(axis=1)
        digits_cols = ["n1", "n2", "n3", "n4"]

    # Count unique digits
    df["unique_count"] = df[digits_cols].astype(int).apply(
        lambda row: len(set(row.values)), axis=1
    )

    # Pattern flags
    def classify_pattern(row):
        vals = list(row[digits_cols].astype(int).values)
        counts = {v: vals.count(v) for v in set(vals)}
        max_count = max(counts.values())
        if max_count == 4:
            return 0, 0, 1  # double, triple, quad
        if max_count == 3:
            return 0, 1, 0
        if max_count == 2:
            # At least one pair
            return 1, 0, 0
        return 0, 0, 0

    pattern_cols = df.apply(classify_pattern, axis=1, result_type="expand")
    pattern_cols.columns = ["has_double", "has_triple", "has_quad"]

    df[["has_double", "has_triple", "has_quad"]] = pattern_cols

    return df


def _compute_gap_metrics(df: pd.DataFrame, game: str) -> pd.DataFrame:
    """
    Compute basic "gap since last seen" metrics for each full digits combo.

    For each unique digits string:
        • last_seen_gap: number of draws since this combo last hit (NaN for first appearance)
        • hit_index: running count of how many times this combo has hit so far

    These are draw-index-based (not calendar-days).
    """
    df = df.copy()
    df["draw_index"] = range(len(df))

    df["last_seen_gap"] = None
    df["hit_index"] = 0

    last_seen: Dict[str, int] = {}
    hit_counts: Dict[str, int] = {}

    for idx, row in df.iterrows():
        digits = row["digits"]
        cur_index = row["draw_index"]

        # gap
        if digits in last_seen:
            df.at[idx, "last_seen_gap"] = cur_index - last_seen[digits]
        else:
            df.at[idx, "last_seen_gap"] = None

        # hit index
        hit_counts[digits] = hit_counts.get(digits, 0) + 1
        df.at[idx, "hit_index"] = hit_counts[digits]

        # update last seen
        last_seen[digits] = cur_index

    return df


def _compute_rolling_frequency(df: pd.DataFrame, window: int = 365) -> pd.DataFrame:
    """
    Compute a simple rolling frequency for each digits combo over the last N draws.

    For each row:
        • roll_freq_last_N: count of how many times this digits hit in the previous `window` draws.

    NOTE:
        This is a light-weight approximation, suitable as a base feature
        for more advanced statistical engines.
    """
    df = df.copy()
    df["roll_freq_last_N"] = 0

    from collections import deque

    window_digits = deque()  # store digits strings
    window_size = window

    for idx, row in df.iterrows():
        digits = row["digits"]

        # Count frequency in current window
        df.at[idx, "roll_freq_last_N"] = window_digits.count(digits)

        # Update window: add current draw, shrink if too long
        window_digits.append(digits)
        if len(window_digits) > window_size:
            window_digits.pop(0)

    return df


# ---------------------------------------
# MAIN PER-GAME DAILY INDEX
# ---------------------------------------

def build_daily_index_for_game(
    history: pd.DataFrame,
    cfg: Optional[DailyIndexConfig] = None,
) -> pd.DataFrame:
    """
    Builds a "daily index" DataFrame for a single game.

    Input:
        history: DataFrame from left_ingest_v3_7.load_left_history
        cfg: DailyIndexConfig (if None, inferred from history)

    Output:
        DataFrame with columns (at minimum):
            game
            date
            draw_time
            digits
            n1, n2, n3 [, n4]
            sum_digits
            unique_count
            has_double
            has_triple
            has_quad
            draw_index
            last_seen_gap
            hit_index
            roll_freq_last_N
    """

    if cfg is None:
        # Infer game by digit length of first row
        first_len = len(str(history["digits"].iloc[0]))
        game = "cash3" if first_len == 3 else "cash4"
        cfg = DailyIndexConfig(game=game)

    game = cfg.game.lower()

    # Ensure sorted by date, draw_time
    history_sorted = history.sort_values(["date", "draw_time"]).reset_index(drop=True)

    # 1) Static derived
    df = _compute_basic_derived(history_sorted, game=game)

    # 2) Gap metrics
    df = _compute_gap_metrics(df, game=game)

    # 3) Rolling frequency
    df = _compute_rolling_frequency(df, window=cfg.lookback_days)

    # 4) Tag game
    df["game"] = game.upper()

    # Stable ordering of columns for audit readability
    base_cols = ["game", "date", "draw_time", "digits"]
    digit_cols = ["n1", "n2", "n3"] + (["n4"] if game == "cash4" else [])
    feature_cols = [
        "sum_digits",
        "unique_count",
        "has_double",
        "has_triple",
        "has_quad",
        "draw_index",
        "last_seen_gap",
        "hit_index",
        "roll_freq_last_N",
    ]

    ordered_cols = base_cols + digit_cols + feature_cols
    # Keep any extra columns at the end
    extras = [c for c in df.columns if c not in ordered_cols]
    df = df[ordered_cols + extras]

    return df


# ---------------------------------------
# TOP-LEVEL CONTEXT BUILDERS
# ---------------------------------------

def build_daily_index_context(
    cash3_history: pd.DataFrame,
    cash4_history: pd.DataFrame,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """
    Build daily index tables for BOTH Cash 3 and Cash 4,
    mirroring the v3.6 style but with cleaner structure.

    Returns:
        {
            "cash3_daily": <DataFrame>,
            "cash4_daily": <DataFrame>,
        }
    """
    c3_cfg = DailyIndexConfig(game="cash3", lookback_days=lookback_days)
    c4_cfg = DailyIndexConfig(game="cash4", lookback_days=lookback_days)

    cash3_daily = build_daily_index_for_game(cash3_history, cfg=c3_cfg)
    cash4_daily = build_daily_index_for_game(cash4_history, cfg=c4_cfg)

    return {
        "cash3_daily": cash3_daily,
        "cash4_daily": cash4_daily,
    }


def build_daily_index(
    left_ctx_or_c3,
    cash4_history: Optional[pd.DataFrame] = None,
    lookback_days: int = 365,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for v3.6-style callers.

    Accepts EITHER:
        • left_ctx dict with keys "cash3_history", "cash4_history"
        • or two DataFrames: (cash3_history, cash4_history)

    Returns:
        {
            "cash3_daily": <DataFrame>,
            "cash4_daily": <DataFrame>,
            "combined_daily": <DataFrame>,
        }
    """
    if isinstance(left_ctx_or_c3, dict):
        # style: build_daily_index(left_ctx)
        cash3_history = left_ctx_or_c3["cash3_history"]
        cash4_history_local = left_ctx_or_c3["cash4_history"]
    else:
        # style: build_daily_index(cash3_history, cash4_history)
        cash3_history = left_ctx_or_c3
        cash4_history_local = cash4_history
        if cash4_history_local is None:
            raise ValueError(
                "build_daily_index called with a single DataFrame but no cash4_history provided."
            )

    daily_ctx = build_daily_index_context(
        cash3_history=cash3_history,
        cash4_history=cash4_history_local,
        lookback_days=lookback_days,
    )

    # Add a combined table for convenience
    combined_daily = pd.concat(
        [
            daily_ctx["cash3_daily"],
            daily_ctx["cash4_daily"],
        ],
        ignore_index=True,
    ).sort_values(["date", "draw_time"]).reset_index(drop=True)

    daily_ctx["combined_daily"] = combined_daily

    return daily_ctx


# ---------------------------------------
# SMOKE TEST
# ---------------------------------------

if __name__ == "__main__":
    print("daily_index_v3_7 module import OK. Use from left_ingest_v3_7.py for full pipeline.")
