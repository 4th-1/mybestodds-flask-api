# core/v3_7/cash_personalization_v3_7.py
from __future__ import annotations
from typing import List, Dict, Any

from core.v3_7.phase_firewall import (
    assert_mmfsn_sets_only,
    assert_no_mmfsn_exact_match,
)
from core.v3_7.mmfsn_resonance import resonance


def apply_cash_mmfsn_resonance(
    rows: List[Dict[str, Any]],
    subscriber: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    PHASE 3 — Cash personalization only.
    - MMFSN is reference-only
    - Reject exact matches
    - Score echoes
    """

    mm3 = subscriber.get("mmfsn_cash3") or subscriber.get("mmfsn") or []
    mm4 = subscriber.get("mmfsn_cash4") or []

    # Enforce locked MMFSN rules
    assert_mmfsn_sets_only(mm3, digits=3, label="MMFSN_CASH3")
    if mm4:
        assert_mmfsn_sets_only(mm4, digits=4, label="MMFSN_CASH4")

    out: List[Dict[str, Any]] = []

    for r in rows:
        game_code = (r.get("game_code") or "").upper()
        num = str(r.get("number") or "").strip()

        # Defaults
        r["mmfsn_relation"] = "not applicable"
        r["resonance_score"] = 0
        r["resonance_label"] = "NONE"

        # Cash3
        if game_code == "CASH3" and num.isdigit() and len(num) == 3:
            assert_no_mmfsn_exact_match(num, mm3, label="Cash3")
            sc, rel, lab = resonance(num, mm3)
            r["mmfsn_relation"] = rel
            r["resonance_score"] = sc
            r["resonance_label"] = lab

        # Cash4
        elif game_code == "CASH4" and num.isdigit() and len(num) == 4:
            if mm4:
                assert_no_mmfsn_exact_match(num, mm4, label="Cash4")
                sc, rel, lab = resonance(num, mm4)
                r["mmfsn_relation"] = rel
                r["resonance_score"] = sc
                r["resonance_label"] = lab
            else:
                r["mmfsn_relation"] = "no mmfsn provided"

        out.append(r)

    return out
