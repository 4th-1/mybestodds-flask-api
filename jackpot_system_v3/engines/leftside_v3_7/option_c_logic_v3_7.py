"""
option_c_logic_v3_7.py
----------------------

Lane C (Option C) Logic for v3.7 LEFT ENGINE.

Definition:
    Lane C = Lane B + Planetary Hour + Retailer Geo-Tagging

Role:
    This module does NOT replace your core scoring engine.
    Instead, it adds a *Lane C overlay* on top of any DataFrame
    that already contains your core features:

        • game, date, draw_time
        • digits, pattern flags
        • best_odds_score (if already computed)
        • retailer / geo fields (optional)

Outputs:
    Columns added:

        lane_c_flag           → "LANE_C_OK" / "LANE_C_WEAK" / "LANE_C_SKIP"
        lane_c_planetary_tag  → e.g. "PH-STRONG", "PH-NEUTRAL"
        lane_c_geo_tag        → e.g. "HOT_STORE", "HOT_ZIP", "NEUTRAL"
        lane_c_boost          → 0.0–0.35 (fractional boost recommendation)
        lane_c_notes          → hover text for Oracle / Scribe / dashboards
        lane_c_score          → OPTIONAL adjusted score if best_odds_score present

Design:
    • Pure overlay. Safe if planetary/geodata missing.
    • Mirrors v3.6 "Option C" intent but is cleaner & versioned.
    • Meant to be called AFTER:
        - daily_index_v3_7
        - playtype_rubik_v3_7
        - score_fx_v3_7

Usage:
    from engines.leftside_v3_7.option_c_logic_v3_7 import apply_lane_c_overlay

    df_lane_c = apply_lane_c_overlay(
        df_scored,
        hot_store_ids={"CHEVRON_4485_CAMPBELLTON"},
        hot_zip_prefixes={"30331", "30045"},
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, Set, Dict, Any

import pandas as pd


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

@dataclass
class LaneCConfig:
    """
    Tunable config for Lane C.

    All values are *fractions*, not absolute points.
    They are intended to be applied on top of a 0–100 score.
    """
    enable_planetary_hour: bool = True
    enable_geo_tagging: bool = True

    # Max contribution from each component (as fraction of 100)
    planetary_max_boost: float = 0.20   # up to +20 pts
    geo_max_boost: float = 0.15         # up to +15 pts

    # Global cap on Lane C boost
    lane_c_boost_cap: float = 0.35      # 35 pts max

    # Thresholds for labeling the lane
    strong_threshold: float = 0.20      # ≥20 pts boost → strong
    weak_threshold: float = 0.05        # 5–20 pts boost → weak, still playable


DEFAULT_LANE_C_CONFIG = LaneCConfig()


# ------------------------------------------------------------
# PLANETARY HOUR (PLACEHOLDER LOGIC)
# ------------------------------------------------------------

def planetary_hour_band(draw_time: str) -> (str, float):
    """
    Placeholder planetary-hour mapper.

    Because we are not pulling true ephemeris inside this module,
    we map the coarse draw_time band into a rough planetary "strength":

        MIDDAY  → strong (Sun/Jupiter style)
        EVENING → medium (Venus/Mercury style)
        NIGHT   → medium-weak (Moon/Saturn style)
        other   → neutral

    Returns:
        (tag_str, strength_fraction 0–1)

    NOTE:
        This is intentionally simple. The RIGHT ENGINE can later
        plug into your full astro engine and overwrite this logic
        without changing the Lane C interface.
    """
    if not isinstance(draw_time, str):
        return "PH-UNKNOWN", 0.0

    t = draw_time.strip().upper()

    if t in ("MID", "MIDDAY"):
        return "PH-STRONG", 1.0
    if t in ("EVENING", "EVE"):
        return "PH-MEDIUM", 0.7
    if t in ("NIGHT", "LATE"):
        return "PH-LOW", 0.4

    return "PH-NEUTRAL", 0.0


# ------------------------------------------------------------
# GEO-TAGGING (HOT STORE / HOT ZIP)
# ------------------------------------------------------------

def geo_band_for_row(
    row: pd.Series,
    hot_store_ids: Optional[Set[str]] = None,
    hot_zip_prefixes: Optional[Set[str]] = None,
) -> (str, float):
    """
    Determine geo band and strength based on retailer fields.

    Expected optional columns:
        • retailer_id
        • retailer_name
        • retailer_zip

    hot_store_ids:
        A set of retailer_id strings you trust the most.

    hot_zip_prefixes:
        A set like {"30331", "30045"} to mark key zip clusters.

    Returns:
        (tag_str, strength_fraction 0–1)
    """
    hot_store_ids = hot_store_ids or set()
    hot_zip_prefixes = hot_zip_prefixes or set()

    retailer_id = str(row.get("retailer_id", "") or "").strip().upper()
    retailer_zip = str(row.get("retailer_zip", "") or "").strip()

    # Highest signal: known hot store
    if retailer_id and retailer_id in hot_store_ids:
        return "HOT_STORE", 1.0

    # Next: zip prefix triggers
    for prefix in hot_zip_prefixes:
        if retailer_zip.startswith(prefix):
            return "HOT_ZIP", 0.7

    # Fall back to neutral if we have some retailer info
    if retailer_id or retailer_zip:
        return "GEO-NEUTRAL", 0.3

    # No geo data → no boost
    return "GEO-UNKNOWN", 0.0


# ------------------------------------------------------------
# MAIN OVERLAY
# ------------------------------------------------------------

def apply_lane_c_overlay(
    df: pd.DataFrame,
    config: LaneCConfig = DEFAULT_LANE_C_CONFIG,
    hot_store_ids: Optional[Iterable[str]] = None,
    hot_zip_prefixes: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """
    Apply Lane C overlay to a scored DataFrame.

    Inputs:
        df:
            DataFrame that SHOULD contain at least:
                • date
                • draw_time
            And ideally (but not required):
                • best_odds_score
                • retailer_id / retailer_zip

        config:
            LaneCConfig instance controlling boost weights.

        hot_store_ids:
            Iterable of known "power" retailers.

        hot_zip_prefixes:
            Iterable of zip prefixes (as strings) that you consider strong.

    Outputs:
        Returns a *new* DataFrame with these columns appended:

            lane_c_flag          (LANE_C_OK / LANE_C_WEAK / LANE_C_SKIP)
            lane_c_planetary_tag
            lane_c_geo_tag
            lane_c_boost         (0.0–0.35 fractional boost)
            lane_c_notes         (human-readable explanation)
            lane_c_score         (if best_odds_score exists, adjusted)
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    hot_store_ids_set = set([s.strip().upper() for s in (hot_store_ids or [])])
    hot_zip_prefixes_set = set([str(z) for z in (hot_zip_prefixes or [])])

    lane_flags = []
    lane_ph_tags = []
    lane_geo_tags = []
    lane_boosts = []
    lane_notes = []
    lane_scores = []

    has_base_score = "best_odds_score" in df.columns

    for _, row in df.iterrows():
        # --- Planetary hour component ---
        ph_tag = "PH-UNKNOWN"
        ph_strength = 0.0
        if config.enable_planetary_hour:
            ph_tag, ph_strength = planetary_hour_band(row.get("draw_time", ""))

        ph_boost = ph_strength * config.planetary_max_boost

        # --- Geo component ---
        geo_tag = "GEO-UNKNOWN"
        geo_strength = 0.0
        if config.enable_geo_tagging:
            geo_tag, geo_strength = geo_band_for_row(
                row,
                hot_store_ids=hot_store_ids_set,
                hot_zip_prefixes=hot_zip_prefixes_set,
            )

        geo_boost = geo_strength * config.geo_max_boost

        # --- Aggregate Lane C boost (capped) ---
        raw_boost = ph_boost + geo_boost
        lane_c_boost = min(raw_boost, config.lane_c_boost_cap)

        # --- Flag strength ---
        if lane_c_boost >= config.strong_threshold:
            flag = "LANE_C_OK"
        elif lane_c_boost >= config.weak_threshold:
            flag = "LANE_C_WEAK"
        else:
            flag = "LANE_C_SKIP"

        # --- Optional adjusted score ---
        base_score = float(row.get("best_odds_score", 0.0) or 0.0)
        adjusted_score = base_score
        if has_base_score:
            adjusted_score = max(0.0, min(base_score + lane_c_boost * 100.0, 100.0))

        # --- Notes for hover / tooltips ---
        note = (
            f"PH={ph_tag}({round(ph_boost*100,1)}pts) "
            f"| GEO={geo_tag}({round(geo_boost*100,1)}pts) "
            f"| TOTAL_BOOST={round(lane_c_boost*100,1)}pts "
            f"| FLAG={flag}"
        )

        lane_flags.append(flag)
        lane_ph_tags.append(ph_tag)
        lane_geo_tags.append(geo_tag)
        lane_boosts.append(round(lane_c_boost, 4))
        lane_notes.append(note)
        lane_scores.append(round(adjusted_score, 2))

    # Attach new columns
    df["lane_c_flag"] = lane_flags
    df["lane_c_planetary_tag"] = lane_ph_tags
    df["lane_c_geo_tag"] = lane_geo_tags
    df["lane_c_boost"] = lane_boosts
    df["lane_c_notes"] = lane_notes

    if has_base_score:
        df["lane_c_score"] = lane_scores

    return df


__all__ = [
    "LaneCConfig",
    "apply_lane_c_overlay",
]
