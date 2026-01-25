# core/daily_loader_v3_7.py

import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ga_results")

FILENAME_MAP = {
    "CASH3": "cash3_results.csv",
    "CASH4": "cash4_results.csv",
}

def load_daily(game: str) -> pd.DataFrame:
    """
    Load Georgia Cash3 / Cash4 results.

    Expected columns:
        draw_date, draw_time, result, sum, digits...
    """
    game_upper = game.upper()
    if game_upper not in FILENAME_MAP:
        raise ValueError(f"Unsupported daily game: {game}")

    filepath = os.path.join(DATA_DIR, FILENAME_MAP[game_upper])

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Daily results not found: {filepath}")

    df = pd.read_csv(filepath)

    # Normalize dates
    if "draw_date" in df.columns:
        df["draw_date"] = pd.to_datetime(df["draw_date"])
    else:
        raise ValueError(f"Missing draw_date in {filepath}")

    # Normalize draw_time
    if "draw_time" not in df.columns:
        df["draw_time"] = "Unknown"

    return df.sort_values(["draw_date", "draw_time"])
