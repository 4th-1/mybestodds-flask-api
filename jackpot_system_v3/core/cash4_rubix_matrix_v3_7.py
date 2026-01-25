#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cash4_rubix_matrix_v3_7.py
---------------------------
Rubix Cube Matrix for Cash 4 (v3.7).

Defines core pattern archetypes for 4-digit numbers:

- UNIQUE      (ABCD)
- ONE_PAIR    (AABC)
- DOUBLE_PAIR (AABB)
- TRIPLE      (AAAB)
- QUAD        (AAAA)

Each pattern specifies:
- perm_count
- default_play_type
- rubix_play_type
- rubix_code
- rubix_bucket
- combo_allowed
- one_off_allowed
- pair_plays         (generally unused for Cash4; included for consistency)
- volatility
- confidence_hint
- bob_actions
- notes
"""

from collections import Counter

# =====================================================================
# HUMAN-FRIENDLY VIEW – CASH 4 PATTERN SUMMARY
# =====================================================================
#
# PATTERN       EXAMPLE   PERMS   DEFAULT PLAY     RUBIX TYPE   BUCKET
# ------------  --------  ------  ---------------  ----------   --------------------
# UNIQUE        1234      24-way  STRAIGHT         U-Type       High Variability
# ONE_PAIR      1123      12-way  BOX              P-Type       Moderate Variability
# DOUBLE_PAIR   1122      6-way   BOX              DP-Type      Low Variability
# TRIPLE        1112      4-way   STRAIGHT/BOX     T-Type       Repeating Digits
# QUAD          1111      1-way   STRAIGHT         Q-Type       Repeating Digits
#
# NOTES:
# - UNIQUE (ABCD): Straight preferred; Box and Combo are generally inefficient.
# - ONE_PAIR (AABC): Box recommended; Straight/Box/Combo reserved for strong overlays.
# - DOUBLE_PAIR (AABB): Box recommended; Combo can be strong on elite days.
# - TRIPLE (AAAB): Straight/Box recommended; excellent pattern for balanced risk/reward.
# - QUAD (AAAA): Straight only as base; Box/Combo give no extra benefit.
# =====================================================================


CASH4_RUBIX_MATRIX = {
    "UNIQUE": {
        "pattern": "UNIQUE",
        "example": "1234",
        "perm_count": 24,
        "default_play_type": "STRAIGHT",
        "rubix_play_type": "U-Type",
        "rubix_code": "U4",
        "rubix_bucket": "High Variability",
        "combo_allowed": False,          # 24-way combo too expensive normally
        "one_off_allowed": True,
        "pair_plays": [],
        "volatility": 0.85,
        "confidence_hint": 0.0,
        "bob_actions": [
            "ADD_BOX",                   # only if overlays justify a safety Box
            "ADD_1_OFF",
        ],
        "notes": (
            "4 unique digits (ABCD). Very high variability. Straight is the "
            "primary recommendation; Box/Combo only in rare, strong-overlay cases."
        ),
    },

    "ONE_PAIR": {
        "pattern": "ONE_PAIR",
        "example": "1123",
        "perm_count": 12,
        "default_play_type": "BOX",
        "rubix_play_type": "P-Type",
        "rubix_code": "P4",
        "rubix_bucket": "Moderate Variability",
        "combo_allowed": True,           # can be worthwhile with strong overlays
        "one_off_allowed": True,
        "pair_plays": [],
        "volatility": 0.70,
        "confidence_hint": 0.05,
        "bob_actions": [
            "ADD_BOX",
            "ADD_1_OFF",
        ],
        "notes": (
            "One pair with 2 distinct digits (AABC). 12-way Box pattern. "
            "Box is the base recommendation; Combo is reserved for high-confidence overlays."
        ),
    },

    "DOUBLE_PAIR": {
        "pattern": "DOUBLE_PAIR",
        "example": "1122",
        "perm_count": 6,
        "default_play_type": "BOX",
        "rubix_play_type": "DP-Type",
        "rubix_code": "DP4",
        "rubix_bucket": "Low Variability",
        "combo_allowed": True,
        "one_off_allowed": True,
        "pair_plays": [],
        "volatility": 0.55,
        "confidence_hint": 0.05,
        "bob_actions": [
            "ADD_BOX",
            "ADD_1_OFF",
        ],
        "notes": (
            "Two pairs (AABB). 6-way Box pattern. Strong candidate for Box as base "
            "and Combo when overlays and confidence are strong."
        ),
    },

    "TRIPLE": {
        "pattern": "TRIPLE",
        "example": "1112",
        "perm_count": 4,
        "default_play_type": "STRAIGHT/BOX",
        "rubix_play_type": "T-Type",
        "rubix_code": "T3",
        "rubix_bucket": "Repeating Digits",
        "combo_allowed": True,           # Combo can be powerful on triples
        "one_off_allowed": True,
        "pair_plays": [],
        "volatility": 0.80,
        "confidence_hint": 0.10,
        "bob_actions": [
            "ADD_BOX",
            "ADD_1_OFF",
            "ADD_COMBO",
        ],
        "notes": (
            "Triple (AAAB). 4-way Box pattern. Excellent candidate for STRAIGHT/BOX "
            "with BOB optionally upgrading to Combo under strong overlays."
        ),
    },

    "QUAD": {
        "pattern": "QUAD",
        "example": "1111",
        "perm_count": 1,
        "default_play_type": "STRAIGHT",
        "rubix_play_type": "Q-Type",
        "rubix_code": "Q1",
        "rubix_bucket": "Repeating Digits",
        "combo_allowed": False,          # no benefit over Straight
        "one_off_allowed": False,        # 1-Off less relevant for quads
        "pair_plays": [],
        "volatility": 0.75,
        "confidence_hint": 0.10,         # small boost due to pattern clarity
        "bob_actions": [
            "STRAIGHT_ONLY",
        ],
        "notes": (
            "Quad (AAAA). Only one true permutation. Straight is the dominant play. "
            "Box and Combo do not offer additional strategic advantage."
        ),
    },
}


# =====================================================================
#  HELPER FUNCTIONS
# =====================================================================

def classify_cash4_pattern(num: str) -> str:
    """
    Classify a 4-digit number into a Rubix pattern key:
        'UNIQUE', 'ONE_PAIR', 'DOUBLE_PAIR', 'TRIPLE', or 'QUAD'

    Assumes `num` is a 4-character string of digits.
    """
    num = str(num)
    if len(num) != 4:
        raise ValueError(f"Expected 4-digit number for Cash 4, got: {num}")

    c = Counter(num)
    vals = sorted(c.values(), reverse=True)
    unique = len(c)

    if unique == 4:
        return "UNIQUE"
    if vals == [2, 1, 1]:
        return "ONE_PAIR"
    if vals == [2, 2]:
        return "DOUBLE_PAIR"
    if vals == [3, 1]:
        return "TRIPLE"
    if vals == [4]:
        return "QUAD"

    # Fallback
    return "UNIQUE"


def get_cash4_rubix_profile(num: str) -> dict:
    """
    Returns the Rubix profile dict for the given Cash 4 number.

    Adds 'pattern_key' to the result for convenience.
    """
    pattern_key = classify_cash4_pattern(num)
    base = CASH4_RUBIX_MATRIX[pattern_key].copy()
    base["pattern_key"] = pattern_key
    base["number"] = str(num)
    return base
