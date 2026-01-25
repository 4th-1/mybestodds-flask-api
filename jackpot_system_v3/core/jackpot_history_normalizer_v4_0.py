#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jackpot_history_normalizer_v4_0.py
----------------------------------
Ensures jackpot history data is properly structured.

Output Schema (minimum required for predictive engine):
    draw_date
    main_1 ... main_5 (or 1..5)
    mega_ball / powerball / cashball
"""

import pandas as pd


def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize jackpot results into a clean consistent set."""

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Make sure draw_date exists
    if "draw_date" not in df.columns:
        return pd.DataFrame()

    # Try to detect main numbers
    main_cols = [c for c in df.columns if c.lower().startswith("main_")]

    # If not found, fallback: look for numeric positions
    if not main_cols:
        possible = [c for c in df.columns if c.lower() in ["n1", "n2", "n3", "n4", "n5"]]
        if possible:
            df.rename(columns={
                "n1": "main_1",
                "n2": "main_2",
                "n3": "main_3",
                "n4": "main_4",
                "n5": "main_5",
            }, inplace=True)
            main_cols = ["main_1", "main_2", "main_3", "main_4", "main_5"]

    # Ball column
    lower_cols = {c.lower(): c for c in df.columns}
    ball_col = None

    for key in ["mega_ball", "powerball", "cashball", "bonus"]:
        if key in lower_cols:
            ball_col = lower_cols[key]
            break

    # Build normalized output
    cols = ["draw_date"]
    if main_cols:
        cols += main_cols
    if ball_col:
        cols.append(ball_col)

    df = df[cols].dropna(subset=["draw_date"]).reset_index(drop=True)

    return df
