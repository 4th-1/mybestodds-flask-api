#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jackpot_alignment_v4_0.py
-------------------------
Jackpot "timing & alignment" layer for v4.0 Right Engine (Option C).

Goal:
    - Take the predictive signals created in predictive_core_v4_0
    - Blend them with existing timing overlays (moon, zodiac, NN, etc.)
    - Produce a clean jackpot-specific alignment score + label.

IMPORTANT:
    - Applies ONLY to jackpot games:
        * MegaMillions
        * Powerball
        * Cash4Life
    - MMFSN overlays are intentionally NOT used here.
      (MMFSN remains a Cash3 / Cash4-only overlay for now.)

Usage:
    from core.jackpot_alignment_v4_0 import enrich_forecast
    df = enrich_forecast(df)
"""

from __future__ import annotations

import math
from typing import Iterable, Set

import pandas as pd

# ----------------------------------------------------------------------
#  CONFIG
# ----------------------------------------------------------------------

JACKPOT_GAMES: Set[str] = {"MegaMillions", "Powerball", "Cash4Life"}

# Columns we MAY use if present. All are optional/safe.
PRED_COL_BASE_PROB = "jk_base_prob"       # from predictive_core_v4_0 (optional)
PRED_COL_GAP_NORM  = "jk_gap_norm"        # normalized recency/gap (0–1 if present)

# Timing overlays that *might* already exist from v3.7 left engine
COL_MOON_SCORE     = "moon_weight"        # or whatever final moon-strength column name ended up as
COL_ZODIAC_MONEY   = "zodiac_money_score" # money-house alignment (if present)
COL_NN_WINDOW      = "nn_window_score"    # North Node timing score (if present)

# Output columns for this module
COL_ALIGN_SCORE    = "jk_alignment_score"
COL_ALIGN_BUCKET   = "jk_alignment_bucket"
COL_ALIGN_NOTE     = "jk_alignment_note"


# ----------------------------------------------------------------------
#  HELPER FUNCTIONS
# ----------------------------------------------------------------------

def _clamp01(x: float | int | None) -> float:
    """Clamp any numeric-ish input into [0, 1]."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.5  # neutral default
    try:
        x = float(x)
    except Exception:
        return 0.5
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _jackpot_alignment_row(row: pd.Series) -> pd.Series:
    """
    Compute jackpot alignment score + bucket + note for a single row.

    This is deliberately robust:
        - Every input is optional
        - If a column is missing, we fall back to neutral values
    """

    idx = row.index

    # --- Base predictive probability (from v4.0 core, if present) ---
    if PRED_COL_BASE_PROB in idx:
        base_prob = _clamp01(row[PRED_COL_BASE_PROB])
    else:
        base_prob = 0.5

    # --- Gap / recency normalized (if present) ---
    if PRED_COL_GAP_NORM in idx:
        gap_norm = _clamp01(row[PRED_COL_GAP_NORM])
    else:
        gap_norm = 0.5

    # --- Moon timing (if present) ---
    if COL_MOON_SCORE in idx:
        moon_score = _clamp01(row[COL_MOON_SCORE])
    else:
        moon_score = 0.5

    # --- Zodiac money-house alignment (if present) ---
    if COL_ZODIAC_MONEY in idx:
        zodiac_score = _clamp01(row[COL_ZODIAC_MONEY])
    else:
        zodiac_score = 0.5

    # --- North Node / destiny window (if present) ---
    if COL_NN_WINDOW in idx:
        nn_score = _clamp01(row[COL_NN_WINDOW])
    else:
        nn_score = 0.5

    # Combined “timing overlay” score (zodiac + NN)
    timing_combo = (zodiac_score + nn_score) / 2.0

    # ------------------------------------------------------------------
    #  BLEND WEIGHTS (can be tuned later)
    # ------------------------------------------------------------------
    # Weights must sum to 1.0
    w_base   = 0.45  # predictive core (recency / hit-rate)
    w_gap    = 0.20  # how "due" it is
    w_moon   = 0.15  # lunar timing
    w_timing = 0.20  # zodiac + NN destiny window

    alignment_score = (
        w_base   * base_prob +
        w_gap    * gap_norm +
        w_moon   * moon_score +
        w_timing * timing_combo
    )

    alignment_score = _clamp01(alignment_score)

    # ------------------------------------------------------------------
    #  BUCKET + NOTE
    # ------------------------------------------------------------------
    if alignment_score >= 0.75:
        bucket = "🟩 Jackpot Sweet Spot"
        note = "Strong jackpot timing window – premium alignment across signals."
    elif alignment_score >= 0.60:
        bucket = "🟨 Decent Window"
        note = "Good timing window – consider playing if budget and lane rules allow."
    elif alignment_score >= 0.45:
        bucket = "🤎 Weak Window"
        note = "Low alignment – only play if intuitively aligned or part of coverage."
    else:
        bucket = "🚫 Misaligned Window"
        note = "Poor timing – recommended to skip this jackpot draw."

    out = pd.Series(index=[COL_ALIGN_SCORE, COL_ALIGN_BUCKET, COL_ALIGN_NOTE], dtype="object")
    out[COL_ALIGN_SCORE] = float(alignment_score)
    out[COL_ALIGN_BUCKET] = bucket
    out[COL_ALIGN_NOTE] = note
    return out


# ----------------------------------------------------------------------
#  PUBLIC ENTRYPOINT
# ----------------------------------------------------------------------

def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich a full forecast DataFrame with jackpot alignment.

    - Leaves non-jackpot games untouched (alignment columns stay NaN).
    - Is safe to call multiple times (idempotent).
    - Does nothing if 'game_name' is missing.
    """

    if "game_name" not in df.columns:
        # We can't tell which rows are jackpots; bail out safely.
        return df

    df = df.copy()

    # Ensure alignment columns exist (even for non-jackpot rows)
    for col in (COL_ALIGN_SCORE, COL_ALIGN_BUCKET, COL_ALIGN_NOTE):
        if col not in df.columns:
            df[col] = pd.NA

    # Mask jackpot rows
    mask = df["game_name"].isin(JACKPOT_GAMES)
    if not mask.any():
        # No jackpot rows in this forecast – nothing to do
        return df

    # Compute alignment only for jackpot rows
    jackpot_slice = df.loc[mask]
    aligned = jackpot_slice.apply(_jackpot_alignment_row, axis=1)

    # aligned is a DataFrame with our 3 columns; write them back
    df.loc[mask, COL_ALIGN_SCORE] = aligned[COL_ALIGN_SCORE].values
    df.loc[mask, COL_ALIGN_BUCKET] = aligned[COL_ALIGN_BUCKET].values
    df.loc[mask, COL_ALIGN_NOTE] = aligned[COL_ALIGN_NOTE].values

    return df
