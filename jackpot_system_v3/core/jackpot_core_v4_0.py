# core/jackpot_core_v4_0.py
# ---------------------------------
# Shared config + helpers for Jackpot Right Engine (Option C)

from dataclasses import dataclass
from typing import Dict, Optional, List


JACKPOT_GAMES: List[str] = [
    "MegaMillions",
    "Powerball",
    "Cash4Life",
]


@dataclass
class JackpotConfig:
    game: str
    main_balls: int
    main_min: int
    main_max: int
    bonus_balls: int
    bonus_min: int
    bonus_max: int


JACKPOT_CONFIGS: Dict[str, JackpotConfig] = {
    "MegaMillions": JackpotConfig(
        game="MegaMillions",
        main_balls=5,
        main_min=1,
        main_max=70,
        bonus_balls=1,
        bonus_min=1,
        bonus_max=25,
    ),
    "Powerball": JackpotConfig(
        game="Powerball",
        main_balls=5,
        main_min=1,
        main_max=69,
        bonus_balls=1,
        bonus_min=1,
        bonus_max=26,
    ),
    "Cash4Life": JackpotConfig(
        game="Cash4Life",
        main_balls=5,
        main_min=1,
        main_max=60,
        bonus_balls=1,
        bonus_min=1,
        bonus_max=4,
    ),
}


def is_jackpot_game(game: str) -> bool:
    """Return True if this game is a jackpot (Right Engine) game."""
    if game is None:
        return False
    return game in JACKPOT_GAMES


def get_jackpot_config(game: str) -> Optional[JackpotConfig]:
    """Return the jackpot config for a game, or None if not jackpot."""
    return JACKPOT_CONFIGS.get(game)


def build_jackpot_draw_id(game: str, draw_date: str) -> str:
    """Simple canonical draw id: e.g. 'MegaMillions_2025-10-17'."""
    return f"{game}_{draw_date}"
