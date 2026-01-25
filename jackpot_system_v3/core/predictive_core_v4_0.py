#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predictive_core_v4_0.py
-----------------------
Jackpot Predictive Core (Option C) for:
    - MegaMillions
    - Powerball
    - Cash4Life

This module:
    - Loads jackpot history from data/jackpot_results/*.csv
    - Normalizes it
    - Attaches basic per-row jackpot stats to forecast.csv rows:
        * jk_game_code
        * jk_has_history
        * jk_history_rows_total
        * jk_draws_seen_to_date
        * jk_days_since_last_draw

It is SAFE:
    - Only touches rows that look like jackpot games
    - Leaves all other games unchanged
"""

import os
import pandas as pd

from .jackpot_loader_v4_0 import load_jackpot
from .jackpot_history_normalizer_v4_0 import normalize_history


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _detect_game_column(df: pd.DataFrame) -> str | None:
    """Try to find the game column."""
    for col in ["game_name", "game", "Game"]:
        if col in df.columns:
            return col
    return None


def _classify_jackpot_game(raw_name: str) -> str | None:
    """
    Map a free-form game label to a canonical jackpot code.
    Returns:
        "MEGAMILLIONS", "POWERBALL", "CASH4LIFE", or None
    """
    if not isinstance(raw_name, str):
        return None

    name = raw_name.upper().strip()

    if "MEGA" in name:
        return "MEGAMILLIONS"
    if "POWER" in name:
        return "POWERBALL"
    if "CASH4LIFE" in name or "CASH 4 LIFE" in name:
        return "CASH4LIFE"

    return None


def _attach_stats_for_game(df: pd.DataFrame,
                           mask: pd.Series,
                           game_code: str) -> pd.DataFrame:
    """
    Attach basic jackpot stats for rows where mask is True.

    Stats:
        jk_game_code
        jk_has_history
        jk_history_rows_total
        jk_draws_seen_to_date
        jk_days_since_last_draw
    """
    # Load + normalize history
    hist = load_jackpot(game_code)
    hist = normalize_history(hist)

    if hist.empty:
        # Nothing to attach; mark has_history = False
        df.loc[mask, "jk_game_code"] = game_code
        df.loc[mask, "jk_has_history"] = False
        df.loc[mask, "jk_history_rows_total"] = 0
        df.loc[mask, "jk_draws_seen_to_date"] = 0
        df.loc[mask, "jk_days_since_last_draw"] = pd.NA
        return df

    # Prepare history stats indexed by draw_date
    hist_stats = (
        hist[["draw_date"]]
        .drop_duplicates()
        .sort_values("draw_date")
        .reset_index(drop=True)
    )
    hist_stats = hist_stats.rename(columns={"draw_date": "jk_last_draw_date"})
    hist_stats["jk_draws_seen_to_date"] = (
        hist_stats.index + 1
    )  # 1-based count of draws

    # Subset forecast rows for this game
    sub = df.loc[mask].copy()
    sub = sub.sort_values("draw_date")

    # Align each forecast row with the most recent jackpot draw
    merged = pd.merge_asof(
        sub,
        hist_stats,
        left_on="draw_date",
        right_on="jk_last_draw_date",
        direction="backward",
    )

    # Compute days since last draw
    merged["jk_days_since_last_draw"] = (
        merged["draw_date"] - merged["jk_last_draw_date"]
    ).dt.days

    # Flag history presence
    merged["jk_has_history"] = merged["jk_last_draw_date"].notna()
    merged["jk_game_code"] = game_code
    merged["jk_history_rows_total"] = len(hist_stats)

    # Push columns back onto main df
    cols_to_copy = [
        "jk_game_code",
        "jk_has_history",
        "jk_history_rows_total",
        "jk_draws_seen_to_date",
        "jk_days_since_last_draw",
    ]

    df.loc[merged.index, cols_to_copy] = merged[cols_to_copy]

    return df


# ---------------------------------------------------------
# Public entry: enrich_forecast
# ---------------------------------------------------------

def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Top-level jackpot predictive enrichment.

    SAFE BEHAVIOR:
        - If no game column → returns df unchanged.
        - If no draw_date column → returns df unchanged.
        - Only modifies rows classified as jackpot games.

    New columns added (if applicable):
        jk_game_code
        jk_has_history
        jk_history_rows_total
        jk_draws_seen_to_date
        jk_days_since_last_draw
    """
    if df is None or df.empty:
        return df

    game_col = _detect_game_column(df)
    if game_col is None:
        # Not a forecast we recognize → leave untouched
        return df

    if "draw_date" not in df.columns:
        # We need draw_date to line up against history
        return df

    # Normalize date
    df["draw_date"] = pd.to_datetime(df["draw_date"])

    # Initialize columns so Scribe/Oracle see consistent schema
    if "jk_game_code" not in df.columns:
        df["jk_game_code"] = pd.NA
    if "jk_has_history" not in df.columns:
        df["jk_has_history"] = False
    if "jk_history_rows_total" not in df.columns:
        df["jk_history_rows_total"] = 0
    if "jk_draws_seen_to_date" not in df.columns:
        df["jk_draws_seen_to_date"] = 0
    if "jk_days_since_last_draw" not in df.columns:
        df["jk_days_since_last_draw"] = pd.NA

    # Classify each row
    df["jk_game_code"] = df[game_col].apply(_classify_jackpot_game)

    # For each jackpot game, attach stats
    for code in ["MEGAMILLIONS", "POWERBALL", "CASH4LIFE"]:
        mask = df["jk_game_code"] == code
        if mask.any():
            df = _attach_stats_for_game(df, mask, code)

    return df
