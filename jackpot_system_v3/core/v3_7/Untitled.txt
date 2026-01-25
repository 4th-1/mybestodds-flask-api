"""
sentinel_engine_v3_7.py

Sentinel policy enforcement layer for My Best Odds v3.7
"""

from datetime import datetime
from typing import List, Dict, Any

JACKPOT_DRAW_DAYS = {
    "MEGAMILLIONS": {1, 4},
    "POWERBALL": {1, 4},
    "CASH4LIFE": {0, 2, 4, 6},
}

def is_draw_day(game_code: str, forecast_date: str) -> bool:
    try:
        dt = datetime.fromisoformat(forecast_date)
    except Exception:
        return False
    return dt.weekday() in JACKPOT_DRAW_DAYS.get(game_code.upper(), set())

def log(msg: str):
    print(msg)

def sentinel_filter_jackpot_rows(
    rows: List[Dict[str, Any]],
    game_code: str,
    forecast_date: str,
    kit_type: str,
) -> List[Dict[str, Any]]:

    if not rows:
        return []

    draw_day = is_draw_day(game_code, forecast_date)

    if not draw_day:
        if kit_type == "BOOK3":
            log(f"[JACKPOT] PREVIEW MODE: allowing non-draw-day picks for BOOK3 ({game_code} {forecast_date})")
            for row in rows:
                row["preview"] = True
            return rows
        else:
            log(f"[JACKPOT] NOT draw day: suppressing jackpot picks ({game_code} {forecast_date})")
            return []

    log(f"[JACKPOT] DRAW DAY confirmed: allowing jackpot picks ({game_code} {forecast_date})")
    for row in rows:
        row["preview"] = False

    return rows
