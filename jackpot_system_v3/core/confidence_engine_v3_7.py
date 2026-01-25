#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
confidence_engine_v3_7.py
-------------------------
My Best Odds v3.7 – CONFIDENCE ENGINE

Generates:
- confidence_score  (0.00 to 1.00)
- confidence_band   ("Low", "Moderate", "Strong")
- mbo_odds          (1-in-X odds representation)
- mbo_odds_text     ("1 in 214")
- mbo_odds_band     (🟩🟨🤎🚫)

Inputs this engine uses:
- overlay_score            (0–1)
- rubix_confidence_hint    (from Rubix Matrix)
- rubix_bucket             (High, Moderate, Low, Repeating Digits)
- bob_actions              (list)
- perm_count               (Rubix perms, influences stability)
"""

# ---------------------------------------------------------------------
# CONFIDENCE BAND DEFINITIONS
# ---------------------------------------------------------------------

CONFIDENCE_BANDS = [
    (0.00, 0.33, "Low"),
    (0.34, 0.66, "Moderate"),
    (0.67, 1.00, "Strong"),
]

# Odds color-coding based on user rules:
def odds_color(odds_value):
    """
    Return emoji band based on 1-in-X odds.
    """
    if odds_value <= 50:
        return "🟩"  # Strong signal
    if odds_value <= 150:
        return "🟨"  # Decent edge
    if odds_value <= 300:
        return "🤎"  # Low odds
    return "🚫"      # Skip zone


# ---------------------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------------------

def compute_confidence(row: dict) -> dict:
    """
    Core confidence calculation for v3.7.

    INPUTS expected in row:
        overlay_score
        rubix_confidence_hint
        rubix_bucket
        perm_count
        rubix_volatility
        rubix_bob_actions

    OUTPUTS added to row:
        confidence_score
        confidence_band
        mbo_odds
        mbo_odds_text
        mbo_odds_band
    """

    # -------------------------------------------------------------
    # 1) BASE: Overlay score (moon + zodiac + planetary + numerology)
    # -------------------------------------------------------------
    overlay_score = float(row.get("overlay_score", 0.0))

    # -------------------------------------------------------------
    # 2) Rubix influence
    # -------------------------------------------------------------
    rubix_hint = float(row.get("rubix_confidence_hint", 0.0))
    rubix_bucket = row.get("rubix_bucket", "")

    # Rubix bucket contributes structural pattern strength
    bucket_bonus = 0.0
    if rubix_bucket == "Repeating Digits":
        bucket_bonus = 0.08
    elif rubix_bucket == "Moderate Variability":
        bucket_bonus = 0.04
    elif rubix_bucket == "Low Variability":
        bucket_bonus = 0.02
    else:
        bucket_bonus = 0.00  # High Variability gives no bonus

    # -------------------------------------------------------------
    # 3) BOB contribution – BOB gives +0.03 bump when active
    # -------------------------------------------------------------
    bob_list = row.get("rubix_bob_actions", "")
    bob_bonus = 0.03 if bob_list else 0.0

    # -------------------------------------------------------------
    # 4) Combine raw score
    # -------------------------------------------------------------
    raw = (
        overlay_score +
        rubix_hint +
        bucket_bonus +
        bob_bonus
    )

    # Clamp between 0–1
    confidence = max(0.0, min(raw, 1.0))

    # -------------------------------------------------------------
    # 5) Confidence band (Low / Moderate / Strong)
    # -------------------------------------------------------------
    band = "Low"
    for low, high, name in CONFIDENCE_BANDS:
        if low <= confidence <= high:
            band = name
            break

    # -------------------------------------------------------------
    # 6) Convert confidence to 1-in-X odds
    #    Simple invert: odds = max(1, int(1 / confidence))
    # -------------------------------------------------------------
    if confidence <= 0:
        odds_value = 9999
    else:
        odds_value = int(1 / confidence)

    odds_text = f"1 in {odds_value}"
    odds_band = odds_color(odds_value)

    # -------------------------------------------------------------
    # Attach back to row
    # -------------------------------------------------------------
    row["confidence_score"] = round(confidence, 4)
    row["confidence_band"] = band
    row["mbo_odds"] = odds_value
    row["mbo_odds_text"] = odds_text
    row["mbo_odds_band"] = odds_band

    return row


# ---------------------------------------------------------------------
# INTEGRATION HELPER
# ---------------------------------------------------------------------

def apply_confidence_to_row(row: dict) -> dict:
    """
    Helper wrapper for compute_confidence.
    """
    return compute_confidence(row)


if __name__ == "__main__":
    # Quick test
    test_row = {
        "overlay_score": 0.52,
        "rubix_confidence_hint": 0.10,
        "rubix_bucket": "Repeating Digits",
        "rubix_bob_actions": "ADD_1_OFF",
    }
    out = compute_confidence(test_row)
    print(out)
