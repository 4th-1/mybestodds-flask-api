#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
rubix_engine_v3_7.py
--------------------
My Best Odds v3.7 – Rubix Engine with AUTO-ROUTING by digit length.

This version fixes the Cash3/Cash4 misclassification issue entirely by:
    - If number length = 3 → use Cash 3 matrix
    - If number length = 4 → use Cash 4 matrix
    - Ignores (but logs) incorrect game labels
"""

import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.cash3_rubix_matrix_v3_7 import get_cash3_rubix_profile
from core.cash4_rubix_matrix_v3_7 import get_cash4_rubix_profile


# =====================================================================
#  PUBLIC API – AUTO ROUTING ENABLED
# =====================================================================

def compute_rubix(game: str, number: str) -> dict:
    """
    Compute Rubix properties for a given game + number.

    AUTO-ROUTING LOGIC:
        - If number has 3 digits → Cash 3 matrix
        - If number has 4 digits → Cash 4 matrix
        - Otherwise → error (invalid number)

    The `game` field is no longer trusted for routing.
    """

    n = str(number).strip()

    if not n.isdigit():
        raise ValueError(f"Invalid number (not digits): {n}")

    # ---------------------------------------------------------
    # AUTO-DETECT game based on number length
    # ---------------------------------------------------------
    if len(n) == 3:
        # Always treat as Cash 3
        profile = get_cash3_rubix_profile(n)
    elif len(n) == 4:
        # Always treat as Cash 4
        profile = get_cash4_rubix_profile(n)
    else:
        raise ValueError(
            f"Rubix Engine cannot classify number with length {len(n)}: {n}"
        )

    # ---------------------------------------------------------
    # Build standard Rubix structure
    # ---------------------------------------------------------
    return {
        "play_type":        profile.get("default_play_type", ""),
        "play_type_rubix":  profile.get("rubix_play_type", ""),
        "rubix_code":       profile.get("rubix_code", ""),
        "rubix_bucket":     profile.get("rubix_bucket", ""),
        "perm_count":       profile.get("perm_count", 0),
        "volatility":       profile.get("volatility", 0.0),
        "confidence_hint":  profile.get("confidence_hint", 0.0),
        "bob_actions":      profile.get("bob_actions", []),
        "pattern_key":      profile.get("pattern_key", profile.get("pattern", "")),
        "notes":            profile.get("notes", ""),
    }


# =====================================================================
#  INTEGRATION LAYER
# =====================================================================

def apply_rubix_to_row(row: dict) -> dict:
    """
    Apply Rubix data directly to a forecast row.

    Now ignores row['game'] for classification purposes.
    """
    number = str(row.get("number", "")).strip()
    rubix = compute_rubix(row.get("game", ""), number)

    # Required export fields
    row["play_type"]       = rubix["play_type"]
    row["play_type_rubix"] = rubix["play_type_rubix"]
    row["rubik_code"]      = rubix["rubix_code"]
    row["rubik_bucket"]    = rubix["rubix_bucket"]

    # Metadata
    row["perm_count"]            = rubix["perm_count"]
    row["rubix_volatility"]      = rubix["volatility"]
    row["rubix_confidence_hint"] = rubix["confidence_hint"]
    row["rubix_bob_actions"]     = ",".join(rubix["bob_actions"])
    row["rubix_pattern_key"]     = rubix["pattern_key"]
    row["rubix_notes"]           = rubix["notes"]

    return row


# =====================================================================
# SELF-TEST
# =====================================================================
if __name__ == "__main__":
    tests = ["123", "122", "111", "1234", "1123", "1122", "1112", "1111"]
    for t in tests:
        out = compute_rubix("", t)
        print(t, "->", out)
