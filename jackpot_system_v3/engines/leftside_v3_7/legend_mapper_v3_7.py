"""
legend_mapper_v3_7.py
---------------------------------------------

Purpose:
    Central legend dictionary for all UI-facing labels in v3.7.

This file ensures:
    • Consistent text in PDFs, Excel, Oracle, Scribe, Sentinel
    • Unified color codes
    • Unified lane flags (A, B, C, D)
    • Unified odds bands ("1 in X" → color rules)
    • Unified pattern labels (double, triple, quad)
    • Unified playtype labels (Straight, Box, Str/Box, Back Pair)
    • Unified BOB (Best Odds Bonus) legend
    • Unified Lane C labels

NO MATH occurs in this file.
It only provides TEXT & COLOR MAPPINGS that the engines reference.

Import usage:
    from engines.leftside_v3_7.legend_mapper_v3_7 import LEGEND, get_legend_entry
"""

from __future__ import annotations
from typing import Dict, Any

# ------------------------------------------------------------
# BASE LEGEND STRUCTURE
# ------------------------------------------------------------

LEGEND: Dict[str, Dict[str, Any]] = {

    # --------------------------------------------------------
    # SCORE COLOR BANDS (Applies across Cash 3, Cash 4, MM, PB)
    # --------------------------------------------------------
    "score_bands": {
        "green": {
            "range": "1–50",
            "description": "Strong Signal — Play Confidently",
            "color": "#00C851",
        },
        "yellow": {
            "range": "51–150",
            "description": "Decent Edge — Play Cautiously",
            "color": "#ffbb33",
        },
        "tan": {
            "range": "151–300",
            "description": "Low Odds — Only if Intuitively Aligned",
            "color": "#d2b48c",
        },
        "gray": {
            "range": "301+",
            "description": "Skip Zone — Extremely Low Probability",
            "color": "#9e9e9e",
        },
    },

    # --------------------------------------------------------
    # PLAYTYPE LEGEND
    # --------------------------------------------------------
    "playtype": {
        "STRAIGHT": "Straight (Exact Order)",
        "BOX": "Box (Any Order)",
        "STRBOX": "Straight/Box",
        "BACKPAIR": "Back Pair",
        "FRONTPAIR": "Front Pair",
        "1OFF": "1-Off Option",
    },

    # --------------------------------------------------------
    # PATTERN LEGEND
    # --------------------------------------------------------
    "pattern": {
        "double": "One pair of matching digits",
        "triple": "Three matching digits",
        "quad": "Four matching digits",
        "unique": "All digits different",
    },

    # --------------------------------------------------------
    # BOB (Best Odds Bonus)
    # --------------------------------------------------------
    "bob": {
        "ADD_BOX": "Add Box for Safety",
        "ADD_BACKPAIR": "Add Back Pair Only",
        "ADD_1OFF": "1-Off Boost Suggested",
        "NO_BOB": "Straight Only (No BOB)",
        "BOB_STRONG": "BOB Strong: Add Combo (High Return)",
        "description": (
            "BOB is your internal smart-checker. He boosts safety on near-misses "
            "or pattern-risk draws WITHOUT changing your main pick."
        ),
    },

    # --------------------------------------------------------
    # LANE LABELS
    # --------------------------------------------------------
    "lanes": {
        "A": "Lane A — Raw Analytics",
        "B": "Lane B — Numerology + Spiritual Overlay",
        "C": "Lane C — Planetary Hour + Geo-Tagging",
        "D": "Lane D — DreamSync / Intuitive Overlay",
    },

    # --------------------------------------------------------
    # LANE C (OPTION C)
    # --------------------------------------------------------
    "lane_c": {
        "LANE_C_OK": {
            "description": "Lane C Strong Alignment",
            "color": "#00C851",
        },
        "LANE_C_WEAK": {
            "description": "Lane C Mild Alignment",
            "color": "#ffbb33",
        },
        "LANE_C_SKIP": {
            "description": "Lane C Skip — No Advantage",
            "color": "#9e9e9e",
        },
    },

    # --------------------------------------------------------
    # PLANETARY HOUR TAGS
    # --------------------------------------------------------
    "planetary": {
        "PH-STRONG": "Planetary Hour Strong",
        "PH-MEDIUM": "Planetary Hour Medium",
        "PH-LOW": "Planetary Hour Low",
        "PH-NEUTRAL": "Planetary Hour Neutral",
        "PH-UNKNOWN": "Planetary Hour Undetermined",
    },

    # --------------------------------------------------------
    # GEO-TAGGING LABELS (Hot stores / Zip clusters)
    # --------------------------------------------------------
    "geo": {
        "HOT_STORE": "High-Performance Retailer",
        "HOT_ZIP": "High-Performance Zip Zone",
        "GEO-NEUTRAL": "Neutral Retailer",
        "GEO-UNKNOWN": "No Retailer Data",
    },

    # --------------------------------------------------------
    # CONFIDENCE LABELS
    # --------------------------------------------------------
    "confidence": {
        "HIGH": "High Alignment",
        "MEDIUM": "Moderate Alignment",
        "LOW": "Low Alignment",
        "NONE": "No Alignment",
    },
}


# ------------------------------------------------------------
# HELPER FUNCTION
# ------------------------------------------------------------

def get_legend_entry(section: str, key: str) -> Any:
    """
    Safe accessor for legend entries.
    Example:
        get_legend_entry("bob", "ADD_BACKPAIR")
    """
    sec = LEGEND.get(section, {})
    return sec.get(key, f"[Unknown legend key: {section}.{key}]")
