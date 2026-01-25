"""
jackpot_ingest_v3_6.py

Right-side ingest layer for My Best Odds v3.6 (Mega Millions, Powerball, Cash4Life).

Responsibilities:
- Load raw historical jackpot results
- Normalize into a standard dataframe shape
- Provide 50-draw windows for the engine
- Expose helper functions to compute cycle / hot-cold / streak features

NOTE:
- This is a structural/scaffolding module.
  You will plug in your actual CSV paths and any state-specific parsing details.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Dict, Any

import pandas as pd


# ---------------------------------------------------------
# TYPE DEFINITIONS
# ---------------------------------------------------------

GameName = Literal["megamillions", "powerball", "cash4life"]


@dataclass
class JackpotHistoryConfig:
    game: GameName
    csv_path: Path
    # You may add optional attributes (state, timezone, etc.)


# ---------------------------------------------------------
# LOAD & NORMALIZE HISTORY
# ---------------------------------------------------------

def load_history(cfg: JackpotHistoryConfig) -> pd.DataFrame:
    """
    Load and normalize jackpot history for a given game.

    Expected CSV columns (adapt as needed):
        date (YYYY-MM-DD)
        n1, n2, n3, n4, n5
        bonus
        jackpot (optional)
    """
    df = pd.read_csv(cfg.csv_path)

    # Normalize column names where applicable
    rename_map = {
        "N1": "n1", "N2": "n2", "N3": "n3", "N4": "n4", "N5": "n5",
        "MegaBall": "bonus", "Powerball": "bonus", "LifeBall": "bonus",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Validate required columns
    required = ["date", "n1", "n2", "n3", "n4", "n5", "bonus"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {cfg.csv_path}: {missing}")

    # Parse dates
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Sort oldest → newest
    df = df.sort_values("date").reset_index(drop=True)

    return df


# ---------------------------------------------------------
# LAST 50 DRAWS
# ---------------------------------------------------------

def last_50_draws(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return last 50 draws in chronological order.
    If < 50 draws exist, return all.
    """
    if len(df) <= 50:
        return df.copy()
    return df.iloc[-50:].copy()


# ---------------------------------------------------------
# FEATURE GENERATION (STUBS)
# ---------------------------------------------------------

def compute_basic_features(df_50: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder for feature engineering.

    Your real features:
        - cycle_score
        - hot/cold metrics
        - overdue scoring
        - bonus clustering
        - pattern models
    """
    out = df_50.copy()

    # Stub columns (replace with real calculations later)
    out["cycle_score"] = 0.5
    out["hot_cold_score"] = 0.5
    out["overdue_score"] = 0.5
    out["bonus_cluster_score"] = 0.5
    out["pattern_score"] = 0.5

    return out


# ---------------------------------------------------------
# COMBINED FEATURE CONTEXT FOR ENGINE
# ---------------------------------------------------------

def build_feature_context(cfg: JackpotHistoryConfig) -> Dict[str, Any]:
    """
    Load history → filter last 50 → compute features → package into context dict.
    """
    df = load_history(cfg)
    df_50 = last_50_draws(df)
    feats = compute_basic_features(df_50)

    return {
        "history_all": df,
        "history_50": df_50,
        "features_50": feats,
    }
