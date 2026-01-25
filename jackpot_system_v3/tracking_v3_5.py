"""
tracking_v3_5.py

My Best Odds / SMART LOGIC V3.5
--------------------------------
Centralized logging for all generated picks.

Each row in the tracking CSV represents ONE candidate
(number or jackpot line) generated for ONE draw.

This file is used later by:
  - audit_v3_5.py (accuracy audits)
  - results_monitor_v3_5.py (win detection)
"""

from __future__ import annotations

import csv
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]

# Where to store tracking logs
TRACKING_ROOT = Path("data") / "tracking"
TRACKING_ROOT.mkdir(parents=True, exist_ok=True)


def _tracking_path_for_kit(kit: KitType) -> Path:
    """
    Each kit gets its own tracking CSV.
    Example: data/tracking/BOOK3_tracking_v3_5.csv
    """
    return TRACKING_ROOT / f"{kit}_tracking_v3_5.csv"


def _ensure_header(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp_generated",  # ISO datetime
                "kit",
                "subscriber_id",
                "game",
                "draw_date",          # YYYY-MM-DD
                "session",            # Midday/Evening/Night or "" for jackpots
                "pick_type",          # "pick" or "jackpot"
                "value",              # "123" for pick games; "" for jackpots
                "main_balls",         # "1 12 23 34 45" for jackpots
                "bonus_balls",        # "9" for jackpots
                "confidence",
                "best_odds",
                "confidence_band",
                "lane_sources",       # "P_A|P_B|J_A"
            ]
        )


def log_pick(
    kit: KitType,
    subscriber_id: str,
    game: GameType,
    draw_date: date,
    session: Optional[SessionType],
    pick_type: str,  # "pick" or "jackpot"
    value: str,
    main_balls: List[int],
    bonus_balls: List[int],
    confidence: float,
    best_odds: str,
    confidence_band: str,
    lane_sources: List[str],
) -> None:
    """
    Append a single pick to the kit's tracking CSV.
    """
    path = _tracking_path_for_kit(kit)
    _ensure_header(path)

    ts = datetime.utcnow().isoformat(timespec="seconds")
    draw_str = draw_date.strftime("%Y-%m-%d")
    session_str = session or ""

    main_str = " ".join(str(x) for x in main_balls) if main_balls else ""
    bonus_str = " ".join(str(x) for x in bonus_balls) if bonus_balls else ""
    lanes_str = "|".join(lane_sources) if lane_sources else ""

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                ts,
                kit,
                subscriber_id,
                game,
                draw_str,
                session_str,
                pick_type,
                value,
                main_str,
                bonus_str,
                f"{confidence:.6f}",
                best_odds,
                confidence_band,
                lanes_str,
            ]
        )
