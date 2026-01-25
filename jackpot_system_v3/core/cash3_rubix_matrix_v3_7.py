#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cash3_rubix_matrix_v3_7.py
---------------------------
Rubix Cube Matrix for Cash 3 (v3.7).

Defines core pattern archetypes for 3-digit numbers:

- UNIQUE (ABC)
- ONE_PAIR (AAB)
- TRIPLE (AAA)

Each pattern specifies:
- perm_count         (how many permutations matter for Box/Combo logic)
- default_play_type  (best base recommendation)
- rubix_play_type    (U-Type, P-Type, T-Type)
- rubix_code         (U3, P3, T1, etc.)
- rubix_bucket       (volatility bucket)
- combo_allowed      (if Combo can be a smart recommendation)
- one_off_allowed    (1-Off worth suggesting?)
- pair_plays         (Front/Back Pair relevance)
- volatility         (0–1 rough scale)
- confidence_hint    (suggested confidence adjustment weight)
- bob_actions        (which BOB overlays are “legal” for this pattern)
- notes              (human-readable description)

This file is the *source of truth* for Cash 3 pattern intelligence.
"""

from collections import Counter

# =====================================================================
# HUMAN-FRIENDLY VIEW (for your eyes) – CASH 3 PATTERN SUMMARY
# =====================================================================
#
# PATTERN    EXAMPLE   PERMS   DEFAULT PLAY   RUBIX TYPE   BUCKET
# ---------  --------  ------  -------------  ----------   -------------------
# UNIQUE     123       6-way   STRAIGHT       U-Type       High Variability
# ONE_PAIR   122       3-way   STRAIGHT/BOX   P-Type       Moderate Variability
# TRIPLE     111       1-way   STRAIGHT/BOX   T-Type       Repeating Digits
#
# NOTES:
# - UNIQUE (ABC):
#       Highest variability, most perms.
#       Straight gives best payout; Box used as safety via BOB.
# - ONE_PAIR (AAB):
#       3-way patterns. Great candidates for Straight/Box and 1-Off.
#       Strong Back/Front Pair opportunities.
# - TRIPLE (AAA):
#       Hyper-focused pattern. Only one exact perm.
#       STRAIGHT/BOX + 1-Off + Pair plays are powerful.
# =====================================================================


CASH3_RUBIX_MATRIX = {
    "UNIQUE": {
        "pattern": "UNIQUE",
        "example": "123",
        "perm_count": 6,
        "default_play_type": "STRAIGHT",
        "rubix_play_type": "U-Type",
        "rubix_code": "U3",
        "rubix_bucket": "High Variability",
        "combo_allowed": False,          # Combo too costly for 6 perms normally
        "one_off_allowed": True,
        "pair_plays": [],                # No built-in pair play
        "volatility": 0.85,              # high spread
        "confidence_hint": 0.0,          # neutral; overlay drives confidence
        "bob_actions": [
            "ADD_BOX",
            "ADD_1_OFF",
        ],
        "notes": (
            "3 unique digits (ABC). Best base play is STRAIGHT. "
            "Box is mainly safety via BOB, especially on high-overlay days."
        ),
    },

    "ONE_PAIR": {
        "pattern": "ONE_PAIR",
        "example": "122",
        "perm_count": 3,
        "default_play_type": "STRAIGHT/BOX",
        "rubix_play_type": "P-Type",
        "rubix_code": "P3",
        "rubix_bucket": "Moderate Variability",
        "combo_allowed": True,           # Combo sometimes viable on strong overlays
        "one_off_allowed": True,
        "pair_plays": ["FRONT_PAIR", "BACK_PAIR"],
        "volatility": 0.65,
        "confidence_hint": 0.05,         # mild positive bump
        "bob_actions": [
            "ADD_BOX",
            "ADD_1_OFF",
            "ADD_BACK_PAIR",
            "ADD_FRONT_PAIR",
        ],
        "notes": (
            "One pair + one distinct digit (AAB). Excellent for Straight/Box. "
            "Pairs and 1-Off become strong near-miss protection."
        ),
    },

    "TRIPLE": {
        "pattern": "TRIPLE",
        "example": "111",
        "perm_count": 1,                 # effectively 1 combo, even if box is allowed
        "default_play_type": "STRAIGHT/BOX",
        "rubix_play_type": "T-Type",
        "rubix_code": "T1",
        "rubix_bucket": "Repeating Digits",
        "combo_allowed": False,          # Combo is overkill for triples
        "one_off_allowed": True,
        "pair_plays": ["FRONT_PAIR", "BACK_PAIR"],
        "volatility": 0.90,              # rare but high-impact
        "confidence_hint": 0.10,         # small positive boost when overlays support it
        "bob_actions": [
            "ADD_1_OFF",
            "ADD_BACK_PAIR",
            "ADD_FRONT_PAIR",
        ],
        "notes": (
            "All digits the same (AAA). Best play is STRAIGHT/BOX with BOB "
            "adding 1-Off and pair plays on strong overlay days."
        ),
    },
}


# =====================================================================
#  HELPER FUNCTIONS
# =====================================================================

def classify_cash3_pattern(num: str) -> str:
    """
    Classify a 3-digit number into a Rubix pattern key:
        'UNIQUE', 'ONE_PAIR', or 'TRIPLE'

    Assumes `num` is a 3-character string of digits.
    """
    num = str(num)
    if len(num) != 3:
        raise ValueError(f"Expected 3-digit number for Cash 3, got: {num}")

    c = Counter(num)
    unique = len(c)

    if unique == 3:
        return "UNIQUE"
    if unique == 2:
        return "ONE_PAIR"
    if unique == 1:
        return "TRIPLE"

    # Fallback (should never happen for 3 digits)
    return "UNIQUE"


def get_cash3_rubix_profile(num: str) -> dict:
    """
    Returns the Rubix profile dict for the given Cash 3 number.

    Adds 'pattern_key' to the result for convenience.
    """
    pattern_key = classify_cash3_pattern(num)
    base = CASH3_RUBIX_MATRIX[pattern_key].copy()
    base["pattern_key"] = pattern_key
    base["number"] = str(num)
    return base
