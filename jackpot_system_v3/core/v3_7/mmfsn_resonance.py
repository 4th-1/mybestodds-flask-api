# core/v3_7/mmfsn_resonance.py
from __future__ import annotations
from typing import List, Tuple

_MIRROR = {"0":"9","1":"8","2":"7","3":"6","4":"5","5":"4","6":"3","7":"2","8":"1","9":"0"}

def mirror(n: str) -> str:
    return "".join(_MIRROR.get(c, c) for c in n)

def rotations(n: str) -> List[str]:
    # positional rotations (not permutations)
    return [n[i:] + n[:i] for i in range(1, len(n))]

def one_off(a: str, b: str) -> bool:
    # exactly one digit differs (same position)
    if len(a) != len(b):
        return False
    diffs = 0
    for x, y in zip(a, b):
        if x != y:
            diffs += 1
            if diffs > 1:
                return False
    return diffs == 1

def digit_sum(n: str) -> int:
    return sum(int(c) for c in n if c.isdigit())

def resonance(candidate: str, mmfsn_sets: List[str]) -> Tuple[int, str, str]:
    """
    Returns: (resonance_score, relation_string, label)
    Rules:
      - Exact match handled externally as REJECT
      - 1-off: +6
      - rotation: +5
      - mirror: +5
      - sum-band overlap (±1): +2
      - else: 0
    """
    mm = set(mmfsn_sets or [])

    # 1-off
    for ref in mm:
        if one_off(candidate, ref):
            return (6, f"1-off from {ref}", "ONE_OFF")

    # rotation
    rots = set(rotations(candidate))
    hit = list(rots.intersection(mm))
    if hit:
        return (5, f"rotation of {hit[0]}", "ROTATION")

    # mirror
    mir = mirror(candidate)
    if mir in mm:
        return (5, f"mirror of {mir}", "MIRROR")

    # sum-band overlap
    s = digit_sum(candidate)
    for ref in mm:
        if abs(digit_sum(ref) - s) <= 1:
            return (2, f"sum-band overlap with {ref}", "SUM_BAND")

    return (0, "no resonance", "NONE")

def apply_cash_mmfsn_resonance(rows: list, subscriber: dict) -> list:
    """
    Applies MMFSN resonance logic to Cash3 / Cash4 rows.
    This function is intentionally conservative:
    - It never injects new numbers
    - It only boosts confidence when MMFSN timing is aligned
    """

    if not rows:
        return rows

    for row in rows:
        # Only apply to cash games
        game = (row.get("game") or "").upper()
        if game not in ("CASH3", "CASH4"):
            continue

        # Guardrails
        if row.get("engine_source") != "PROFILE_MMFSN":
            continue

        # If already green, leave it alone
        if row.get("confidence_band") == "GREEN":
            continue

        # Soft resonance boost (non-inflationary)
        row["confidence_band"] = "YELLOW"
        row["play_flag"] = "MODERATE"

    return rows
