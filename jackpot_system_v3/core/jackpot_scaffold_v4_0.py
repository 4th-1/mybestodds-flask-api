# core/jackpot_scaffold_v4_0.py

import pandas as pd

JACKPOT_GAMES = {"MEGAMILLIONS", "POWERBALL", "CASH4LIFE"}

def scaffold_jackpot_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures every forecast.csv has the required jackpot columns.

    These start empty and will be filled in by:
        - jackpot_predictive_v4_0
        - jackpot_alignment_v4_0
        - jackpot_selector_v4_0
    """

    # Normalize GAME column
    if "GAME" in df.columns:
        df["GAME"] = df["GAME"].astype(str).str.upper()
    else:
        raise ValueError("FORECAST MISSING REQUIRED COLUMN: 'GAME'")

    # Flag jackpot rows
    df["jk_is_jackpot_game"] = df["GAME"].isin(JACKPOT_GAMES)

    # Provide normalized name to loader
    df["jk_game_name"] = df["GAME"].apply(
        lambda g: "MegaMillions" if g == "MEGAMILLIONS"
        else "Powerball" if g == "POWERBALL"
        else "Cash4Life" if g == "CASH4LIFE"
        else None
    )

    # Add empty metadata columns (placeholders)
    empty_cols = {
        "jk_draws_seen_to_date": None,
        "jk_last_hit_gap": None,
        "jk_alignment_score": None,
        "jk_pred_score": None,
        "jk_selector_score": None,
    }

    for col, val in empty_cols.items():
        if col not in df.columns:
            df[col] = val

    return df
