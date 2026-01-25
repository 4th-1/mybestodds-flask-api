"""
run_sentinel_book3_v3_7.py
Sentinel Audit Engine for BOOK3 — My Best Odds v3.7
---------------------------------------------------
Evaluates:
- Straight hits
- Box hits
- One-Off hits
- Miss distance (Δ)
- Confidence accuracy
- Play flags
- Legend correctness
"""

import os
import re
import json
import pandas as pd
from datetime import datetime

# ============================================================
# PATHS — AUTHORITATIVE v3.7 STRUCTURE
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOOK3_DIR = os.path.join(PROJECT_ROOT, "core", "v3_7", "output")
BOOK3_PREFIX = "BOOK3"

# ✅ CONFIRMED GA HISTORY FILES
HISTORY_C3 = os.path.join(
    PROJECT_ROOT, "data", "results", "ga_results", "cash3_results.csv"
)
HISTORY_C4 = os.path.join(
    PROJECT_ROOT, "data", "results", "ga_results", "cash4_results.csv"
)

OUT_JSON = os.path.join(PROJECT_ROOT, "audit", "audit_BOOK3_v3_7.json")
OUT_CSV  = os.path.join(PROJECT_ROOT, "audit", "audit_BOOK3_v3_7.csv")
OUT_SUM  = os.path.join(PROJECT_ROOT, "audit", "audit_BOOK3_summary.txt")

# ============================================================
# UTILITIES
# ============================================================

def _normalize_history(df: pd.DataFrame, digits_len: int) -> pd.DataFrame:
    df = df.copy()

    if "digits" not in df.columns:
        for c in df.columns:
            s = df[c].astype(str).str.replace(r"\D", "", regex=True)
            if s.str.len().eq(digits_len).any():
                df["digits"] = s.str.zfill(digits_len)
                break

    df["digits"] = df["digits"].astype(str).str.zfill(digits_len)
    df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce").dt.date
    return df


def load_history():
    if not os.path.exists(HISTORY_C3):
        raise FileNotFoundError(HISTORY_C3)
    if not os.path.exists(HISTORY_C4):
        raise FileNotFoundError(HISTORY_C4)

    df3 = _normalize_history(pd.read_csv(HISTORY_C3, dtype=str), 3)
    df4 = _normalize_history(pd.read_csv(HISTORY_C4, dtype=str), 4)
    return df3, df4


def miss_distance(a: str, b: str) -> int:
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b))


def score_hit(predicted: str, actual: str) -> str:
    if predicted == actual:
        return "STRAIGHT"
    if sorted(predicted) == sorted(actual):
        return "BOX"
    if miss_distance(predicted, actual) == 1:
        return "1-OFF"
    return "MISS"

# ============================================================
# SENTINEL AUDIT
# ============================================================

def run_audit():
    df3, df4 = load_history()
    audit_rows = []

    subscribers = [
        d for d in os.listdir(BOOK3_DIR)
        if d.startswith(BOOK3_PREFIX)
        and os.path.isdir(os.path.join(BOOK3_DIR, d))
    ]

    print(f"[SENTINEL] Found {len(subscribers)} BOOK3 kits.")

    if not subscribers:
        print("[SENTINEL] No BOOK3 kits found.")
        return

    for sub in subscribers:
        sub_dir = os.path.join(BOOK3_DIR, sub)
        forecast_file = os.path.join(sub_dir, "forecast.csv")

        if not os.path.exists(forecast_file):
            print(f"[WARN] Missing forecast.csv for {sub}")
            continue

        df = pd.read_csv(forecast_file, dtype=str)
        if df.empty:
            continue

        # ----------------------------------------------------
        # DATE RESOLUTION (ROBUST)
        # ----------------------------------------------------
        if "forecast_date" in df.columns:
            df["__date__"] = pd.to_datetime(
                df["forecast_date"], errors="coerce"
            ).dt.date
        else:
            m = re.search(
                r"BOOK3_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})",
                sub
            )
            if not m:
                print(f"[SENTINEL] Cannot infer dates for {sub}")
                continue

            start = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            end   = datetime.strptime(m.group(2), "%Y-%m-%d").date()

            dates = []
            cur = start
            while cur <= end:
                dates.append(cur)
                cur += pd.Timedelta(days=1)

            df["__date__"] = [dates[i % len(dates)] for i in range(len(df))]

        # ----------------------------------------------------
        # AUDIT ROWS
        # ----------------------------------------------------
        for _, row in df.iterrows():
            game = str(row.get("game_code", "")).upper()
            date = row.get("__date__")
            predicted = str(row.get("number", "")).strip()

            if not predicted or pd.isna(date):
                continue

            if game == "CASH3":
                hist = df3[df3["draw_date"] == date]
            elif game == "CASH4":
                hist = df4[df4["draw_date"] == date]
            else:
                con
