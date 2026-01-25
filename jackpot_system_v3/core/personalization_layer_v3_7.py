#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
personalization_layer_v3_7.py
-----------------------------
My Best Odds – v3.7 Personalization Layer

Role:
- Add a personal alignment score based on:
    * moon_weight
    * zodiac_weight
    * numerology_weight
    * planetary_weight
    * optional mmfsn_hit flag columns

Outputs:
    - personal_alignment_score  (0–1)
    - personal_alignment_band   ("CORE", "GOOD", "NEUTRAL", "LOW")

Usage:

    python -m core.personalization_layer_v3_7 path/to/kit_folder
"""

import os
import sys
from typing import List

import numpy as np
import pandas as pd


EPS = 1e-9


def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df


def compute_personal_alignment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine overlay weights + optional MMFSN flags into a 0–1 score.

    If present, these boolean/int flags are used:
        - mmfsn_cash3_hit
        - mmfsn_cash4_hit
    """
    weight_cols = ["moon_weight", "zodiac_weight",
                   "numerology_weight", "planetary_weight"]

    df = _ensure_columns(df, weight_cols)

    # fill defaults
    for c in weight_cols:
        df[c] = df[c].fillna(1.0).astype(float)

    base_score = (
        df["moon_weight"]
        + df["zodiac_weight"]
        + df["numerology_weight"]
        + df["planetary_weight"]
    ) / 4.0

    # Normalize base_score into approx [0, 1]
    mean = float(base_score.mean() + EPS)
    norm = base_score / (2.0 * mean)  # roughly [0, ~1]
    norm = np.clip(norm, 0.0, 1.0)

    # MMFSN bonus (BOOK3 only, but safe for all kits)
    mmfsn_cols = [c for c in df.columns if c.lower().startswith("mmfsn_") and c.endswith("_hit")]
    if mmfsn_cols:
        hit_sum = df[mmfsn_cols].fillna(0).sum(axis=1)
        hit_bonus = np.clip(hit_sum * 0.05, 0.0, 0.25)
    else:
        hit_bonus = 0.0

    score = np.clip(norm + hit_bonus, 0.0, 1.0)
    df["personal_alignment_score"] = score

    bands = []
    for s in score:
        if s >= 0.80:
            bands.append("CORE")
        elif s >= 0.60:
            bands.append("GOOD")
        elif s >= 0.35:
            bands.append("NEUTRAL")
        else:
            bands.append("LOW")
    df["personal_alignment_band"] = bands

    return df


def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    return compute_personal_alignment(df)


def _process_kit_folder(kit_folder: str) -> None:
    forecast_path = os.path.join(kit_folder, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_folder}")
        return

    print(f"[PERSONALIZATION] Enriching: {forecast_path}")
    df = pd.read_csv(forecast_path)
    df = enrich_forecast(df)
    df.to_csv(forecast_path, index=False)
    print(f"[DONE] Updated forecast.csv in {kit_folder}")


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m core.personalization_layer_v3_7 path/to/kit_folder [...]")
        return 1

    for kit in argv:
        _process_kit_folder(os.path.abspath(kit))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
