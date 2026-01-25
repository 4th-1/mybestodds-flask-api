"""
score_fx_v3_5.py

My Best Odds / SMART LOGIC V3.5
--------------------------------
Score engine that converts lane outputs into:

- Confidence scores
- "1 in N" Best Odds string
- Emoji confidence bands

Used by:
  pick_engine_v3_5.generate_picks_for_day()

Input:
  - kit, game, draw_date, session
  - lane_outputs: List[LaneOutput]

Output:
  - List[dict], where each dict is either:
      PICK games (Cash3/Cash4):
        {
          "value": "123",
          "digits": [1,2,3],
          "confidence": 0.0123,
          "best_odds": "1 in 81",
          "confidence_band": "🟨",
          "lane_sources": ["P_A", "P_B"]
        }

      JACKPOT games (MM/PB/C4L):
        {
          "main": [1, 12, 23, 34, 45],
          "bonus": [9],
          "confidence": 0.004,
          "best_odds": "1 in 250",
          "confidence_band": "🟩",
          "lane_sources": ["J_A", "J_D"]
        }

NOTE:
  - Confidence is a RELATIVE signal, not the literal lottery probability.
  - We normalize lane-based scores into a 0–0.02 range (~1%–2% max),
    then convert to 1 in N and color-band that.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass, field
from datetime import date

from lanes_v3_5 import LaneOutput, CandidatePick, CandidateJackpot
from history_v3_5 import get_jackpot_stats, GameType as HistoryGameType

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]


# ================================
# Helper: game mapping for history
# ================================

def _map_game_to_history(game: GameType) -> Optional[HistoryGameType]:
    if game == "MegaMillions":
        return "MegaMillions"
    if game == "Powerball":
        return "Powerball"
    if game == "Cash4Life":
        return "Cash4Life"
    return None  # Cash3/Cash4 do not use jackpot history


# ================================
# Helper: convert confidence → 1 in N & band
# ================================

def _confidence_to_odds_and_band(confidence: float) -> (str, str):
    """
    Take a confidence value (0–1) and convert to:
      - "1 in N" formatted string
      - emoji band based on N

    Mapping (per your spec):
      1–50      → 🟩 Strong signal – Play confidently
      51–150    → 🟨 Decent edge – Play cautiously
      151–300   → 🤎 Low odds – Only if intuitively aligned
      301+      → 🚫 Skip Zone – Extremely low probability

    We clamp very small probabilities to avoid N → infinity.
    """
    # Safety clamp
    p = max(min(confidence, 0.9999), 0.0001)  # between 0.01% and 99.99%
    n = int(round(1.0 / p))

    if n <= 50:
        band = "🟩"
    elif n <= 150:
        band = "🟨"
    elif n <= 300:
        band = "🤎"
    else:
        band = "🚫"

    odds_str = f"1 in {n:,}"
    return odds_str, band


# ================================
# Aggregation data structures
# ================================

@dataclass
class PickAggregate:
    value: str
    digits: List[int]
    lane_ids: set = field(default_factory=set)
    base_score_sum: float = 0.0
    lane_count: int = 0
    raw_score: float = 0.0


@dataclass
class JackpotAggregate:
    main: List[int]
    bonus: List[int]
    lane_ids: set = field(default_factory=set)
    base_score_sum: float = 0.0
    lane_count: int = 0
    history_main_score: float = 0.0
    history_bonus_score: float = 0.0
    raw_score: float = 0.0


# ================================
# Core scoring entry point
# ================================

def score_lane_outputs(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: Optional[SessionType],
    lane_outputs: List[LaneOutput],
) -> List[Dict[str, Any]]:
    """
    Main ScoreFX V3.5 entry.

    Steps:
      1. Aggregate candidates across lanes.
      2. Compute raw scores.
      3. Normalize into 0–0.02 confidence (0%–2%).
      4. Convert to 1 in N + color band.
      5. Return list of dicts for downstream engine.
    """

    is_pick_game = game in ("Cash3", "Cash4")

    if is_pick_game:
        return _score_pick_candidates(kit, game, draw_date, session, lane_outputs)
    else:
        return _score_jackpot_candidates(kit, game, draw_date, lane_outputs)


# ================================
# PICK Scoring (Cash3 / Cash4)
# ================================

def _score_pick_candidates(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: Optional[SessionType],
    lane_outputs: List[LaneOutput],
) -> List[Dict[str, Any]]:
    """
    Score Cash3/Cash4 candidates.

    Logic:
      - Aggregate by 'value' (e.g., "123").
      - Sum lane base scores.
      - Add synergy bonus if candidate appears in multiple lanes.
      - Normalize to 0–0.02.
    """

    aggregates: Dict[str, PickAggregate] = {}

    # 1. Aggregate across all PICK lanes
    for lane in lane_outputs:
        if lane.kind != "pick":
            continue

        for cand in lane.pick_candidates:
            key = cand.value
            if key not in aggregates:
                aggregates[key] = PickAggregate(
                    value=cand.value,
                    digits=cand.digits,
                )
            agg = aggregates[key]
            agg.lane_ids.add(lane.lane_id)
            agg.base_score_sum += lane.base_lane_score
            agg.lane_count += 1

    if not aggregates:
        return []

    # 2. Compute raw_score for each candidate
    #    raw_score = base_score_sum * (1 + 0.1 * (lane_count - 1))
    #    (i.e., multiply for cross-lane agreement)
    max_raw = 0.0
    for agg in aggregates.values():
        synergy_factor = 1.0 + 0.1 * max(0, agg.lane_count - 1)
        agg.raw_score = agg.base_score_sum * synergy_factor
        if agg.raw_score > max_raw:
            max_raw = agg.raw_score

    if max_raw <= 0:
        max_raw = 1.0

    # 3. Normalize raw_score → confidence
    #    We map [0, max_raw] → [0.0005, 0.02] (0.05%–2%)
    MIN_CONF = 0.0005
    MAX_CONF = 0.02

    results: List[Dict[str, Any]] = []

    for agg in aggregates.values():
        rel = agg.raw_score / max_raw
        confidence = MIN_CONF + (MAX_CONF - MIN_CONF) * rel

        best_odds, band = _confidence_to_odds_and_band(confidence)

        results.append(
            {
                "value": agg.value,
                "digits": agg.digits,
                "confidence": confidence,
                "best_odds": best_odds,
                "confidence_band": band,
                "lane_sources": sorted(list(agg.lane_ids)),
            }
        )

    # 4. Sort highest confidence first
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


# ================================
# JACKPOT Scoring (MM / PB / C4L)
# ================================

def _score_jackpot_candidates(
    kit: KitType,
    game: GameType,
    draw_date: date,
    lane_outputs: List[LaneOutput],
) -> List[Dict[str, Any]]:
    """
    Score jackpot candidates (MM/PB/C4L).

    Logic:
      - Aggregate by (main tuple, bonus tuple).
      - Sum lane base scores.
      - Blend in history-based composite scores (heat/due).
      - Add synergy bonus for multi-lane agreement.
      - Normalize to 0–0.02 and convert to "1 in N" + band.
    """

    aggregates: Dict[Any, JackpotAggregate] = {}

    # 1. Aggregate across JACKPOT lanes
    for lane in lane_outputs:
        if lane.kind != "jackpot":
            continue

        for cand in lane.jackpot_candidates:
            main_tuple = tuple(sorted(cand.main))
            bonus_tuple = tuple(sorted(cand.bonus))
            key = (main_tuple, bonus_tuple)

            if key not in aggregates:
                aggregates[key] = JackpotAggregate(
                    main=list(main_tuple),
                    bonus=list(bonus_tuple),
                )
            agg = aggregates[key]
            agg.lane_ids.add(lane.lane_id)
            agg.base_score_sum += lane.base_lane_score
            agg.lane_count += 1

    if not aggregates:
        return []

    # 2. Pull history stats for this game
    h_game = _map_game_to_history(game)
    history_stats = get_jackpot_stats(h_game) if h_game is not None else None

    # 3. Compute history-based scores
    for agg in aggregates.values():
        if history_stats is None:
            agg.history_main_score = 0.0
            agg.history_bonus_score = 0.0
            continue

        # Average composite_score over main balls
        main_scores = []
        for b in agg.main:
            bs = history_stats.main_balls.get(b)
            if bs:
                main_scores.append(bs.composite_score)
        agg.history_main_score = sum(main_scores) / len(main_scores) if main_scores else 0.0

        # Average composite_score over bonus balls
        bonus_scores = []
        for b in agg.bonus:
            bs = history_stats.bonus_balls.get(b)
            if bs:
                bonus_scores.append(bs.composite_score)
        agg.history_bonus_score = sum(bonus_scores) / len(bonus_scores) if bonus_scores else 0.0

    # 4. Compute raw_score per combo
    #    raw_score = base_score_sum * (1 + 0.4 * history_main + 0.3 * history_bonus) * (1 + 0.1 * (lane_count - 1))
    max_raw = 0.0
    for agg in aggregates.values():
        history_factor = 1.0 + 0.4 * agg.history_main_score + 0.3 * agg.history_bonus_score
        synergy_factor = 1.0 + 0.1 * max(0, agg.lane_count - 1)
        agg.raw_score = agg.base_score_sum * history_factor * synergy_factor
        if agg.raw_score > max_raw:
            max_raw = agg.raw_score

    if max_raw <= 0:
        max_raw = 1.0

    # 5. Normalize raw_score → confidence
    #    Same range [0.0005, 0.02] for now so bands are comparable.
    MIN_CONF = 0.0005
    MAX_CONF = 0.02

    results: List[Dict[str, Any]] = []

    for agg in aggregates.values():
        rel = agg.raw_score / max_raw
        confidence = MIN_CONF + (MAX_CONF - MIN_CONF) * rel

        best_odds, band = _confidence_to_odds_and_band(confidence)

        results.append(
            {
                "main": agg.main,
                "bonus": agg.bonus,
                "confidence": confidence,
                "best_odds": best_odds,
                "confidence_band": band,
                "lane_sources": sorted(list(agg.lane_ids)),
            }
        )

    # 6. Sort highest confidence first
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


# ================================
# Smoke test
# ================================

if __name__ == "__main__":
    # This relies on lanes_v3_5 and history_v3_5 being present & valid.
    from datetime import date as _date
    from lanes_v3_5 import generate_lanes_for_draw

    test_sub = {
        "dob": "1972-08-22",
        "life_path": 4,
        "personal_year": 3,
        "personal_month": 9,
        "dream_numbers": ["822", "4110"],
    }

    today = _date.today()

    print("=== TEST PICK (Cash3 BOSK Midday) ===")
    lanes_pick = generate_lanes_for_draw(
        kit="BOSK",
        game="Cash3",
        draw_date=today,
        session="Midday",
        subscriber=test_sub,
    )
    scored_pick = score_lane_outputs(
        kit="BOSK",
        game="Cash3",
        draw_date=today,
        session="Midday",
        lane_outputs=lanes_pick,
    )
    for r in scored_pick:
        print(r)

    print("\n=== TEST JACKPOT (MegaMillions BOOK3) ===")
    lanes_j = generate_lanes_for_draw(
        kit="BOOK3",
        game="MegaMillions",
        draw_date=today,
        session=None,
        subscriber=test_sub,
    )
    scored_j = score_lane_outputs(
        kit="BOOK3",
        game="MegaMillions",
        draw_date=today,
        session=None,
        lane_outputs=lanes_j,
    )
    for r in scored_j[:5]:
        print(r)
