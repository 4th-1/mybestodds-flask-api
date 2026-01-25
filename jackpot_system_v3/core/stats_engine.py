# core/stats_engine.py

from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any

from .ga_results import load_all_ga_results, build_weekday_win_counts, normalized_weekday_score

def compute_stats_score_for_day(
    current_date,
    kit_name: str,
    config: Dict[str, Any],
    root: Path
) -> float:
    """
    Compute a 0-100 'stats' score for a given date based on GA history.

    For now:
      - If kit includes Cash3 -> use Cash3 Evening + Midday
      - If kit includes Cash4 -> use Cash4 Night
      - Use weekday win counts to see how 'hot' that weekday has been.
    """

    if isinstance(current_date, datetime):
        as_of = current_date.date()
    elif isinstance(current_date, date):
        as_of = current_date
    else:
        as_of = datetime.fromisoformat(str(current_date)).date()

    all_results = load_all_ga_results(config, root)

    # Determine which alias to use based on kit_name.
    # You can evolve this later; for now, focus on Cash3 Evening + Cash4 Night.
    c3_mid = all_results.get("cash3_midday", [])
    c3_eve = all_results.get("cash3_evening", [])
    c4_ngt = all_results.get("cash4_night", [])

    weekday = as_of.weekday()  # 0=Mon

    # Build weekday counts
    c3_mid_counts = build_weekday_win_counts(c3_mid, as_of, window_days=180)
    c3_eve_counts = build_weekday_win_counts(c3_eve, as_of, window_days=180)
    c4_ngt_counts = build_weekday_win_counts(c4_ngt, as_of, window_days=180)

    c3_mid_score = normalized_weekday_score(weekday, c3_mid_counts) if c3_mid else 50.0
    c3_eve_score = normalized_weekday_score(weekday, c3_eve_counts) if c3_eve else 50.0
    c4_ngt_score = normalized_weekday_score(weekday, c4_ngt_counts) if c4_ngt else 50.0

    # Simple combined score:
    # If kit has all games, average them.
    # You can later weight based on which games the subscriber actually plays.
    scores = [c3_mid_score, c3_eve_score, c4_ngt_score]
    stats_score = sum(scores) / len(scores) if scores else 50.0

    return stats_score
