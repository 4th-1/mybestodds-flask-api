#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
elite_layer_v3_7.py
--------------------
Option C – Elite Interpretation & Notification Layer

This layer sits *after*:
    - predictive_core_v3_7.enrich_forecast
    - personalization_layer_v3_7.enrich_forecast
    - final_selector_v3_7.enrich_forecast

Goals:
    - Translate raw scores into:
        * cycle momentum
        * peak window flags
        * trend-break flags
        * notification tiers (for Base44)
        * short subscriber-facing explanations

    - Do NOT change any upstream columns.
    - Only ADD new columns.
"""

from __future__ import annotations

import pandas as pd
from typing import Any


def _safe_get(series: pd.Series, default: float = 0.0) -> pd.Series:
    """Return series, filled with default if missing or all-NaN."""
    if series is None:
        return pd.Series(default, index=pd.RangeIndex(0))
    if series.empty:
        return series
    return series.fillna(default)


def _compute_cycle_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a simple rolling 'cycle_momentum' per (game, draw_time).

    Uses posterior_p (if present), else falls back to ml_score,
    else falls back to confidence_score.
    """
    df = df.copy()

    # Choose base metric for momentum
    metric_candidates = ["posterior_p", "ml_score", "confidence_score"]
    base_col = None
    for c in metric_candidates:
        if c in df.columns:
            base_col = c
            break

    if base_col is None:
        # Nothing to compute momentum from; create flat column
        df["cycle_momentum_raw"] = 0.0
        df["cycle_momentum_band"] = "Unknown"
        return df

    # Make sure numeric
    df[base_col] = pd.to_numeric(df[base_col], errors="coerce").fillna(0.0)

    # Sort for rolling window
    if "draw_date" in df.columns:
        df["_draw_date_dt"] = pd.to_datetime(df["draw_date"], errors="coerce")
    else:
        df["_draw_date_dt"] = pd.NaT

    df.sort_values(
        by=["game", "draw_time", "_draw_date_dt", base_col],
        inplace=True
    )

    # Rolling mean per game/time over last N draws (e.g., 12)
    window = 12

    df["cycle_momentum_raw"] = (
        df.groupby(["game", "draw_time"])[base_col]
          .rolling(window=window, min_periods=3)
          .mean()
          .reset_index(level=[0, 1], drop=True)
    ).fillna(0.0)

    # Banding: relative to global quantiles
    q_low = df["cycle_momentum_raw"].quantile(0.33)
    q_mid = df["cycle_momentum_raw"].quantile(0.66)

    def _band(x: float) -> str:
        if x <= q_low:
            return "Cooling"
        elif x <= q_mid:
            return "Stable"
        else:
            return "Heating"

    df["cycle_momentum_band"] = df["cycle_momentum_raw"].apply(_band)

    # Clean temp
    df.drop(columns=["_draw_date_dt"], inplace=True, errors="ignore")
    return df


def _compute_peak_window_and_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute:
        - peak_window_flag: True when odds & confidence align
        - trend_break_flag: True when score deviates sharply from local momentum
    """
    df = df.copy()

    # Ensure required cols exist
    for col in ["confidence_score", "mbo_odds", "cycle_momentum_raw"]:
        if col not in df.columns:
            df[col] = 0.0

    df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0.0)
    df["mbo_odds"] = pd.to_numeric(df["mbo_odds"], errors="coerce").fillna(9999.0)
    df["cycle_momentum_raw"] = pd.to_numeric(df["cycle_momentum_raw"], errors="coerce").fillna(0.0)

    # Peak window if:
    #   - confidence_score is relatively high
    #   - mbo_odds are relatively favorable
    conf_q = df["confidence_score"].quantile(0.70)
    odds_q = df["mbo_odds"].quantile(0.40)  # lower is better

    df["peak_window_flag"] = (
        (df["confidence_score"] >= conf_q) &
        (df["mbo_odds"] <= odds_q)
    )

    # Trend-break when confidence deviates from local rolling mean
    if "draw_date" in df.columns:
        df["_draw_date_dt"] = pd.to_datetime(df["draw_date"], errors="coerce")
    else:
        df["_draw_date_dt"] = pd.NaT

    df.sort_values(
        by=["game", "draw_time", "_draw_date_dt", "confidence_score"],
        inplace=True
    )

    roll = (
        df.groupby(["game", "draw_time"])["confidence_score"]
          .rolling(window=10, min_periods=4)
          .mean()
          .reset_index(level=[0, 1], drop=True)
    ).fillna(df["confidence_score"].mean())

    df["trend_delta"] = df["confidence_score"] - roll
    # Trend break if delta is in top 10% absolute deviation
    threshold = df["trend_delta"].abs().quantile(0.90)
    df["trend_break_flag"] = df["trend_delta"].abs() >= threshold

    df.drop(columns=["_draw_date_dt"], inplace=True, errors="ignore")
    return df


def _compute_notification_tier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign a 0–3 notification tier for Base44:

        3 – 🔥 High-priority alert (push + SMS)
        2 – ✅ Normal priority (push only)
        1 – 👀 Low priority (in-app highlight)
        0 – 👤 Background (no proactive alert)
    """
    df = df.copy()

    for col in ["confidence_score", "mbo_odds", "peak_window_flag"]:
        if col not in df.columns:
            if col == "peak_window_flag":
                df[col] = False
            else:
                df[col] = 0.0

    df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0.0)
    df["mbo_odds"] = pd.to_numeric(df["mbo_odds"], errors="coerce").fillna(9999.0)

    # Base tiers
    conditions = []

    # Tier 3 – elite
    tier3 = (
        (df["peak_window_flag"] == True) &
        (df["confidence_score"] >= df["confidence_score"].quantile(0.80)) &
        (df["mbo_odds"] <= df["mbo_odds"].quantile(0.30))
    )
    conditions.append(("notification_tier", 3, tier3))

    # Tier 2 – solid plays
    tier2 = (
        (df["confidence_score"] >= df["confidence_score"].quantile(0.60)) &
        (~tier3)
    )
    conditions.append(("notification_tier", 2, tier2))

    # Tier 1 – mild interest
    tier1 = (
        (df["confidence_score"] >= df["confidence_score"].quantile(0.40)) &
        (~tier3) & (~tier2)
    )
    conditions.append(("notification_tier", 1, tier1))

    # Default 0
    df["notification_tier"] = 0
    for col, val, mask in conditions:
        df.loc[mask, col] = val

    return df


