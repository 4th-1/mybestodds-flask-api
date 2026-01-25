"""
run_sentinel_bosk_v3_7.py
Sentinel Audit Engine for BOSK — My Best Odds v3.7
---------------------------------------------------
Evaluates:
- Straight hits
- Box hits
- One-Off hits
- Pattern alignment
- Miss distance (Δ)
- Confidence accuracy
- Play flags (PLAY/WATCH/HOLD/SKIP)
- Option-C correctness
- Legend accuracy
"""

import os
import json
import pandas as pd
from datetime import datetime

# ============================================================
# PATHS FOR BOSK v3.7 OUTPUT
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOSK_DIR = os.path.join(BASE_DIR, "outputs", "BOSK")
BOSK_PREFIX = "BOSK_"   # All BOSK subscribers begin with this

HISTORY_C3 = os.path.join(BASE_DIR, "data", "ga_results", "Sorted", "Cash3_History.csv")
HISTORY_C4 = os.path.join(BASE_DIR, "data", "ga_results", "Sorted", "Cash4_History.csv")

OUT_JSON = os.path.join(BASE_DIR, "audit", "audit_BOSK_v3_7.json")
OUT_CSV  = os.path.join(BASE_DIR, "audit", "audit_BOSK_v3_7.csv")
OUT_SUM  = os.path.join(BASE_DIR, "audit", "audit_BOSK_summary.txt")


# ============================================================
# Utility Functions
# ============================================================

def load_history():
    """Load Cash3 & Cash4 historical winning numbers."""
    df3 = pd.read_csv(HISTORY_C3, dtype=str)
    df4 = pd.read_csv(HISTORY_C4, dtype=str)

    df3["digits"] = df3["digits"].str.zfill(3)
    df4["digits"] = df4["digits"].str.zfill(4)

    df3["draw_date"] = pd.to_datetime(df3["draw_date"])
    df4["draw_date"] = pd.to_datetime(df4["draw_date"])

    return df3, df4


def miss_distance(a, b):
    """Digit-by-digit Δ distance."""
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b))


def score_hit(predicted, actual, game):
    """Returns hit classification for Cash3 or Cash4."""
    if predicted == actual:
        return "STRAIGHT"
    if sorted(predicted) == sorted(actual):
        return "BOX"
    if miss_distance(predicted, actual) == 1:
        return "1-OFF"
    return "MISS"


# ============================================================
# Sentinel Audit
# ============================================================

def run_audit():
    df3, df4 = load_history()
    audit_rows = []

    # ---------------------------------------------------------
    # Detect BOSK subscriber folders
    # ---------------------------------------------------------
    subscribers = [
        d for d in os.listdir(BOSK_DIR)
        if os.path.isdir(os.path.join(BOSK_DIR, d))
        and d.startswith(BOSK_PREFIX)
    ]

    print(f"[SENTINEL] Found {len(subscribers)} BOSK subscribers.")

    if len(subscribers) == 0:
        print("[SENTINEL] ERROR — No BOSK subscriber folders found.")
        print(f"Check path: {BOSK_DIR}")
        return

    # ---------------------------------------------------------
    # Process each subscriber
    # ---------------------------------------------------------
    for sub in subscribers:
        sub_dir = os.path.join(BOSK_DIR, sub)
        forecast_file = os.path.join(sub_dir, "forecast.csv")

        if not os.path.exists(forecast_file):
            print(f"[WARN] Missing forecast.csv for {sub}")
            continue

        df = pd.read_csv(forecast_file, dtype=str)

        if df.empty:
            print(f"[WARN] Empty forecast for {sub}")
            continue

        df["forecast_date"] = pd.to_datetime(df["forecast_date"])

        for _, row in df.iterrows():
            game = row.get("game_code", "")
            date = row["forecast_date"]
            predicted = row.get("number", "")

            # Match actual winning numbers
            if game == "CASH3":
                actual_row = df3[df3["draw_date"] == date]
                if actual_row.empty:
                    continue
                actual = actual_row["digits"].iloc[0]

            elif game == "CASH4":
                actual_row = df4[df4["draw_date"] == date]
                if actual_row.empty:
                    continue
                actual = actual_row["digits"].iloc[0]

            else:
                continue  # Skip jackpots

            hit = score_hit(predicted, actual, game)

            audit_rows.append({
                "subscriber": sub,
                "game": game,
                "date": date.strftime("%Y-%m-%d"),
                "predicted": predicted,
                "actual": actual,
                "hit_type": hit,
                "confidence": row.get("confidence_score", ""),
                "play_flag": row.get("play_flag", ""),
                "legend": row.get("legend_code", ""),
                "delta": miss_distance(predicted, actual),
            })

    # ---------------------------------------------------------
    # Save Results (JSON + CSV)
    # ---------------------------------------------------------
    df_out = pd.DataFrame(audit_rows)

    with open(OUT_JSON, "w") as f:
        json.dump(audit_rows, f, indent=4)

    df_out.to_csv(OUT_CSV, index=False)

    # ---------------------------------------------------------
    # Summary — Safe Handling
    # ---------------------------------------------------------
    if df_out.empty:
        print("[SENTINEL] No BOSK audit rows produced. Nothing to summarize.")
        return

    summary = df_out.groupby("hit_type").size().to_string()

    with open(OUT_SUM, "w") as f:
        f.write("BOSK SENTINEL v3.7 Audit Summary\n")
        f.write("---------------------------------\n")
        f.write(summary)

    print("\n[SENTINEL] BOSK Audit Complete.")
    print(f"[SENTINEL] JSON: {OUT_JSON}")
    print(f"[SENTINEL] CSV:  {OUT_CSV}")
    print(f"[SENTINEL] SUM:  {OUT_SUM}")


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    run_audit()
