"""
pick_engine_v3_5.py

Pick engine for My Best Odds – SMART LOGIC V3.5

This module:
- Accepts pre-generated candidate numbers + subscores
- Calls score_fx_v3_5.score_candidate(...)
- Filters and sorts candidates
- Produces a DailyGameForecast-style dict

NOTE:
Lane A/B/C/D generation should be done upstream.
This engine assumes that 'context["candidates"]' contains a list of dicts:

context["candidates"] = [
    {
        "number": "7263",
        "lane_sources": ["A", "B"],
        "subscores": {
            "astro": 60.0,
            "stats": 50.0,
            "mmfsn": 58.0,
            "planetary": 65.0,
            "numerology": 62.0,
            "pattern": 55.0,
            "lane": 68.0
        }
    },
    ...
]

You can adapt your existing lane engine to populate this structure.
"""

from typing import Dict, Any, List
from datetime import date

from score_fx_v3_5 import score_candidate


def make_tracking_key(subscriber_id: str,
                      kit_name: str,
                      target_date: date,
                      game: str,
                      session: str,
                      number: str) -> str:
    """
    Create a unique tracking key for this pick.

    Example:
    "BOOK3_JDS_2025-09-01_Cash4_Night_7263"
    """
    date_str = target_date.isoformat()
    clean_kit = kit_name.replace(" ", "").upper()
    clean_game = game.replace(" ", "")
    clean_session = session.replace(" ", "")
    clean_sub = subscriber_id.replace(" ", "")
    clean_num = str(number).strip()
    key = f"{clean_kit}_{clean_sub}_{date_str}_{clean_game}_{clean_session}_{clean_num}"
    return key


def _filter_and_sort_candidates(scored_candidates: List[Dict[str, Any]],
                                game: str,
                                config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter and sort candidates for a given game.
    """
    # Example rule: keep only candidates with confidence >= 41 (Medium or better)
    kept = [c for c in scored_candidates if c.get("confidence", 0) >= 41]

    # Per-game limit
    if game in ("Cash3", "Cash4"):
        limit = 5
    else:
        # MegaMillions, Powerball, Cash4Life -> fewer picks
        limit = 3

    kept.sort(key=lambda x: (-x.get("confidence", 0), str(x.get("number", ""))))
    return kept[:limit]


def generate_picks_for_day(subscriber: Dict[str, Any],
                           target_date: date,
                           game: str,
                           session: str,
                           context: Dict[str, Any],
                           config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate picks for one subscriber / date / game / session.

    Parameters
    ----------
    subscriber : dict
        Must contain at least "id".
    target_date : datetime.date
        The forecast date.
    game : str
        e.g. "Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life".
    session : str
        e.g. "Midday", "Evening", "Night", or "Main".
    context : dict
        Should contain:
        - "kit_name": str
        - "candidates": List[dict] (see module docstring)
        - "north_node_alignment": "Low" | "Medium" | "High"
        - "planetary_hour_label": optional str
    config : dict
        Parsed config_v3_5.json.

    Returns
    -------
    dict
        {
            "subscriber_id": str,
            "date": "YYYY-MM-DD",
            "game": str,
            "session": str,
            "picks": [
                {
                    "number": str,
                    "confidence": int,
                    "confidence_band": str,
                    "best_odds": str,
                    "color": str,
                    "alignment_strength": str,
                    "lane_sources": List[str],
                    "timing_window": {
                        "session": str,
                        "planetary_hour": str or None
                    },
                    "north_node_alignment": str,
                    "marketing_triggers": List[str],
                    "tracking_key": str
                }, ...
            ]
        }
    """
    subscriber_id = subscriber.get("id", "UNKNOWN_SUBSCRIBER")
    kit_name = context.get("kit_name", "UNKNOWN_KIT")
    nn_align = context.get("north_node_alignment", "Medium")
    planetary_hour_label = context.get("planetary_hour_label")

    raw_candidates = context.get("candidates", [])
    scored_candidates: List[Dict[str, Any]] = []

    for cand in raw_candidates:
        number = str(cand.get("number", "")).strip()
        lane_sources = cand.get("lane_sources", [])
        subscores = cand.get("subscores", {})

        # Ensure subscores has all keys; fill missing with 0
        for key in ["astro", "stats", "mmfsn",
                    "planetary", "numerology", "pattern", "lane"]:
            subscores.setdefault(key, 0.0)

        score_info = score_candidate(
            subscores=subscores,
            game=game,
            session=session,
            north_node_alignment=nn_align,
            config=config
        )

        out = {
            "number": number,
            "lane_sources": lane_sources,
            "subscores": subscores
        }
        out.update(score_info)
        scored_candidates.append(out)

    # Filter & sort
    filtered = _filter_and_sort_candidates(scored_candidates, game, config)

    # Attach tracking keys and timing windows
    final_picks: List[Dict[str, Any]] = []
    for item in filtered:
        tk = make_tracking_key(
            subscriber_id=subscriber_id,
            kit_name=kit_name,
            target_date=target_date,
            game=game,
            session=session,
            number=item["number"]
        )
        pick_entry = {
            "number": item["number"],
            "confidence": item["confidence"],
            "confidence_band": item["confidence_band"],
            "best_odds": item["best_odds"],
            "color": item["color"],
            "alignment_strength": item["alignment_strength"],
            "lane_sources": item.get("lane_sources", []),
            "timing_window": {
                "session": session,
                "planetary_hour": planetary_hour_label
            },
            "north_node_alignment": nn_align,
            "marketing_triggers": item.get("marketing_triggers", []),
            "tracking_key": tk
        }
        final_picks.append(pick_entry)

    return {
        "subscriber_id": subscriber_id,
        "date": target_date.isoformat(),
        "game": game,
        "session": session,
        "picks": final_picks
    }
