"""
score_fx_v3_7.py
-----------------------------------------------------
Core scoring engine for v3.7 LEFT ENGINE.

This file:
    • Computes Confidence Score
    • Computes WinLikelihoodScore (WLS)
    • Converts WLS to "1 in X" odds
    • Applies v3.7 color band rules
    • Aggregates all scoring components into a final score dict
    • Designed to match the structure & success of v3.6

Input:
    daily_row = a row from daily_index_v3_7 DataFrame

Output (dict):
    {
        "confidence_score": float,
        "wls": float,
        "odds_1_in": float,
        "odds_color": "green/yellow/tan/gray",
        "rank_score": float
    }

All labels/colors come from LEGEND, not hardcoded.
"""

from __future__ import annotations

import math
from typing import Dict, Any

from engines.leftside_v3_7.legend_mapper_v3_7 import LEGEND


# ============================================================
#  HELPERS
# ============================================================

def _safe(val, default=0.0):
    """Return val if valid, else default."""
    try:
        if val is None:
            return default
        if isinstance(val, float) and math.isnan(val):
            return default
    except:
        pass
    return val


# ============================================================
#  COMPONENT 1 — BASE CONFIDENCE (STRUCTURE)
# ============================================================

def compute_structure_score(row) -> float:
    """
    Structural factors based on:
        • sum range normalization
        • pattern flags
        • unique count
    """
    score = 0.0

    # Unique count
    uc = _safe(row.get("unique_count"))
    if uc == 3:
        score += 0.8
    elif uc == 2:
        score += 0.5
    else:
        score += 0.2

    # Patterns
    if row.get("has_double"):
        score += 0.3
    if row.get("has_triple"):
        score += 0.6
    if row.get("has_quad"):
        score += 1.0

    # Sum normalization
    sum_digits = _safe(row.get("sum_digits"))
    score += (sum_digits / 40.0)

    return round(score, 4)


# ============================================================
#  COMPONENT 2 — RECENCY / GAP METRICS
# ============================================================

def compute_gap_score(row) -> float:
    """
    Uses:
        • last_seen_gap
        • hit_index
        • rolling frequency
    """
    score = 0.0

    gap = _safe(row.get("last_seen_gap"), 10)
    roll_freq = _safe(row.get("roll_freq_last_N"), 0)
    hit_idx = _safe(row.get("hit_index"), 1)

    # Increasing gap = higher rebound probability
    score += min(gap / 20.0, 1.0)

    # Lower rolling frequency → higher rebound chance
    if roll_freq == 0:
        score += 0.8
    elif roll_freq == 1:
        score += 0.4
    else:
        score += 0.2

    # Hit index curve
    if hit_idx == 1:
        score += 0.5  # fresh number
    elif hit_idx == 2:
        score += 0.3

    return round(score, 4)


# ============================================================
#  COMPONENT 3 — WinLikelihoodScore (WLS)
# ============================================================

def compute_wls(conf_score: float) -> float:
    """
    Win Likelihood Score (WLS)
    A smooth logistic-curve approximation based solely on confidence.
    """
    wls = 1 / (1 + math.exp(-(conf_score - 2.2)))
    return round(wls, 6)


# ============================================================
#  COMPONENT 4 — Convert WLS → "1 in X" odds
# ============================================================

def compute_odds_from_wls(wls: float) -> float:
    """Convert likelihood to a 1-in-X format."""
    if wls <= 0:
        return 9999
    return round(1 / wls, 2)


# ============================================================
#  COMPONENT 5 — Map to Color Band (Legend-driven)
# ============================================================

def map_color_band(odds: float) -> str:
    """
    Use LEGEND score_bands to assign a color band.
    """
    if odds <= 50:
        return "green"
    if odds <= 150:
        return "yellow"
    if odds <= 300:
        return "tan"
    return "gray"


# ============================================================
#  MASTER — compute_full_score(row)
# ============================================================

def compute_full_score(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main scoring aggregator.
    Sent back to the PDF/Excel exporter and Oracle/Scribe dashboards.
    """

    # 1) structural
    s_score = compute_structure_score(row)

    # 2) gap-based
    g_score = compute_gap_score(row)

    # 3) combined confidence
    confidence = round(s_score + g_score, 4)

    # 4) likelihood
    wls = compute_wls(confidence)

    # 5) odds
    odds_one_in = compute_odds_from_wls(wls)

    # 6) color code
    color = map_color_band(odds_one_in)

    # 7) final ranking (weight structure heavier than gap)
    rank = round((s_score * 0.6) + (g_score * 0.4) + (wls * 2), 4)

    return {
        "confidence_score": confidence,
        "wls": wls,
        "odds_1_in": odds_one_in,
        "odds_color": color,
        "rank_score": rank,
    }


# ============================================================
# SMOKE TEST (Run directly)
# ============================================================

if __name__ == "__main__":
    sample = {
        "unique_count": 3,
        "has_double": 1,
        "has_triple": 0,
        "has_quad": 0,
        "sum_digits": 11,
        "last_seen_gap": 14,
        "hit_index": 2,
        "roll_freq_last_N": 0,
    }
    out = compute_full_score(sample)
    print("Sample Score Output:\n", out)
