#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
final_selector_v3_7.py
----------------------
My Best Odds – v3.7 Final Pick Selector

Role:
- Take enriched forecast.csv (with WLS, odds, confidence, etc.)
- Select "core" picks per draw
- Add simple BOB guidance

Outputs:
    - core_pick_rank   (1,2,3... within the game/day/time; NaN if not core)
    - is_core_pick     (True/False)
    - bob_action       (text code)
    - bob_note         (human explanation)

Game pick limits (per draw):
    Cash3       → top 3 by WLS
    Cash4       → top 3
    MegaMillions→ top 2
    Powerball   → top 2
    Cash4Life   → top 1
    other       → top 3
"""

import os
import sys
from typing import Dict

import numpy as np
import pandas as pd


PICK_LIMITS: Dict[str, int] = {
    "Cash3": 3,
    "Cash4": 3,
    "MegaMillions": 2,
    "Powerball": 2,
    "Cash4Life": 1,
}


def _pick_limit_for_game(game: str) -> int:
    return PICK_LIMITS.get(str(game), 3)


def apply_core_selection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag core picks using WLS within each (kit_name, game, draw_date, draw_time).
    """
    required = ["kit_name", "game", "draw_date", "draw_time", "wls"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"final_selector_v3_7: required column missing: {c}")

    df["core_pick_rank"] = np.nan
    df["is_core_pick"] = False

    group_keys = ["kit_name", "game", "draw_date", "draw_time"]

    for (kit, game, ddate, dtime), g in df.groupby(group_keys):
        limit = _pick_limit_for_game(game)
        # sort by WLS descending
        g_sorted = g.sort_values("wls", ascending=False)

        core_indices = g_sorted.index[:limit]
        ranks = range(1, len(core_indices) + 1)

        df.loc[core_indices, "core_pick_rank"] = list(ranks)
        df.loc[core_indices, "is_core_pick"] = True

    return df


def apply_bob_logic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple BOB decision based on confidence_band & core_pick_rank.
    """
    # ensure columns
    for c in ["bob_action", "bob_note", "confidence_band",
              "core_pick_rank", "play_type"]:
        if c not in df.columns:
            df[c] = np.nan

    actions = []
    notes = []

    for band, rank, play_type in zip(
        df["confidence_band"], df["core_pick_rank"], df["play_type"]
    ):
        band = str(band)
        pt = str(play_type)

        if np.isnan(rank):
            # non-core picks → no BOB
            actions.append("NONE")
            notes.append("Non-core pick – no BOB applied.")
            continue

        if band == "🟩":
            actions.append("BOB_STRONG_COMBO")
            notes.append("Strong edge – consider Straight + Box or Combo.")
        elif band == "🟨":
            if "Box" in pt:
                actions.append("KEEP_BOX")
                notes.append("Decent edge – keep Box for safety.")
            else:
                actions.append("ADD_BOX")
                notes.append("Decent edge – add Box for near-miss protection.")
        elif band == "🤎":
            actions.append("STRAIGHT_ONLY_LIGHT")
            notes.append("Low odds – Straight only, small stake if you play.")
        else:  # "🚫" or anything else
            actions.append("SKIP")
            notes.append("Skip – extremely low probability for this draw.")

    df["bob_action"] = actions
    df["bob_note"] = notes

    return df


def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    df = apply_core_selection(df)
    df = apply_bob_logic(df)
    return df


def _process_kit_folder(kit_folder: str) -> None:
    forecast_path = os.path.join(kit_folder, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_folder}")
        return

    print(f"[FINAL SELECTOR] Enriching: {forecast_path}")
    df = pd.read_csv(forecast_path)
    df = enrich_forecast(df)
    df.to_csv(forecast_path, index=False)
    print(f"[DONE] Updated forecast.csv in {kit_folder}")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m core.final_selector_v3_7 path/to/kit_folder [...]")
        return 1

    for kit in argv:
        _process_kit_folder(os.path.abspath(kit))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