def _build_short_explanation(row: pd.Series) -> str:
    """
    One-line, subscriber-facing summary.
    """
    parts = []

    game = row.get("game", "")
    time = row.get("draw_time", "")
    conf = row.get("confidence_score", 0.0)
    odds = row.get("mbo_odds", 0.0)
    band = row.get("cycle_momentum_band", "")
    peak = bool(row.get("peak_window_flag", False))
    trend_break = bool(row.get("trend_break_flag", False))

    if game:
        parts.append(str(game))
    if time:
        parts.append(f"({time})")

    header = " ".join(p for p in parts if p).strip()
    if header:
        header += ": "

    detail_bits = []

    if conf:
        detail_bits.append(f"Confidence ~ {conf:.0f}/100")
    if odds:
        detail_bits.append(f"Best Odds ~ 1-in-{int(odds):,}")
    if band:
        detail_bits.append(f"Cycle: {band}")

    if peak:
        detail_bits.append("🚀 Peak Window")
    if trend_break:
        detail_bits.append("⚠ Trend Break (watch closely)")

    if not detail_bits:
        return header + "No special signals."

    return header + " • ".join(detail_bits)


def _build_long_explanation(row: pd.Series) -> str:
    """
    Multi-sentence, human-readable interpretation.
    """
    game = row.get("game", "")
    time = row.get("draw_time", "")
    conf = row.get("confidence_score", 0.0)
    odds = row.get("mbo_odds", 0.0)
    band = row.get("cycle_momentum_band", "")
    peak = bool(row.get("peak_window_flag", False))
    trend_break = bool(row.get("trend_break_flag", False))
    tier = int(row.get("notification_tier", 0))

    base = f"For {game} {time}, "

    msg_parts = []

    # Confidence + odds
    msg_parts.append(
        f"your system is reading a confidence level around {conf:.0f} out of 100 "
        f"with an estimated Best Odds of about 1-in-{int(odds):,}."
    )

    if band:
        msg_parts.append(
            f"This number’s recent cycle momentum is classified as **{band}**, "
            "based on how it has behaved across prior draws in this lane."
        )

    if peak:
        msg_parts.append(
            "This draw is landing inside a **Peak Window**, where timing, overlays, "
            "and scoring are synchronizing in your favor."
        )

    if trend_break:
        msg_parts.append(
            "We’re also detecting a **Trend Break**, meaning today’s pattern differs "
            "sharply from recent behavior — this can precede meaningful moves."
        )

    # Notification tier guidance
    tier_msg = {
        3: "This ranks as a **Tier 3 High-Priority Alert** — it deserves your closest attention.",
        2: "This ranks as a **Tier 2 Solid Opportunity** — a strong candidate for disciplined play.",
        1: "This ranks as a **Tier 1 Watchlist Signal** — worth noting, but not a must-play.",
        0: "This ranks as a **Tier 0 Background Signal** — no alert recommended at this time.",
    }.get(tier, "No special alert is recommended for this draw.")

    msg_parts.append(tier_msg)

    return base + " ".join(msg_parts)


def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Public entry-point.

    Input:
        df – forecast DataFrame *after* predictive, personalization, selector.

    Output:
        df with new columns:
            - cycle_momentum_raw
            - cycle_momentum_band
            - peak_window_flag
            - trend_break_flag
            - trend_delta
            - notification_tier
            - explanation_short
            - explanation_long
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    # 1) Cycle momentum
    df = _compute_cycle_momentum(df)

    # 2) Peak window & trend break
    df = _compute_peak_window_and_trend(df)

    # 3) Notification tier
    df = _compute_notification_tier(df)

    # 4) Explanations
    df["explanation_short"] = df.apply(_build_short_explanation, axis=1)
    df["explanation_long"] = df.apply(_build_long_explanation, axis=1)

    return df
