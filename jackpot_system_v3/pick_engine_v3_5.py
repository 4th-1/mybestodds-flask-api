"""
pick_engine_v3_5.py

My Best Odds / SMART LOGIC V3.5
------------------------------------
This is the unified Pick & Jackpot generation engine that sits between:

 - lanes_v3_5.py (candidate generation)
 - score_fx_v3_5.py (confidence scoring)
 - run_kit_v3_5.py (driver / orchestrator)
 - tracking_v3_5.py (logging)
 - audit_v3_5.py (hit/miss audits)

This file:
  1. Calls lane engine (pick + jackpot) to get raw candidates
  2. Passes candidates into ScoreFX for scoring
  3. Consolidates results into a standard format
  4. Returns final picks for each date/game/session

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from datetime import date

from lanes_v3_5 import (
    LaneOutput,
    CandidatePick,
    CandidateJackpot,
    generate_lanes_for_draw,
)

from score_fx_v3_5 import (
    score_lane_outputs,
)

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]


# ================================
# FINAL PICK STRUCTURES
# ================================

@dataclass
class FinalPick:
    """
    For Cash3 / Cash4 (Pick games)
    """
    game: GameType
    session: SessionType
    draw_date: date
    value: str
    digits: List[int]
    confidence: float
    best_odds: str          # "1 in N" string
    confidence_band: str    # 🟩, 🟨, 🤎, 🚫 per your system
    lane_sources: List[str] = field(default_factory=list)


@dataclass
class FinalJackpotPick:
    """
    For MM/PB/C4L (Jackpot games)
    """
    game: GameType
    draw_date: date
    main: List[int]
    bonus: List[int]
    confidence: float
    best_odds: str
    confidence_band: str
    lane_sources: List[str] = field(default_factory=list)


# ================================
# MAIN ENGINE FUNCTION
# ================================

def generate_picks_for_day(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: Optional[SessionType],
    subscriber: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Top-level engine call used by run_kit_v3_5.py

    Returns dict:
    {
       "lanes": [... LaneOutput ...],
       "final": [... FinalPick or FinalJackpotPick ...]
    }
    """
    # 1. Generate lane outputs (Pick or Jackpot depending on game & kit)
    lane_outputs: List[LaneOutput] = generate_lanes_for_draw(
        kit=kit,
        game=game,
        draw_date=draw_date,
        session=session,
        subscriber=subscriber,
        context=context or {},
    )

    # 2. Score all lane outputs (ScoreFX handles fusion + scoring)
    scored_items = score_lane_outputs(
        kit=kit,
        game=game,
        draw_date=draw_date,
        session=session,
        lane_outputs=lane_outputs,
    )

    # 3. Convert scored_items into final structured picks
    final_picks = _convert_scored_items_to_final(
        kit=kit,
        game=game,
        draw_date=draw_date,
        session=session,
        scored=scored_items,
    )

    return {
        "lanes": lane_outputs,
        "final": final_picks,
    }


# ================================
# INTERNAL CONVERSION LAYER
# ================================

def _convert_scored_items_to_final(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: Optional[SessionType],
    scored: List[Dict[str, Any]],
) -> List[Any]:
    """
    Convert ScoreFX results to unified FinalPick structures
    depending on whether the game is pick or jackpot.
    """
    is_pick_game = game in ("Cash3", "Cash4")

    final_items: List[Any] = []

    for item in scored:
        if is_pick_game:
            # for pick games, item['value'] is "123"
            final_items.append(
                FinalPick(
                    game=game,
                    session=session,
                    draw_date=draw_date,
                    value=item["value"],
                    digits=item["digits"],
                    confidence=item["confidence"],
                    best_odds=item["best_odds"],
                    confidence_band=item["confidence_band"],
                    lane_sources=item["lane_sources"],
                )
            )
        else:
            # jackpot: item contains 'main' and 'bonus'
            final_items.append(
                FinalJackpotPick(
                    game=game,
                    draw_date=draw_date,
                    main=item["main"],
                    bonus=item["bonus"],
                    confidence=item["confidence"],
                    best_odds=item["best_odds"],
                    confidence_band=item["confidence_band"],
                    lane_sources=item["lane_sources"],
                )
            )

    return final_items


# ================================
# OPTIONAL: SMOKE TEST
# ================================

if __name__ == "__main__":
    import pprint
    today = date.today()
    test_sub = {
        "dob": "1972-08-22",
        "life_path": 4,
        "personal_year": 3,
        "personal_month": 9,
        "dream_numbers": ["822", "4110"],
    }

    print("=== TEST Cash3 (BOSK) ===")
    out = generate_picks_for_day(
        kit="BOSK",
        game="Cash3",
        draw_date=today,
        session="Midday",
        subscriber=test_sub,
    )
    pprint.pprint(out["final"][:5])

    print("\n=== TEST MegaMillions (BOOK3) ===")
    out2 = generate_picks_for_day(
        kit="BOOK3",
        game="MegaMillions",
        draw_date=today,
        session=None,
        subscriber=test_sub,
    )
    pprint.pprint(out2["final"][:3])
