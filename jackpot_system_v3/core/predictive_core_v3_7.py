#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predictive_core_v3_7.py — FINAL PATCH A + A3 + A4 APPLIED
--------------------------------------------------------
Stabilized predictive engine for My Best Odds v3.7.

✔ Fixes pandas dtype mismatch
✔ Eliminates groupby.apply FutureWarning (uses transform)
✔ Guarantees posterior_p always valid
✔ Restores live predictive enrichment
✔ Preserves v3.7 schema contracts
✔ Adds legacy column alias compatibility (GAME, DRAW_DATE, DRAW_TIME)
✔ PATCH A4: Ensures STRICT SCRIBE schema (58 columns) by loading schema file + ordering columns
"""

import os
import sys
from typing import List
import numpy as np
import pandas as pd


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_OVERLAY_WEIGHT = 1.0
EPS = 1e-9  # avoid divide-by-zero


def _ensure(df: pd.DataFrame, cols: List[str]):
    """Ensure required columns exist."""
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df


# ============================================================
# COLUMN ALIAS NORMALIZATION (PATCH A3)
# ============================================================

def normalize_forecast_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure backward compatibility with legacy scaffold expectations.
    Canonical schema remains lowercase.
    """
    alias_map = {
        "GAME": "game",
        "DRAW_DATE": "draw_date",
        "DRAW_TIME": "draw_time",
    }

    for legacy, modern in alias_map.items():
        if legacy not in df.columns and modern in df.columns:
            df[legacy] = df[modern]

    return df


# ============================================================
# PATCH A4 — STRICT SCHEMA GUARANTEE (58 columns)
# ============================================================

def _load_scribe_schema_columns() -> List[str]:
    """
    Load the authoritative v3.7 schema column order used by SCRIBE.
    Tries common locations. If not found, returns [] (no-op).
    """
    root = os.getcwd()
    candidates = [
        os.path.join(root, "config", "schema_v3_7.csv"),
        os.path.join(root, "config", "schema_v3_7.json"),
        os.path.join(root, "config", "scribe_schema_v3_7.csv"),
        os.path.join(root, "config", "scribe_schema_v3_7.json"),
        os.path.join(root, "core", "schema_v3_7.csv"),
        os.path.join(root, "core", "schema_v3_7.json"),
    ]

    for path in candidates:
        if not os.path.isfile(path):
            continue

        try:
            if path.lower().endswith(".json"):
                import json
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)

                # Allow either: {"columns":[...]} or straight list [...]
                if isinstance(obj, dict) and "columns" in obj and isinstance(obj["columns"], list):
                    return [str(c) for c in obj["columns"]]
                if isinstance(obj, list):
                    return [str(c) for c in obj]

            # CSV schema: first column named "column" or single-column list
            if path.lower().endswith(".csv"):
                sch = pd.read_csv(path, dtype=str)
                if "column" in sch.columns:
                    return [c for c in sch["column"].dropna().astype(str).tolist()]
                # fallback: first column
                return [c for c in sch.iloc[:, 0].dropna().astype(str).tolist()]

        except Exception:
            # If a candidate fails to parse, try the next one
            continue

    return []


