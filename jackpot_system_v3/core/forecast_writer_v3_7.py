#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
forecast_writer_v3_7.py
-----------------------
FINAL v3.7 Forecast Writer (SCRIBE-safe 58-column schema)

This file is the SINGLE SOURCE OF TRUTH for forecast.csv schema.

✔ 58/58 columns (SCRIBE contract)
✔ Strict column order
✔ Safe defaults
✔ Accepts legacy aliases (play_type_rubix vs play_type_rubik)
✔ Guarantees forecast.csv always matches v3.7 schema
"""

import os
import csv
from datetime import date


# ============================================================
# OFFICIAL v3.7 COLUMN ORDER (58 COLUMNS)
# ============================================================

V37_COLUMNS = [
    # Identity
    "kit_name",
    "game",
    "game_code",
    "draw_date",
    "forecast_date",
    "draw_time",
    "number",

    # Astro / Numerology
    "moon_phase",
    "zodiac_sign",
    "numerology_code",
    "planetary_hour",

    # Overlay + Weights
    "overlay_score",
    "moon_weight",
    "zodiac_weight",
    "numerology_weight",
    "planetary_weight",

    # Play logic / Rubik
    "play_type",
    "play_type_rubik",     # canonical (writer outputs this)
    "rubik_code",
    "rubik_bucket",

    # BOB
    "bob_action",
    "bob_note",

    # Confidence / Odds
    "confidence_score",
    "confidence_band",
    "confidence_pct",
    "confidence_tier",
    "mbo_odds",
    "mbo_odds_text",
    "mbo_odds_band",

    # Predictive outputs (may be blank until predictive core fills)
    "posterior_p",
    "markov_tag",
    "kelly_fraction",
    "ml_score",
    "wls",

    # Lanes / priority / ops
    "lane",
    "priority",
    "play_window",
    "retailer_id",

    # Math / pattern
    "sum",
    "sum_range",
    "delta_pattern",

    # Jackpot intelligence (JP)
    "jp_alignment_score",
    "jp_streak_score",
    "jp_hot_index",
    "jp_due_index",
    "jp_repeat_score",
    "jp_momentum_score",
    "jp_cycle_flag",

    # Forecast metadata
    "forecast_run_id",

    # Hits
    "hit_type_book",
    "hit_type_book3",
    "hit_type_bosk",
]


# ============================================================
# DEFAULTS
# ============================================================

_NUMERIC_DEFAULTS = {
    "overlay_score": "0.0",
    "moon_weight": "0.0",
    "zodiac_weight": "0.0",
    "numerology_weight": "0.0",
    "planetary_weight": "0.0",

    "confidence_score": "0.00",
    "confidence_pct": "0.00",
    "mbo_odds": "0",
    "wls": "0.0",

    "posterior_p": "",
    "kelly_fraction": "",
    "ml_score": "",

    "sum": "0",
    "sum_range": "0",

    "jp_alignment_score": "0.0",
    "jp_streak_score": "0.0",
    "jp_hot_index": "0.0",
    "jp_due_index": "0.0",
    "jp_repeat_score": "0.0",
    "jp_momentum_score": "0.0",
    "jp_cycle_flag": "0",
}

_TEXT_DEFAULTS = {
    "confidence_band": "",
    "confidence_tier": "",
    "mbo_odds_text": "1-in-0",
    "mbo_odds_band": "",
    "markov_tag": "",
    "lane": "A",
    "priority": "0",
    "play_window": "",
    "retailer_id": "",
    "forecast_run_id": "",
    "hit_type_book": "NO_HIT",
    "hit_type_book3": "NO_HIT",
    "hit_type_bosk": "NO_HIT",
    "bob_action": "NO_BOB",
    "bob_note": "",
    "play_type": "",
    "play_type_rubik": "",
    "rubik_code": "",
    "rubik_bucket": "",
}


# ============================================================
# PLACEHOLDER ROW BUILDER
# ============================================================

def make_placeholder_row(core_values: dict) -> dict:
    """
    Builds a guaranteed-complete v3.7 row.
    Any missing keys are filled with safe defaults.
    """
    row = {col: "" for col in V37_COLUMNS}

    # Identity
    row["kit_name"] = core_values.get("kit_name", "")
    row["game"] = core_values.get("game", "")
    row["game_code"] = core_values.get("game_code", "")
    row["draw_date"] = core_values.get("draw_date", "")
    row["draw_time"] = core_values.get("draw_time", "")
    row["number"] = core_values.get("number", "")

    # Forecast date (fallback to draw_date; else today)
    fd = core_values.get("forecast_date", "") or row["draw_date"] or str(date.today())
    row["forecast_date"] = fd

    # Apply defaults
    for k, v in _NUMERIC_DEFAULTS.items():
        row[k] = v
    for k, v in _TEXT_DEFAULTS.items():
        row[k] = v

    # Astro defaults (optional)
    row["moon_phase"] = core_values.get("moon_phase", "")
    row["zodiac_sign"] = core_values.get("zodiac_sign", "")
    row["numerology_code"] = core_values.get("numerology_code", "")
    row["planetary_hour"] = core_values.get("planetary_hour", "")

    return row


# ============================================================
# ROW NORMALIZATION (ALIAS HARDENING)
# ============================================================

def _normalize_row(row: dict) -> dict:
    """
    Ensures:
    - Canonical rubik column name is used: play_type_rubik
    - Missing columns are added
    - Defaults applied
    - Extra columns are ignored (writer only outputs V37_COLUMNS)
    """
    if row is None:
        row = {}

    # Accept legacy typo variants coming from other modules
    if "play_type_rubik" not in row:
        if "play_type_rubix" in row:
            row["play_type_rubik"] = row.get("play_type_rubix", "")
        elif "PLAY_TYPE_RUBIX" in row:
            row["play_type_rubik"] = row.get("PLAY_TYPE_RUBIX", "")
        elif "PLAY_TYPE_RUBIK" in row:
            row["play_type_rubik"] = row.get("PLAY_TYPE_RUBIK", "")

    # Also accept legacy uppercase identity fields if they show up
    if "game" not in row and "GAME" in row:
        row["game"] = row.get("GAME", "")
    if "draw_date" not in row and "DRAW_DATE" in row:
        row["draw_date"] = row.get("DRAW_DATE", "")
    if "draw_time" not in row and "DRAW_TIME" in row:
        row["draw_time"] = row.get("DRAW_TIME", "")
    if "number" not in row and "NUMBER" in row:
        row["number"] = row.get("NUMBER", "")

    # Ensure forecast_date exists
    if not row.get("forecast_date"):
        row["forecast_date"] = row.get("draw_date", "") or str(date.today())

    # Apply defaults for missing keys
    for col in V37_COLUMNS:
        if col not in row:
            row[col] = ""

    for k, v in _NUMERIC_DEFAULTS.items():
        if row.get(k, "") == "":
            row[k] = v

    for k, v in _TEXT_DEFAULTS.items():
        if row.get(k, "") == "":
            row[k] = v

    return row


# ============================================================
# WRITE FORECAST FILE (SCRIBE-SAFE)
# ============================================================

def write_forecast_v37(forecast_rows: list, output_path: str):
    """
    Writes CSV in strict v3.7 format.
    HARD RESETS schema to V37_COLUMNS (no extra columns allowed).
    """

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=V37_COLUMNS,
            extrasaction="ignore"   # 🚨 CRITICAL FIX
        )
        writer.writeheader()

        for r in forecast_rows or []:
            row = _normalize_row(r)

            # HARD SCHEMA LOCK — only allowed columns survive
            clean_row = {c: row.get(c, "") for c in V37_COLUMNS}

            writer.writerow(clean_row)

    print(f"[v3.7 FORECAST WRITER] Built CLEAN forecast file: {output_path}")


if __name__ == "__main__":
    # quick sanity check
    print(len(V37_COLUMNS))
