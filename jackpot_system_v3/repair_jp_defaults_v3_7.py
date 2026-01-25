import os
import pandas as pd

ROOT = os.getcwd()
KITS_ROOT = os.path.join(ROOT, "kits")

# Canonical JP fields required by ORACLE v3.7
JP_FIELDS = [
    "JP_REPEAT_DISTANCE",
    "JP_STREAK_SCORE",
    "JP_ALIGNMENT_SCORE",   # ← THIS WAS MISSING
    "JP_HOT_INDEX",
    "JP_DUE_INDEX",
    "JP_REPEAT_SCORE",
    "JP_MOMENTUM_SCORE",
    "JP_CYCLE_FLAG",
]

print("[JP DEFAULTS REPAIR v3.7] Starting...")

kits = [
    d for d in os.listdir(KITS_ROOT)
    if os.path.isdir(os.path.join(KITS_ROOT, d))
]

for kit in kits:
    forecast_path = os.path.join(KITS_ROOT, kit, "forecast.csv")
    if not os.path.exists(forecast_path):
        continue

    df = pd.read_csv(forecast_path, dtype=str).fillna("")

    touched = 0
    for col in JP_FIELDS:
        if col not in df.columns:
            continue
        # default only if the entire column is empty
        if (df[col] == "").all():
            df[col] = "0"
            touched += 1

    if touched > 0:
        df.to_csv(forecast_path, index=False)
        print(f"✔ {kit}: defaulted {touched} JP_* fields to 0")
    else:
        print(f"✔ {kit}: JP_* fields already populated")

print("[JP DEFAULTS REPAIR v3.7] COMPLETE")