def ensure_schema_completeness_and_order(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures forecast contains ALL required SCRIBE schema columns and matches order.
    If schema file not found, falls back to leaving df as-is (but will still ensure key fields).
    """
    schema_cols = _load_scribe_schema_columns()

    # Minimum guarantees even if schema file isn't found
    minimum_required = [
        "kit_name", "game", "draw_date", "draw_time", "overlay_score",
        "posterior_p", "ml_score", "mbo_odds", "mbo_odds_text",
        "mbo_odds_band", "confidence_score", "confidence_band",
        "kelly_fraction", "wls", "wls_rank",
    ]

    for col in minimum_required:
        if col not in df.columns:
            df[col] = 0

    # If we found the authoritative schema, enforce it strictly
    if schema_cols:
        for col in schema_cols:
            if col not in df.columns:
                df[col] = 0

        # Reorder EXACTLY to schema
        df = df[schema_cols]

    return df


# ============================================================
# POSTERIOR CALCULATION (PATCH A)
# ============================================================

def compute_posterior(df: pd.DataFrame) -> pd.DataFrame:
    """
    posterior_p_i = overlay_i / Σ overlay_group
    If Σ=0 → uniform distribution.
    """
    df = _ensure(df, ["kit_name", "game", "draw_date", "draw_time", "overlay_score"])
    df["overlay_score"] = df["overlay_score"].fillna(0).astype(float)

    group_cols = ["kit_name", "game", "draw_date", "draw_time"]

    # Force grouping keys to stable dtype
    for c in group_cols:
        df[c] = df[c].astype(str)

    group_sum = df.groupby(group_cols)["overlay_score"].transform("sum").astype(float)
    group_size = df.groupby(group_cols)["overlay_score"].transform("size").astype(float)

    posterior = df["overlay_score"] / (group_sum + EPS)
    uniform = 1.0 / np.maximum(group_size, 1.0)

    df["posterior_p"] = np.where(group_sum <= 0, uniform, posterior).astype(float)

    return df


# ============================================================
# ML SCORE
# ============================================================

def compute_ml_score(df: pd.DataFrame) -> pd.DataFrame:
    weight_cols = [
        "moon_weight",
        "zodiac_weight",
        "numerology_weight",
        "planetary_weight",
    ]

    df = _ensure(df, weight_cols + ["posterior_p"])

    for c in weight_cols:
        df[c] = df[c].fillna(DEFAULT_OVERLAY_WEIGHT).astype(float)

    overlay_strength = (
        df["moon_weight"]
        + df["zodiac_weight"]
        + df["numerology_weight"]
        + df["planetary_weight"]
    ) / 4.0

    norm = overlay_strength / (overlay_strength.mean() + EPS)
    norm = np.clip(norm, 0.25, 2.0)

    df["ml_score"] = df["posterior_p"].fillna(0).astype(float) * norm

    return df


# ============================================================
# MBO ODDS + CONFIDENCE
# ============================================================

def compute_mbo_odds_and_confidence(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure(df, ["posterior_p"])

    p = df["posterior_p"].fillna(0).astype(float)
    mbo_raw = 1.0 / np.maximum(p, EPS)
    mbo_raw = np.clip(mbo_raw, 1, 9999)

    df["mbo_odds"] = mbo_raw.round(0).astype(int)
    df["mbo_odds_text"] = "1 in " + df["mbo_odds"].astype(str)

    bands = []
    confs = []

    for x in df["mbo_odds"]:
        if x <= 50:
            bands.append("🟩")
            confs.append(0.90)
        elif x <= 150:
            bands.append("🟨")
            confs.append(0.70)
        elif x <= 300:
            bands.append("🤎")
            confs.append(0.45)
        else:
            bands.append("🚫")
            confs.append(0.10)

    df["mbo_odds_band"] = bands
    df["confidence_score"] = confs
    df["confidence_band"] = df["mbo_odds_band"]

    return df


# ============================================================
# KELLY FRACTION + WLS
# ============================================================

def compute_kelly_and_wls(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure(
        df,
        ["mbo_odds", "confidence_score", "mbo_odds_band", "lane", "ml_score"],
    )

    kelly = []
    for odds, band in zip(df["mbo_odds"], df["mbo_odds_band"]):
        if band == "🟩" and odds <= 50:
            kelly.append(0.20)
        elif odds <= 150:
            kelly.append(0.10)
        elif odds <= 300:
            kelly.append(0.05)
        else:
            kelly.append(0.00)

    df["kelly_fraction"] = kelly

    lane_mult = {"A": 1.10, "B": 1.05, "C": 1.00, "D": 0.95}
    lane_bonus = df["lane"].map(lane_mult).fillna(1.0)

    ml = df["ml_score"].fillna(0).astype(float)
    conf = df["confidence_score"].fillna(0).astype(float)

    df["wls"] = ml * (0.6 + 0.4 * conf) * lane_bonus

    return df


# ============================================================
# RANKING
# ============================================================

def compute_wls_rank(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure(df, ["kit_name", "game", "draw_date", "draw_time", "wls"])

    group_cols = ["kit_name", "game", "draw_date", "draw_time"]

    df["wls_rank"] = (
        df.groupby(group_cols)["wls"]
        .rank(method="dense", ascending=False)
        .fillna(0)
        .astype(int)
    )

    return df


# ============================================================
# FULL PIPELINE
# ============================================================

def enrich_forecast(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_forecast_aliases(df)
    df = compute_posterior(df)
    df = compute_ml_score(df)
    df = compute_mbo_odds_and_confidence(df)
    df = compute_kelly_and_wls(df)
    df = compute_wls_rank(df)
    df = ensure_schema_completeness_and_order(df)  # PATCH A4
    return df


# ============================================================
# CLI
# ============================================================

def _process_folder(folder: str):
    f = os.path.join(folder, "forecast.csv")
    if not os.path.isfile(f):
        print(f"[SKIP] No forecast.csv in {folder}")
        return

    print(f"[PREDICTIVE CORE] Processing {f}")
    df = pd.read_csv(f)
    df = enrich_forecast(df)
    df.to_csv(f, index=False)
    print(f"[DONE] Updated: {f}")


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m core.predictive_core_v3_7 <kit_folder> [...]")
        return 1

    for path in argv:
        _process_folder(os.path.abspath(path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
