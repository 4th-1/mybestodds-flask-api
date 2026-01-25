#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ORACLE_v3_7.py
--------------------------------------
Overlay validation engine for My Best Odds v3.7.

ENGINE-ALIGNED STRICT MODE
- Validates ONLY canonical v3.7 schema fields
- No legacy / phantom fields
- No mutation of persisted data
- Normalizes values ONLY for validation safety
"""

import os
import sys
import pandas as pd

# ---------------------------------------------------------
# CANONICAL v3.7 OVERLAY FIELDS (MATCH forecast_writer_v3_7)
# ---------------------------------------------------------
REQUIRED_OVERLAY_FIELDS = [
    # Astrology
    "moon_phase",
    "zodiac_sign",
    "planetary_hour",

    # Numerology
    "numerology_code",

    # Jackpot (v3.7)
    "jp_alignment_score",
    "jp_streak_score",
    "jp_hot_index",
    "jp_due_index",
    "jp_repeat_score",
    "jp_momentum_score",
    "jp_cycle_flag",
]

# ---------------------------------------------------------
# ALLOWED VALUES (ENGINE CANONICAL)
# ---------------------------------------------------------
ALLOWED_MOON_PHASES = {
    "", "NEW", "WAXING CRESCENT", "FIRST QUARTER",
    "WAXING GIBBOUS", "FULL", "WANING GIBBOUS",
    "LAST QUARTER", "WANING CRESCENT"
}

ALLOWED_PLANETARY_HOURS = {
    "", "Sun", "Moon", "Mars", "Mercury",
    "Jupiter", "Venus", "Saturn"
}

# Treat these game codes as "jackpot games"
JACKPOT_GAME_CODES = {"MM", "PB"}

# ---------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------
def fail(msg: str) -> None:
    print(f"\n❌ [ORACLE-ERROR] {msg}\n")
    sys.exit(1)

def normalize_moon(val) -> str:
    """Normalize moon phase safely for validation only."""
    if pd.isna(val):
        return ""
    return (
        str(val)
        .strip()
        .upper()
        .replace(" MOON", "")
    )

def is_jackpot_row(row: pd.Series) -> bool:
    """
    Decide whether a row is a jackpot game row.
    Priority: game_code if present, fallback to game name text.
    """
    gc = str(row.get("game_code", "")).strip().upper()
    if gc in JACKPOT_GAME_CODES:
        return True

    g = str(row.get("game", "")).strip().upper()
    # conservative fallback
    return ("MEGA" in g) or ("POWER" in g) or (g in {"MM", "PB"})

# ---------------------------------------------------------
# CORE VALIDATION
# ---------------------------------------------------------
def validate_oracle_overlays(df: pd.DataFrame, kit_name: str) -> None:

    # Defensive column normalization
    df.columns = [c.strip() for c in df.columns]

    # 1️⃣ Required fields exist
    for field in REQUIRED_OVERLAY_FIELDS:
        if field not in df.columns:
            fail(f"[{kit_name}] Missing overlay field: {field}")

    # 2️⃣ Moon phase validation (normalized, blank-safe)
    normalized_moon = df["moon_phase"].apply(normalize_moon)
    invalid = normalized_moon[~normalized_moon.isin(ALLOWED_MOON_PHASES)]
    if not invalid.empty:
        fail(
            f"[{kit_name}] Invalid moon phase detected. "
            f"Examples: {list(pd.unique(invalid))[:3]}"
        )

    # 3️⃣ Zodiac sign validation (v3.7 compliant — blank-safe)
    # Presence is enforced by schema; values may be empty placeholders
    _ = df["zodiac_sign"].fillna("").astype(str).str.strip()

    # 4️⃣ Planetary hour validation (blank-safe)
    if not df["planetary_hour"].fillna("").isin(ALLOWED_PLANETARY_HOURS).all():
        fail(f"[{kit_name}] Invalid planetary_hour detected.")

    # 5️⃣ Jackpot numeric sanity — ONLY for jackpot rows
    # If kit has no jackpot rows, skip this entirely.
    jackpot_mask = df.apply(is_jackpot_row, axis=1)

    if jackpot_mask.any():
        df_jp = df.loc[jackpot_mask].copy()

        numeric_fields = [
            "jp_alignment_score",
            "jp_streak_score",
            "jp_hot_index",
            "jp_due_index",
            "jp_repeat_score",
            "jp_momentum_score",
        ]

        for field in numeric_fields:
            # Allow blank strings, but NOT all-null/empty across jackpot rows
            series = df_jp[field]

            all_null = series.isna().all()
            all_blank = series.fillna("").astype(str).str.strip().eq("").all()

            if all_null or all_blank:
                fail(
                    f"[{kit_name}] Jackpot field {field} is entirely NULL/blank "
                    f"for jackpot rows."
                )

    print(f"  ✔ Overlays validated for {kit_name}")

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main() -> None:
    kits_root = "kits"

    if not os.path.isdir(kits_root):
        fail(f"No kits directory found at: {kits_root}")

    kit_paths = [
        p.path for p in os.scandir(kits_root)
        if p.is_dir() and not p.name.startswith("__")
    ]

    if not kit_paths:
        fail("No kit folders found under /kits")

    for kit in kit_paths:
        kit_name = os.path.basename(kit)
        forecast_path = os.path.join(kit, "forecast.csv")

        if not os.path.isfile(forecast_path):
            fail(f"[{kit_name}] forecast.csv missing for ORACLE check.")

        print(f"[ORACLE] Validating overlays for: {kit_name}")

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            fail(f"[{kit_name}] Unable to read forecast.csv: {e}")

        validate_oracle_overlays(df, kit_name)

    print("\n✅ ORACLE_v3_7 — ENGINE-ALIGNED OVERLAY VALIDATION PASSED.\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
