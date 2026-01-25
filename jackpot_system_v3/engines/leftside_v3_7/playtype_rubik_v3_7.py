"""
playtype_rubik_v3_7.py
----------------------

Purpose:
    Centralize play-type and BOB (Best Odds Bonus) decisions for v3.7
    using the LEFT ENGINE daily index as input.

This module:
    • Takes daily_index_v3_7 outputs (cash3_daily / cash4_daily)
    • Assigns:
        - primary_play (Straight / Box / StrBox / Combo)
        - BOB helper text (“Add Box for Safety”, etc.)
        - BOB strength (High / Medium / Low)
        - Confidence band emoji (🟩 / 🟨 / 🤎 / 🚫)
        - Raw 0–100 score for future BOSK hooks

Key API:
    • suggest_playtype_for_row(game, row) -> PlayTypeDecision
    • apply_playtype_rubik(daily_df, game) -> DataFrame

You can plug this into the RIGHT ENGINE later without changing callers;
the surface API is intentionally simple and stable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple

import pandas as pd


@dataclass
class PlayTypeDecision:
    """
    Container for a single play-type / BOB decision.

    Fields:
        primary_play:      Core play type (Straight, Box, StrBox, Combo, etc.)
        bob_suggestion:    Optional BOB helper text ("Add Box for Safety", etc.)
        bob_strength:      High / Medium / Low indicator for BOB.
        confidence_band:   🟩 / 🟨 / 🤎 / 🚫 based on internal score.
        raw_score:         Numeric 0–100 style score (for future BOSK hooks).
        notes:             Human-readable explanation for the decision.
    """
    primary_play: str
    bob_suggestion: Optional[str] = None
    bob_strength: Optional[str] = None
    confidence_band: str = "🟨"
    raw_score: float = 0.0
    notes: str = ""


# -------------------------------------------------------------------
# Simple confidence scoring helpers
# -------------------------------------------------------------------

def _compute_base_score(last_seen_gap: float, roll_freq: float) -> float:
    """
    Very lightweight scoring heuristic.

    Intuition:
        - Larger last_seen_gap → slightly higher score (more 'due')
        - Smaller roll_freq_last_N → slightly higher score
        - This is intentionally simple; BOSK / ML engines can
          override or replace this later.
    """
    if last_seen_gap is None:
        last_seen_gap = 0.0

    if roll_freq is None:
        roll_freq = 0.0

    # Normalize in a soft way
    gap_term = min(float(last_seen_gap) / 50.0, 2.0)      # cap
    freq_term = max(0.0, 1.0 - float(roll_freq) / 10.0)   # fewer hits → closer to 1

    score = (gap_term * 40.0) + (freq_term * 60.0)
    return max(0.0, min(score, 100.0))


def _score_to_band(score: float) -> str:
    """
    Map numeric score into the same visual bands you use elsewhere:

        🟩  Strong signal
        🟨  Decent edge
        🤎  Low odds
        🚫  Skip zone

    Thresholds are placeholders for now and can be tightened later.
    """
    if score >= 80:
        return "🟩"
    if score >= 60:
        return "🟨"
    if score >= 40:
        return "🤎"
    return "🚫"


# -------------------------------------------------------------------
# BOB decision helpers
# -------------------------------------------------------------------

def _basic_pattern_flags(row: pd.Series) -> Tuple[bool, bool, bool]:
    """
    Convenience wrapper; row is expected to come from daily_index_v3_7
    where has_double / has_triple / has_quad are already computed.
    """
    has_double = bool(row.get("has_double", 0))
    has_triple = bool(row.get("has_triple", 0))
    has_quad = bool(row.get("has_quad", 0))
    return has_double, has_triple, has_quad


def _choose_primary_play(game: str, has_double: bool, has_triple: bool, has_quad: bool) -> str:
    """
    Very lightweight play-type chooser; this mirrors the spirit of 3.6
    without being locked to its exact implementation.

    You can refine this table later without changing the outer API.
    """
    game = game.lower()

    if game == "cash3":
        if has_triple:
            return "Straight/Box"
        if has_double:
            return "Straight/Box"
        return "Straight"

    # cash4
    if has_quad:
        return "Combo"
    if has_triple:
        return "Straight/Box"
    if has_double:
        return "Straight/Box"
    return "Straight"


def _choose_bob_suggestion(
    game: str,
    band: str,
    has_double: bool,
    has_triple: bool,
    has_quad: bool,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Encodes your BOB philosophy in a compact way.

    Returns:
        (bob_suggestion, bob_strength)
    """
    game = game.lower()

    # Skip zone: do not recommend any BOB expansion
    if band == "🚫":
        return "Straight Only (No BOB)", "Low"

    # Strong band: lean into more coverage options
    if band == "🟩":
        if has_quad or has_triple:
            return "BOB Strong: Add Combo (High Return)", "High"
        if has_double:
            return "Add Box for Safety", "Medium"
        return "Add 1-Off", "Medium"

    # Decent edge
    if band == "🟨":
        if has_double or has_triple:
            return "Add Box for Safety", "Medium"
        return "Add Back Pair Only", "Low"

    # Low odds
    if band == "🤎":
        if has_double:
            return "Add Box for Safety (Optional)", "Low"
        return "Straight Only (Optional BOB)", "Low"


