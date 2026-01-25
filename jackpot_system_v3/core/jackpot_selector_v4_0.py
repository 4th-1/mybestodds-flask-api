# core/jackpot_selector_v4_0.py
# ---------------------------------
# Selector layer for Jackpot Right Engine.
#
# Uses:
#   - jackpot_alignment_score
#   - wls (if present)
#   - mbo_odds (if present)
#
# Produces (for jackpot rows only):
#   - jackpot_score         (internal combined score)
#   - jackpot_rank          (1 = best for that game/date)
#   - jackpot_pick_flag     (True/False: recommended pick)
#   - jackpot_tier          ("PRIMARY", "SECONDARY", "LONGSHOT")

from typing import Any
import pandas as pd

from .jackpot_core_v4_0 import is_jackpot_game


def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank jackpot candidates per game/draw_date and tag recommended picks.
    """
    if "game" not in df.columns or "draw_date" not in df.columns:
        return df

    mask = df["game"].apply(is_jackpot_game)
    if not mask.any():
        return df

    jdf = df[mask].copy()

    # Base fields
    align = jdf.get(
        "jackpot_alignment_score", pd.Series(0.5, index=jdf.index)
    ).astype(float)

    wls = jdf.get("wls", pd.Series(0.5, index=jdf.index)).astype(float)

    # Lower mbo_odds = better (1-in-78 is better than 1-in-1200)
    mbo_raw = jdf.get("mbo_odds", pd.Series(500.0, index=jdf.index)).astype(float)
    # Avoid division by zero
    inv_mbo = mbo_raw.replace(0, 1.0)
    inv_mbo = 1.0 / inv_mbo

    # Normalize to a combined score (0–1-ish)
    # Weight alignment most heavily
    jackpot_score = (
        0.50 * align +
        0.30 * wls +
        0.20 * inv_mbo
    )

    jdf["jackpot_score"] = jackpot_score

    # Rank within each game/date by score (descending)
    jdf["jackpot_rank"] = (
        jdf.groupby(["game", "draw_date"])["jackpot_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # Decide pick tiers
    def tier_from_rank(r: int) -> str:
        if r <= 3:
            return "PRIMARY"
        if r <= 7:
            return "SECONDARY"
        return "LONGSHOT"

    jdf["jackpot_tier"] = jdf["jackpot_rank"].apply(tier_from_rank)
    jdf["jackpot_pick_flag"] = jdf["jackpot_tier"].isin(["PRIMARY", "SECONDARY"])

    # Push back into main df
    for col in [
        "jackpot_score",
        "jackpot_rank",
        "jackpot_tier",
        "jackpot_pick_flag",
    ]:
        df.loc[mask, col] = jdf[col]

    return df
