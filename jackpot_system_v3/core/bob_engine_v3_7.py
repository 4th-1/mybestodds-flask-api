#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bob_engine_v3_7.py
------------------
Step 5C of Option C – Best Odds Bonus (BOB) logic for My Best Odds v3.7.

BOB NEVER changes the core pick.
It only suggests an extra play-type overlay such as:

- Add Box for Safety
- Add Back Pair Only
- Add Front Pair Only
- Add 1-Off
- Straight Only (No BOB)
- BOB Strong: Add Combo (High Return)

Outputs:
    bob_action  (machine-friendly code)
    bob_note    (subscriber-facing explanation)
"""

from collections import Counter


# ---------------------------------------------------------------------
# Utility: safe parse overlay_score (string -> float 0–1)
# ---------------------------------------------------------------------
def _parse_score(val, default=0.5):
    try:
        f = float(val)
        if f < 0:
            return 0.0
        if f > 1:
            return 1.0
        return f
    except Exception:
        return default


# ---------------------------------------------------------------------
# Digit helpers
# ---------------------------------------------------------------------
def _is_quad(num: str) -> bool:
    return len(num) == 4 and len(set(num)) == 1


def _is_triple(num: str) -> bool:
    return len(Counter(num).values()) <= 3 and 3 in Counter(num).values()


def _has_double_pair(num: str) -> bool:
    c = Counter(num)
    return len(num) == 4 and sorted(c.values(), reverse=True) == [2, 2]


def _has_one_pair(num: str) -> bool:
    c = Counter(num)
    return 2 in c.values() and not _has_double_pair(num) and not _is_triple(num)


def _front_pair_candidate(num: str) -> bool:
    """First two digits same, last digit different (Cash3)."""
    return len(num) == 3 and num[0] == num[1] and num[1] != num[2]


def _back_pair_candidate(num: str) -> bool:
    """Last two digits same, first digit different (Cash3)."""
    return len(num) == 3 and num[1] == num[2] and num[0] != num[1]


# ---------------------------------------------------------------------
# Mapping bob_action -> bob_note (defaults)
# ---------------------------------------------------------------------
DEFAULT_BOB_NOTES = {
    "NO_BOB": "",
    "ADD_BOX": "Add Box for safety.",
    "ADD_BACK_PAIR": "Add Back Pair only.",
    "ADD_FRONT_PAIR": "Add Front Pair only.",
    "ADD_1_OFF": "Add 1-Off for near-miss protection.",
    "ADD_COMBO": "BOB Strong: Add Combo (High Return).",
    "STRAIGHT_ONLY": "Straight Only (No BOB) – optimal play for this pattern.",
}


# ---------------------------------------------------------------------
# Core Best Odds Bonus Logic
# ---------------------------------------------------------------------
def compute_bob(
    game: str,
    number: str,
    play_type: str,
    rubik_bucket: str,
    overlay_score: str,
) -> dict:
    """
    Main public API.

    Inputs:
        game          - 'Cash3' or 'Cash4' (case-insensitive)
        number        - digit string, e.g. '406', '1112'
        play_type     - base play type from Rubik engine ('STRAIGHT', 'BOX', 'STRAIGHT/BOX', etc.)
        rubik_bucket  - volatility classification ('High Variability', 'Repeating Digits', etc.)
        overlay_score - string representation of 0–1 overlay score

    Returns:
        {
            "bob_action": <code>,
            "bob_note": <subscriber-facing text>
        }
    """
    g = (game or "").strip().lower()
    num = (number or "").strip()
    rb = (rubik_bucket or "").strip()
    pt = (play_type or "").strip().upper()
    o = _parse_score(overlay_score)

    # ---------------------------------------------------------------
    # RULE 0 – Default
    # ---------------------------------------------------------------
    bob_action = "NO_BOB"
    bob_note = DEFAULT_BOB_NOTES[bob_action]

    # ---------------------------------------------------------------
    # RULE 1 – Cash4 Quad: Straight Only, never alter
    # ---------------------------------------------------------------
    if g == "cash4" and _is_quad(num):
        bob_action = "STRAIGHT_ONLY"
        bob_note = DEFAULT_BOB_NOTES[bob_action]
        return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # RULE 2 – High overlay + high volatility: protect with Box / 1-Off
    # ---------------------------------------------------------------
    high_overlay = o >= 0.75
    med_overlay = 0.55 <= o < 0.75
    low_overlay = o < 0.55

    high_var_bucket = rb in ("High Variability", "Repeating Digits")
    low_var_bucket = rb in ("Low Variability",)

    # If straight-only call with high risk pattern -> add Box safety
    if pt == "STRAIGHT" and high_var_bucket and (med_overlay or high_overlay):
        bob_action = "ADD_BOX"
        bob_note = "Add Box for Safety on a high-variability pattern."
        return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # RULE 3 – Cash3 Pair Opportunities (Front/Back Pair)
    # ---------------------------------------------------------------
    if g == "cash3":
        # Back Pair
        if _back_pair_candidate(num) and (med_overlay or high_overlay):
            bob_action = "ADD_BACK_PAIR"
            bob_note = "Add Back Pair Only – strong ending pair setup."
            return {"bob_action": bob_action, "bob_note": bob_note}

        # Front Pair
        if _front_pair_candidate(num) and (med_overlay or high_overlay):
            bob_action = "ADD_FRONT_PAIR"
            bob_note = "Add Front Pair Only – strong starting pair setup."
            return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # RULE 4 – 1-Off coverage for strong but risky numbers
    # ---------------------------------------------------------------
    if high_overlay and high_var_bucket and pt in ("STRAIGHT", "STRAIGHT/BOX"):
        bob_action = "ADD_1_OFF"
        bob_note = "Add 1-Off for premium near-miss protection."
        return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # RULE 5 – BOB STRONG: Add Combo on elite setups
    # (Very high overlay + good bucket + strong base play)
    # ---------------------------------------------------------------
    if o >= 0.85 and rb in ("High Variability", "Repeating Digits") and pt in ("STRAIGHT", "STRAIGHT/BOX"):
        bob_action = "ADD_COMBO"
        bob_note = DEFAULT_BOB_NOTES["ADD_COMBO"]
        return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # RULE 6 – Low-overlay, low-variability patterns:
    #           no bonus, base play is sufficient.
    # ---------------------------------------------------------------
    if low_overlay and low_var_bucket:
        bob_action = "NO_BOB"
        bob_note = ""
        return {"bob_action": bob_action, "bob_note": bob_note}

    # ---------------------------------------------------------------
    # Fallback: if nothing stronger triggered but overlay is moderate,
    #           gently suggest Box safety on any non-quad pattern.
    # ---------------------------------------------------------------
    if med_overlay and pt == "STRAIGHT":
        bob_action = "ADD_BOX"
        bob_note = DEFAULT_BOB_NOTES["ADD_BOX"]

    return {"bob_action": bob_action, "bob_note": bob_note}