def suggest_playtype_for_row(
    game: str,
    row: pd.Series,
) -> PlayTypeDecision:
    """
    Core decision engine for a single draw row.

    Expects row to come from the v3.7 daily index table with
    at least the following columns:
        - last_seen_gap
        - roll_freq_last_N
        - has_double
        - has_triple
        - has_quad
    """
    has_double, has_triple, has_quad = _basic_pattern_flags(row)

    # 1) Base score + confidence band
    last_gap = row.get("last_seen_gap", 0)
    roll_freq = row.get("roll_freq_last_N", 0)
    score = _compute_base_score(last_gap, roll_freq)
    band = _score_to_band(score)

    # 2) Primary play
    primary_play = _choose_primary_play(game, has_double, has_triple, has_quad)

    # 3) BOB
    bob_suggestion, bob_strength = _choose_bob_suggestion(
        game=game,
        band=band,
        has_double=has_double,
        has_triple=has_triple,
        has_quad=has_quad,
    )

    # 4) Notes (for Sentinel / Oracle hover text later)
    notes_parts = [
        f"Game={game.upper()}",
        f"gap={last_gap}",
        f"freqN={roll_freq}",
        f"pattern double={int(has_double)}, triple={int(has_triple)}, quad={int(has_quad)}",
    ]
    notes = " | ".join(notes_parts)

    return PlayTypeDecision(
        primary_play=primary_play,
        bob_suggestion=bob_suggestion,
        bob_strength=bob_strength,
        confidence_band=band,
        raw_score=round(score, 2),
        notes=notes,
    )


def apply_playtype_rubik(
    daily_df: pd.DataFrame,
    game: str,
) -> pd.DataFrame:
    """
    Vectorized application of the PlayType Rubik over a daily index DataFrame.

    Input:
        daily_df: DataFrame from daily_index_v3_7.build_daily_index_context()[f"{game}_daily"]
        game:     "cash3" or "cash4"

    Output:
        A NEW DataFrame including the following additional columns:
            - primary_play
            - bob_suggestion
            - bob_strength
            - confidence_band
            - raw_score
            - play_notes
    """
    if daily_df is None or daily_df.empty:
        return daily_df

    game = game.lower()

    decisions: Dict[int, Dict[str, Any]] = {}

    for idx, row in daily_df.iterrows():
        decision = suggest_playtype_for_row(game, row)
        decisions[idx] = asdict(decision)

    dec_df = pd.DataFrame.from_dict(decisions, orient="index")
    dec_df.index = daily_df.index

    merged = pd.concat([daily_df.copy(), dec_df], axis=1)
    merged.rename(columns={"notes": "play_notes"}, inplace=True)

    return merged


__all__ = [
    "PlayTypeDecision",
    "suggest_playtype_for_row",
    "apply_playtype_rubik",
]
