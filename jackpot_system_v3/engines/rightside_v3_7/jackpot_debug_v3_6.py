"""
jackpot_debug_v3_6.py

Debug helpers for right-side (jackpot) engine v3.6.
Use this to sanity check Play/Skip flags and confidence scores.
"""

from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Dict

from rightside_engine_v3_6 import build_engine_for_game, KitType
from jackpot_ingest_v3_6 import GameName


def preview_game_for_range(
    game: GameName,
    kit_type: KitType,
    history_csv: str,
    start: date,
    end: date,
    limit: int = 10,
) -> None:
    """
    Print a quick preview of picks for a single game.
    """
    engine = build_engine_for_game(game=game, kit_type=kit_type, history_csv=history_csv)
    picks = engine.generate_picks_for_range(start, end)

    print(f"\n=== {game.upper()} preview ({kit_type}) {start} → {end} ===")
    for row in picks[:limit]:
        print(
            f"{row['date']} rank={row['rank']} "
            f"conf={row['confidence']} "
            f"flag={row['play_flag']} "
            f"best_odds={row['best_odds']}"
        )


if __name__ == "__main__":
    # Example usage – adjust paths and dates for a quick smoke test.
    start = date(2025, 12, 3)
    end = date(2025, 12, 31)

    history_paths: Dict[GameName, str] = {
        "megamillions": r"C:\MyBestOdds\data\ga_megamillions_history.csv",
        "powerball": r"C:\MyBestOdds\data\ga_powerball_history.csv",
        "cash4life": r"C:\MyBestOdds\data\ga_cash4life_history.csv",
    }

    for game, path in history_paths.items():
        preview_game_for_range(
            game=game, kit_type="BOOK3", history_csv=path, start=start, end=end, limit=5
        )
