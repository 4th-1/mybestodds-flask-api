#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VIEW_TOP_PICKS_v3_7.py
----------------------
Reader for My Best Odds v3.7 forecast files.

Role:
- Take a kit folder that contains forecast.csv
- For each (game, draw_date, draw_time) group:
    * Sort rows by confidence_score (DESC)
    * Take the top N rows
- Write a compact summary CSV with the strongest picks per draw.

Usage:

    python audit/VIEW_TOP_PICKS_v3_7.py output/BOOK3_2025-09-01_to-2025-11-10 --top 5
    python audit/VIEW_TOP_PICKS_v3_7.py output/BOOK_2025-09-01_to-2025-11-10 --top 3

Output:

    <kit_folder>/top_picks_summary_v3_7.csv
"""

import os
import sys
import argparse

import pandas as pd


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _safe_float_series(s, default=0.0):
    try:
        return pd.to_numeric(s, errors="coerce").fillna(default)
    except Exception:
        return pd.Series([default] * len(s))


def build_top_picks(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """
    Group by (game, draw_date, draw_time), sort by confidence_score DESC,
    and keep top N rows from each group.
    """

    # Ensure key columns exist
    required = ["game", "draw_date", "draw_time", "number"]
    for c in required:
        if c not in df.columns:
            df[c] = ""

    # Make sure confidence_score is numeric
    if "confidence_score" not in df.columns:
        df["confidence_score"] = 0.0

    df["confidence_score_num"] = _safe_float_series(df["confidence_score"], default=0.0)

    # Group and take top N
    group_cols = ["game", "draw_date", "draw_time"]
    grouped = (
        df
        .sort_values(group_cols + ["confidence_score_num"], ascending=[True, True, True, False])
        .groupby(group_cols, group_keys=False)
        .head(top_n)
    )

    # Build a compact view
    cols_out = [
        "game",
        "draw_date",
        "draw_time",
        "number",
        "confidence_score",
        "mbo_odds_text",
        "mbo_odds_band",
        "lane",
        "wls",
        "hit_type_book",
        "hit_type_book3",
        "hit_type_bosk",
    ]

    # Only keep columns that actually exist, in order
    cols_existing = [c for c in cols_out if c in grouped.columns]
    summary = grouped[cols_existing].copy()

    # Sort for readability
    summary = summary.sort_values(group_cols + ["confidence_score"], ascending=[True, True, True, False])

    return summary


def process_kit(kit_folder: str, top_n: int) -> None:
    forecast_path = os.path.join(kit_folder, "forecast.csv")

    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_folder}")
        return

    print(f"[VIEW] Reading {forecast_path}")
    try:
        df = pd.read_csv(forecast_path)
    except Exception as e:
        print(f"[ERROR] Could not read forecast.csv in {kit_folder}: {e}")
        return

    summary = build_top_picks(df, top_n=top_n)

    out_path = os.path.join(kit_folder, "top_picks_summary_v3_7.csv")
    try:
        summary.to_csv(out_path, index=False)
    except Exception as e:
        print(f"[ERROR] Could not write summary CSV in {kit_folder}: {e}")
        return

    print(f"[DONE] Top picks summary written → {out_path}")
    print(f"[INFO] Rows in summary: {len(summary)}")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(argv=None) -> int:
    argv = argv or sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="View top v3.7 picks per draw based on confidence_score."
    )
    parser.add_argument(
        "kit_folder",
        help="Path to a kit folder containing forecast.csv (e.g., output/BOOK3_2025-09-01_to-2025-11-10)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of top rows per (game, draw_date, draw_time) group to keep (default: 3).",
    )

    args = parser.parse_args(argv)

    kit_folder = os.path.abspath(args.kit_folder)
    if not os.path.isdir(kit_folder):
        print(f"[ERROR] Not a directory: {kit_folder}")
        return 1

    process_kit(kit_folder, top_n=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())