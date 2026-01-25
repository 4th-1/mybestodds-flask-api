# core/jackpot_loader_v4_0.py

import os
import pandas as pd

# --------------------------------------------------------
# Locate jackpot results folder
# --------------------------------------------------------
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "jackpot_results"
)

# --------------------------------------------------------
# Normalize ALL name formats here
# --------------------------------------------------------
GAME_NORMALIZE = {
    # Mega Millions
    "MEGAMILLIONS": "MegaMillions",
    "MEGA MILLIONS": "MegaMillions",
    "MEGA_MILLIONS": "MegaMillions",
    "MEGA": "MegaMillions",
    "MM": "MegaMillions",

    # Powerball
    "POWERBALL": "Powerball",
    "POWER BALL": "Powerball",
    "PB": "Powerball",

    # Cash4Life
    "CASH4LIFE": "Cash4Life",
    "CASH 4 LIFE": "Cash4Life",
    "CASH-4-LIFE": "Cash4Life",
    "C4L": "Cash4Life",
}

# File mapping
FILENAME_MAP = {
    "MegaMillions": "MegaMillions.csv",
    "Powerball": "Powerball.csv",
    "Cash4Life": "Cash4Life.csv",
}


# --------------------------------------------------------
# Loader Function
# --------------------------------------------------------
def load_jackpot(game: str) -> pd.DataFrame:
    """
    Loads and normalizes MegaMillions, Powerball, and Cash4Life data.
    
    Output columns:
        draw_date, n1..n5, bonus, jackpot
    """

    # Normalize game name safely
    key = GAME_NORMALIZE.get(game.upper())
    if key is None:
        raise ValueError(f"[jackpot_loader_v4_0] Unsupported game: {game}")

    filename = FILENAME_MAP[key]
    filepath = os.path.join(DATA_DIR, filename)

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"[jackpot_loader_v4_0] File not found: {filepath}")

    df = pd.read_csv(filepath)
    df = df.rename(columns=str.lower)

    # ------------------------------
    # Normalize draw date
    # ------------------------------
    date_cols = ["draw_date", "date", "drawdate"]
    date_found = None

    for col in date_cols:
        if col in df.columns:
            df["draw_date"] = pd.to_datetime(df[col])
            date_found = True
            break

    if not date_found:
        raise ValueError(f"[jackpot_loader_v4_0] No valid date column in: {filepath}")

    # ------------------------------
    # Normalize number columns
    # ------------------------------
    # Accept ANY of these formats:
    # n1..n5, num1..num5, ball1..ball5
    number_candidates = []

    for prefix in ["n", "num", "ball"]:
        for i in range(1, 6):
            col = f"{prefix}{i}"
            if col in df.columns:
                number_candidates.append(col)

    if len(number_candidates) < 5:
        raise ValueError(f"[jackpot_loader_v4_0] Missing main numbers in: {filepath}")

    # Ensure correct output names
    for i, col in enumerate(number_candidates[:5], start=1):
        df[f"n{i}"] = df[col]

    # ------------------------------
    # Normalize bonus column
    # ------------------------------
    bonus_col = None
    for bc in ["mb", "pb", "bonus", "megaball", "powerball"]:
        if bc in df.columns:
            bonus_col = bc
            break

    df["bonus"] = df[bonus_col] if bonus_col else None

    # ------------------------------
    # Normalize jackpot amount
    # ------------------------------
    jackpot_col = next(
        (c for c in df.columns if "jackpot" in c.lower() or "est" in c.lower()),
        None
    )
    df["jackpot"] = df[jackpot_col] if jackpot_col else None

    # ------------------------------
    # Final standardized output
    # ------------------------------
    final_cols = ["draw_date", "n1", "n2", "n3", "n4", "n5", "bonus", "jackpot"]

    df = df[final_cols].sort_values("draw_date").reset_index(drop=True)

    return df
