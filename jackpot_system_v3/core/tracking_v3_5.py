"""
tracking_v3_5.py

Utility functions to log V3.5 engine picks to CSV for later auditing.
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def ensure_tracking_dir(root: Path) -> Path:
    tracking_dir = root / "outputs" / "TRACKING"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    return tracking_dir


def get_tracking_path(root: Path, kit_name: str, period: str) -> Path:
    tracking_dir = ensure_tracking_dir(root)
    clean_kit = kit_name.replace(" ", "").upper()
    filename = f"{clean_kit}_tracking_{period}.csv"
    return tracking_dir / filename


def init_tracking_file(path: Path) -> None:
    """
    Create file with header if it doesn't exist.
    """
    if path.exists():
        return

    header = [
        "tracking_key",
        "kit",
        "subscriber_id",
        "period",
        "date",
        "game",
        "session",
        "number",
        "confidence",
        "confidence_band",
        "best_odds",
        "color",
        "alignment_strength",
        "north_node_alignment",
        "marketing_triggers",
        "hit_type",
        "winning_number",
        "created_at"
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def append_forecast_to_tracking(root: Path,
                                kit_name: str,
                                period: str,
                                forecast: Dict[str, Any]) -> None:
    """
    Append all picks from a DailyGameForecast to the tracking CSV.

    forecast structure:
    {
        "subscriber_id": str,
        "date": "YYYY-MM-DD",
        "game": str,
        "session": str,
        "picks": [ {...}, ... ]
    }
    """
    path = get_tracking_path(root, kit_name, period)
    init_tracking_file(path)

    subscriber_id = forecast.get("subscriber_id", "UNKNOWN_SUBSCRIBER")
    date_str = forecast.get("date")
    game = forecast.get("game")
    session = forecast.get("session")

    now = datetime.utcnow().isoformat(timespec="seconds")

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for pick in forecast.get("picks", []):
            tracking_key = pick.get("tracking_key", "")
            number = pick.get("number", "")
            confidence = pick.get("confidence", 0)
            confidence_band = pick.get("confidence_band", "")
            best_odds = pick.get("best_odds", "")
            color = pick.get("color", "")
            alignment_strength = pick.get("alignment_strength", "")
            north_node_alignment = pick.get("north_node_alignment", "")
            marketing_triggers = ",".join(pick.get("marketing_triggers", []))

            row = [
                tracking_key,
                kit_name,
                subscriber_id,
                period,
                date_str,
                game,
                session,
                number,
                confidence,
                confidence_band,
                best_odds,
                color,
                alignment_strength,
                north_node_alignment,
                marketing_triggers,
                "",            # hit_type (filled by audit later)
                "",            # winning_number (filled by audit later)
                now
            ]
            writer.writerow(row)
