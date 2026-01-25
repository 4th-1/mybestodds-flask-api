#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ENRICH_v3_7.py — Patch Pack D+E + Jackpot Scaffold (FINAL, CLAMPED)
------------------------------------------------------------------
Runs the complete enrichment pipeline across any kit folder.

IMPORTANT:
- Internal analytics & jackpot intelligence are allowed
- forecast.csv output MUST match V37_COLUMNS exactly
"""

import os
import sys
import pandas as pd

# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
CORE_DIR = os.path.join(PARENT_DIR, "core")

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

# ---------------------------------------------------------
# SCHEMA CONTRACT (🔥 SINGLE SOURCE OF TRUTH 🔥)
# ---------------------------------------------------------
from core.forecast_writer_v3_7 import V37_COLUMNS

def clamp_df_to_v37(df: pd.DataFrame) -> pd.DataFrame:
    """
    FINAL SAFETY GATE:
    - Drops ALL non-contract columns
    - Enforces exact column order
    """
    return df.reindex(columns=V37_COLUMNS)

# ---------------------------------------------------------
# LEFT ENGINE (v3.7)
# ---------------------------------------------------------
from core.row_enricher_v3_7 import enrich_row_v3_7
from core.predictive_core_v3_7 import enrich_forecast as enrich_predictive
from core.personalization_layer_v3_7 import enrich_forecast as enrich_personal
from core.final_selector_v3_7 import enrich_forecast as enrich_selector

# ---------------------------------------------------------
# RIGHT ENGINE (v4.0)
# ---------------------------------------------------------
from core.jackpot_scaffold_v4_0 import scaffold_jackpot_columns
from core.jackpot_predictive_v4_0 import enrich_forecast as enrich_jk_predictive
from core.jackpot_alignment_v4_0 import enrich_forecast as enrich_jk_alignment
from core.jackpot_selector_v4_0 import enrich_forecast as enrich_jk_selector


# =========================================================
# PROCESS A SINGLE KIT
# =========================================================
def process_kit(kit_folder: str) -> None:

    forecast_path = os.path.join(kit_folder, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[SKIP] No forecast.csv in {kit_folder}")
        return

    print(f"[ENRICH] Processing {forecast_path}")

    # 1) LOAD CSV
    df = pd.read_csv(forecast_path, dtype=str)

    # 2) ROW ENRICHER (v3.7)
    df = pd.DataFrame([enrich_row_v3_7(dict(r)) for _, r in df.iterrows()])

    # 3) PREDICTIVE CORE v3.7
    df = enrich_predictive(df)

    # 4) PERSONALIZATION LAYER v3.7
    df = enrich_personal(df)

    # 5) FINAL SELECTOR v3.7
    df = enrich_selector(df)

    # 6) JACKPOT SCAFFOLD
    df = scaffold_jackpot_columns(df)

    # 7) RIGHT ENGINE (v4.0) — jackpot rows only
    jackpot_mask = df.get("jk_is_jackpot_game", False) == True

    if jackpot_mask.any():
        df_jk = df[jackpot_mask].copy()
        df_non = df[~jackpot_mask].copy()

        df_jk = enrich_jk_predictive(df_jk)
        df_jk = enrich_jk_alignment(df_jk)
        df_jk = enrich_jk_selector(df_jk)

        df = pd.concat([df_jk, df_non], ignore_index=True)

    # -----------------------------------------------------
    # 🔒 FINAL CONTRACT ENFORCEMENT (THIS WAS MISSING)
    # -----------------------------------------------------
    df = clamp_df_to_v37(df)

    # 8) SAVE OUTPUT
    df.to_csv(forecast_path, index=False)
    print(f"[DONE] Updated forecast → {forecast_path}")


# =========================================================
# MAIN ENTRY
# =========================================================
def main(argv=None) -> int:
    argv = argv or sys.argv[1:]

    if not argv:
        print("Usage: python ENRICH_v3_7.py path/to/kit_folder [...]")
        return 1

    for kit in argv:
        process_kit(os.path.abspath(kit))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
