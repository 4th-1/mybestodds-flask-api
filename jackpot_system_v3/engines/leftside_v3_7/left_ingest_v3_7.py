"""
left_ingest_v3_7.py
-----------------------------------------
Structured upgrade of the v3.6 left-side ingestion engine.

Purpose:
    • Load GA Cash 3 / Cash 4 historical data
    • Normalize formats for 3.7 score engines
    • Maintain backwards compatibility with v3.6 layout
    • Provide a clean, validated ingest layer for Sentinel

This is the FIRST of 3 left-engine foundation files:
    1. left_ingest_v3_7.py   (you are here)
    2. daily_index_v3_7.py   (next)
    3. cash3_engine_v3_7.py / cash4_engine_v3_7.py
"""

from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, Any

# ---------------------------------------
# CONFIG
# ---------------------------------------

@dataclass
class LeftHistoryConfig:
    game: str
    csv_path: Path


# ---------------------------------------
# LOADER
# ---------------------------------------

def load_left_history(cfg: LeftHistoryConfig) -> pd.DataFrame:
    """
    Load GA Cash 3 / Cash 4 history.

    Expected CSV columns (adapted to match 3.6 for now):
        date (YYYY-MM-DD)
        draw_time (MIDDAY/EVENING/NIGHT)
        n1, n2, n3 (Cash 3)
        n4        (Cash 4 only)

    Automatically normalizes:
        • date → datetime.date
        • draw_time → upper-case
        • digits column → "XYZ" or "WXYZ"
    """
    df = pd.read_csv(cfg.csv_path)

    rename_map = {
        "DRAWDAT": "date",
        "DRAWDATE": "date",
        "DRAWTIME": "draw_time",
        "N1": "n1", "N2": "n2", "N3": "n3", "N4": "n4",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # --- Date Normalize ---
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    # --- Draw Time Normalize ---
    if "draw_time" in df.columns:
        df["draw_time"] = df["draw_time"].astype(str).str.upper().str.replace(" ", "")

    # --- Build digits ---
    def _digits(row):
        if cfg.game.lower() == "cash3":
            return f"{int(row['n1'])}{int(row['n2'])}{int(row['n3'])}"
        else:
            return f"{int(row['n1'])}{int(row['n2'])}{int(row['n3'])}{int(row['n4'])}"

    df["digits"] = df.apply(_digits, axis=1)

    # --- Sort ---
    df = df.sort_values(["date", "draw_time"]).reset_index(drop=True)

    return df


# ---------------------------------------
# TOP-LEVEL INGEST ENTRY POINT
# ---------------------------------------

def build_left_feature_context(cash3_csv: str, cash4_csv: str) -> Dict[str, Any]:
    """
    High-level ingest wrapper.

    Returns:
        {
            "cash3_history": <DataFrame>,
            "cash4_history": <DataFrame>,
        }
    """

    c3_cfg = LeftHistoryConfig(game="cash3", csv_path=Path(cash3_csv))
    c4_cfg = LeftHistoryConfig(game="cash4", csv_path=Path(cash4_csv))

    c3_hist = load_left_history(c3_cfg)
    c4_hist = load_left_history(c4_cfg)

    return {
        "cash3_history": c3_hist,
        "cash4_history": c4_hist,
    }


# ---------------------------------------
# TEST RUNNER (optional)
# ---------------------------------------

if __name__ == "__main__":
    print("Left ingest v3.7 OK — module loaded.")
