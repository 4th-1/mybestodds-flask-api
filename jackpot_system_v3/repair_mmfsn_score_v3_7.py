import os
import json
import pandas as pd
from datetime import datetime

print("[MMFSN REPAIR v3.7] Starting MMFSN repair...")

ROOT = os.getcwd()
KITS_ROOT = os.path.join(ROOT, "kits")
SUB_ROOT = os.path.join(ROOT, "data", "subscribers")

# ----------------------------
# Utilities
# ----------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_subscriber(sub_id, kit_type):
    path = os.path.join(SUB_ROOT, kit_type, f"{sub_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Subscriber file not found: {path}")
    return load_json(path)

def extract_mmfsn_digits(subscriber):
    """
    Extracts digit-level MMFSN signals from:
    - engine_profile.mmfsn (BOOK3 canonical)
    - legacy top-level mmfsn (backward compatibility)
    Returns a SET of digit strings.
    """
    digit_set = set()

    # --- Canonical BOOK3 structure ---
    mmfsn_profile = subscriber.get("engine_profile", {}).get("mmfsn", {})
    if isinstance(mmfsn_profile, dict):
        for game_cfg in mmfsn_profile.values():
            if isinstance(game_cfg, dict) and "values" in game_cfg:
                for combo in game_cfg["values"]:
                    for ch in str(combo):
                        if ch.isdigit():
                            digit_set.add(ch)

    # --- Legacy fallback ---
    legacy_digits = subscriber.get("mmfsn", [])
    for d in legacy_digits:
        if str(d).isdigit():
            digit_set.add(str(d))

    return digit_set

def compute_mmfsn_score(number_str, digit_set):
    if not number_str or not digit_set:
        return 0, 0.0

    digits = [c for c in str(number_str) if c.isdigit()]
    if not digits:
        return 0, 0.0

    hits = sum(1 for d in digits if d in digit_set)
    score = hits / len(digits)

    return (1 if hits > 0 else 0), round(score, 6)

# ----------------------------
# Main Processing
# ----------------------------
kits = [
    d for d in os.listdir(KITS_ROOT)
    if os.path.isdir(os.path.join(KITS_ROOT, d))
]

for kit in kits:
    kit_path = os.path.join(KITS_ROOT, kit)
    forecast_path = os.path.join(kit_path, "forecast.csv")

    if not os.path.exists(forecast_path):
        continue

    kit_type = kit.split("_")[0].upper()
    df = pd.read_csv(forecast_path, dtype=str).fillna("")

    # Ensure columns exist
    if "MMFSN_FLAG" not in df.columns:
        df["MMFSN_FLAG"] = "0"
    if "MMFSN_SCORE" not in df.columns:
        df["MMFSN_SCORE"] = "0"

    # Safe subscriber_id extraction
    if "SUBSCRIBER_ID" not in df.columns:
        print(f"⚠ {kit}: SUBSCRIBER_ID column missing — skipping")
        continue

    sub_id = df["SUBSCRIBER_ID"].dropna().iloc[0]

    # ----------------------------
    # BOOK / BOSK → defaults only
    # ----------------------------
    if kit_type in ("BOOK", "BOSK"):
        df["MMFSN_FLAG"] = "0"
        df["MMFSN_SCORE"] = "0"
        print(f"✔ {kit}: MMFSN defaults applied ({kit_type})")

    # ----------------------------
    # BOOK3 → compute MMFSN
    # ----------------------------
    else:
        subscriber = find_subscriber(sub_id, "BOOK3")
        digit_set = extract_mmfsn_digits(subscriber)

        flags = []
        scores = []

        for _, row in df.iterrows():
            f, s = compute_mmfsn_score(row.get("NUMBER"), digit_set)
            flags.append(str(f))
            scores.append(str(s))

        df["MMFSN_FLAG"] = flags
        df["MMFSN_SCORE"] = scores

        print(f"✔ {kit}: MMFSN computed for BOOK3 ({len(digit_set)} digits)")

    # ----------------------------
    # Backup + Save
    # ----------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = forecast_path + f".bak_mmfsn_{ts}"

    df.to_csv(backup, index=False)
    df.to_csv(forecast_path, index=False)

print("[MMFSN REPAIR v3.7] COMPLETE")
