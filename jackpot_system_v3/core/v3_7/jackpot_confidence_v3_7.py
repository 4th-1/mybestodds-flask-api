from __future__ import annotations
from typing import Dict, Any

# -----------------------------------
# JACKPOT CONFIDENCE SCORING v3.7
# -----------------------------------

# Conservative ceiling (jackpots are rare)
JACKPOT_MAX_SCORE = 12.0

def compute_jackpot_confidence(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a conservative jackpot confidence score.
    This is NOT probability. It is alignment strength.
    """

    if not row.get("is_jackpot"):
        return row

    score = 0.0

    # -------------------------
    # SENTINEL PASS BONUS
    # -------------------------
    if row.get("jackpot_status") == "PASSED":
        score += 3.0

    # -------------------------
    # DRAW DAY VALIDITY
    # -------------------------
    if row.get("draw_time") == "JACKPOT":
        score += 2.0

    # -------------------------
    # ENGINE SOURCE CONFIDENCE
    # -------------------------
    if row.get("engine_source") == "RIGHT_GENERATED":
        score += 2.0

    # -------------------------
    # HOLD WINDOW BONUS (OPTIONAL)
    # -------------------------
    if row.get("window_status") == "FORMING":
        score += 1.5
    elif row.get("window_status") == "OPEN":
        score += 3.0

    # -------------------------
    # HARD CAP
    # -------------------------
    score = min(score, JACKPOT_MAX_SCORE)

    row["jackpot_confidence_score"] = round(score, 1)

    return row
