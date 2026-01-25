"""
history_v3_5.py

My Best Odds / SmartLogic V3.5
--------------------------------
Jackpot history engine for Mega Millions, Powerball, Cash4Life.

Responsibilities:
- Load cached jackpot frequency / recency data from JSON files.
- Normalize into a common internal structure.
- Compute:
    - frequency ratio (heat)
    - recency in days (due)
    - composite scores for lane logic.
- Provide helpers for:
    - get_jackpot_stats(game)
    - get_hot_balls(game, ...)
    - get_due_balls(game, ...)
    - score_jackpot_ball(game, field, ball)

This module deliberately does NOT call external APIs directly.
A separate process/script should periodically fetch and update
the JSON files under data/jackpot_history/.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Literal, Tuple

# -----------------------------
# Type aliases & constants
# -----------------------------

GameType = Literal["MegaMillions", "Powerball", "Cash4Life"]
BallField = Literal["main", "bonus"]

# Default relative folder for cached history
DEFAULT_HISTORY_ROOT = Path("data") / "jackpot_history"

# Map internal game keys to file names
GAME_FILE_MAP: Dict[GameType, str] = {
    "MegaMillions": "mega_millions_stats.json",
    "Powerball": "powerball_stats.json",
    "Cash4Life": "cash4life_stats.json",
}


@dataclass
class BallStats:
    ball: int
    frequency: int
    last_seen: Optional[date]  # None if never seen
    draw_count: int

    # Derived / computed fields (filled by compute_scores)
    heat_score: float = 0.0       # 0–1, relative frequency
    due_score: float = 0.0        # 0–1, relative recency
    composite_score: float = 0.0  # 0–1, blend of heat & due


@dataclass
class JackpotStats:
    game: GameType
    last_updated: date
    draw_count: int
    main_balls: Dict[int, BallStats]
    bonus_balls: Dict[int, BallStats]


# -----------------------------
# Helpers
# -----------------------------


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    # Accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS" style
    try:
        if "T" in d:
            return datetime.fromisoformat(d).date()
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return None


def _today() -> date:
    # Centralize for easier testing/mocking later if needed
    return date.today()


# -----------------------------
# Core load / normalize
# -----------------------------


def _load_raw_json(history_root: Path, game: GameType) -> Dict:
    """
    Load raw JSON data for a given game from history_root.

    Expected structure (example):

    {
      "game": "MegaMillions",
      "last_updated": "2025-11-20",
      "draw_count": 500,
      "main_balls": {
        "1": { "frequency": 23, "last_seen": "2025-11-10" },
        "2": { "frequency": 15, "last_seen": "2025-11-01" },
        ...
      },
      "bonus_balls": {
        "1": { "frequency": 8, "last_seen": "2025-11-15" },
        ...
      }
    }

    If your upstream fetcher uses a slightly different schema,
    adjust this function to normalize into the above format.
    """
    file_name = GAME_FILE_MAP[game]
    path = history_root / file_name

    if not path.exists():
        raise FileNotFoundError(
            f"[history_v3_5] History file not found for {game}: {path}"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def _normalize_ball_stats(
    raw_balls: Dict[str, Dict],
    draw_count: int
) -> Dict[int, BallStats]:
    balls: Dict[int, BallStats] = {}

    for key, info in raw_balls.items():
        try:
            ball_num = int(key)
        except ValueError:
            # Skip any non-numeric keys
            continue

        frequency = int(info.get("frequency", 0))
        last_seen = _parse_date(info.get("last_seen"))

        balls[ball_num] = BallStats(
            ball=ball_num,
            frequency=frequency,
            last_seen=last_seen,
            draw_count=draw_count,
        )

    return balls


def _compute_scores_for_balls(balls: Dict[int, BallStats]) -> None:
    """
    Compute heat_score, due_score, and composite_score in-place
    for the given ball dictionary.

    Strategy:
    - heat_score: normalized frequency vs max frequency.
    - due_score: normalized recency vs max recency.
    - composite_score: blend of heat and due.
    """
    if not balls:
        return

    today = _today()

    # Frequency & recency ranges
    max_freq = max(b.frequency for b in balls.values()) or 1

    recencies: List[int] = []
    for b in balls.values():
        if b.last_seen is None:
            # Treat "never seen" as most due → use a large recency
            # e.g., 2 * max_recency_of_others or an arbitrary cap
            # For now, we mark as None; we’ll handle after computing others.
            continue
        delta_days = (today - b.last_seen).days
        recencies.append(max(delta_days, 0))

    max_recency = max(recencies) if recencies else 1

    # Pass 1: assign base heat_score
    for b in balls.values():
        b.heat_score = b.frequency / max_freq if max_freq > 0 else 0.0

    # Pass 2: assign due_score
    for b in balls.values():
        if b.last_seen is None:
            # Never seen → treat as more due than any seen ball
            b.due_score = 1.0
        else:
            days = max((today - b.last_seen).days, 0)
            b.due_score = days / max_recency if max_recency > 0 else 0.0

    # Pass 3: composite score blend
    # You can tweak weights if desired.
    WEIGHT_DUE = 0.6
    WEIGHT_HEAT = 0.4

    for b in balls.values():
        b.composite_score = (WEIGHT_DUE * b.due_score) + (WEIGHT_HEAT * b.heat_score)


def _normalize_stats(history_root: Path, game: GameType) -> JackpotStats:
    raw = _load_raw_json(history_root, game)

    game_name = raw.get("game", game)
    # Use game parameter as truth, but keep raw for checksum if needed.

    last_updated = _parse_date(raw.get("last_updated")) or _today()
    draw_count = int(raw.get("draw_count", 0))

    main_raw = raw.get("main_balls", {}) or {}
    bonus_raw = raw.get("bonus_balls", {}) or {}

    main_balls = _normalize_ball_stats(main_raw, draw_count)
    bonus_balls = _normalize_ball_stats(bonus_raw, draw_count)

    _compute_scores_for_balls(main_balls)
    _compute_scores_for_balls(bonus_balls)

    return JackpotStats(
        game=game,
        last_updated=last_updated,
        draw_count=draw_count,
        main_balls=main_balls,
        bonus_balls=bonus_balls,
    )


# -----------------------------
# Public API
# -----------------------------


def get_jackpot_stats(
    game: GameType,
    history_root: Path = DEFAULT_HISTORY_ROOT
) -> JackpotStats:
    """
    Load and return JackpotStats for a given game.

    This is the main entry point other modules should call.
    """
    return _normalize_stats(history_root, game)


def get_hot_balls(
    game: GameType,
    field: BallField = "main",
    top_n: int = 10,
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> List[BallStats]:
    """
    Return the top N hot balls based on heat_score (frequency-based),
    for the given game and field ("main" or "bonus").
    """
    stats = get_jackpot_stats(game, history_root=history_root)
    balls = stats.main_balls if field == "main" else stats.bonus_balls

    return sorted(
        balls.values(),
        key=lambda b: b.heat_score,
        reverse=True,
    )[:top_n]


def get_due_balls(
    game: GameType,
    field: BallField = "main",
    top_n: int = 10,
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> List[BallStats]:
    """
    Return the top N most due balls based on due_score (recency-based),
    for the given game and field ("main" or "bonus").
    """
    stats = get_jackpot_stats(game, history_root=history_root)
    balls = stats.main_balls if field == "main" else stats.bonus_balls

    return sorted(
        balls.values(),
        key=lambda b: b.due_score,
        reverse=True,
    )[:top_n]


def score_jackpot_ball(
    game: GameType,
    ball: int,
    field: BallField = "main",
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> Optional[BallStats]:
    """
    Return BallStats (including composite_score) for a specific ball.
    If the ball is not in the history file, returns None.
    """
    stats = get_jackpot_stats(game, history_root=history_root)
    balls = stats.main_balls if field == "main" else stats.bonus_balls
    return balls.get(ball)


def rank_all_balls(
    game: GameType,
    field: BallField = "main",
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> List[BallStats]:
    """
    Return all balls ranked by composite_score (high → low).
    Useful for lane logic when compressing the field.
    """
    stats = get_jackpot_stats(game, history_root=history_root)
    balls = stats.main_balls if field == "main" else stats.bonus_balls

    return sorted(
        balls.values(),
        key=lambda b: b.composite_score,
        reverse=True,
    )


def summarize_top_balls(
    game: GameType,
    field: BallField = "main",
    top_n: int = 10,
    history_root: Path = DEFAULT_HISTORY_ROOT,
) -> List[Tuple[int, float, float, float]]:
    """
    Convenience function for debugging / audits.

    Returns a list of tuples:
        (ball, heat_score, due_score, composite_score)
    for the top N balls by composite_score.
    """
    ranked = rank_all_balls(game, field=field, history_root=history_root)[:top_n]
    return [
        (b.ball, b.heat_score, b.due_score, b.composite_score)
        for b in ranked
    ]


if __name__ == "__main__":
    # Simple smoke test for local runs:
    root = DEFAULT_HISTORY_ROOT
    for g in ("MegaMillions", "Powerball", "Cash4Life"):
        try:
            stats = get_jackpot_stats(g, history_root=root)
        except FileNotFoundError as e:
            print(e)
            continue

        print(f"=== {g} (last_updated={stats.last_updated}, draws={stats.draw_count}) ===")
        print("Top 5 main balls by composite_score:")
        for b in summarize_top_balls(g, field="main", top_n=5, history_root=root):
            print("  Ball %2d | heat=%.3f | due=%.3f | composite=%.3f" % b)
        print()
