#!/usr/bin/env python
# ==============================================================================
# SCRIBE PRODUCTION VALIDATOR v3.7
# ==============================================================================
# Final production gatekeeper.
# Single source of truth = core.forecast_writer_v3_7.V37_COLUMNS
# ==============================================================================

import os
import sys
import glob
import pandas as pd
from collections import Counter

# ------------------------------------------------------------------------------
# Ensure project root is on PYTHONPATH
# ------------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ------------------------------------------------------------------------------
# Import schema contract (SINGLE SOURCE OF TRUTH)
# ------------------------------------------------------------------------------
try:
    from core.forecast_writer_v3_7 import V37_COLUMNS
except ImportError as e:
    print("❌ [SCRIBE-CRITICAL] Cannot import V37_COLUMNS from core.forecast_writer_v3_7")
    print(f"   Reason: {e}")
    sys.exit(1)

EXPECTED_COLUMNS = [c.strip() for c in V37_COLUMNS]  # defensive copy
EXPECTED_SET = set(EXPECTED_COLUMNS)
EXPECTED_COUNT = len(EXPECTED_COLUMNS)

print("=" * 60)
print(" RUNNING: SCRIBE_PRODUCTION_v3_7 (Final Schema Validation)")
print("=" * 60)
print(f"[SCRIBE] Expecting exactly {EXPECTED_COUNT} columns")
print("-" * 60)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def fail(msg):
    print(f"\n❌ [SCRIBE-ERROR] {msg}")
    print("   Pipeline halted due to schema violation.")
    sys.exit(1)


def validate(df, kit_name, path):
    # Normalize column names (BOM / whitespace protection)
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    found_cols = list(df.columns)
    found_set = set(found_cols)

    # 1️⃣ Duplicate detection
    dupes = [c for c, n in Counter(found_cols).items() if n > 1]
    if dupes:
        fail(f"[{kit_name}] DUPLICATE COLUMNS DETECTED: {dupes}")

    # 2️⃣ Missing / Extra detection (before count)
    missing = sorted(EXPECTED_SET - found_set)
    extra = sorted(found_set - EXPECTED_SET)

    if missing or extra:
        msg = f"[{kit_name}] SCHEMA SET MISMATCH\n"
        if missing:
            msg += f"   Missing columns ({len(missing)}): {missing}\n"
        if extra:
            msg += f"   Extra columns ({len(extra)}): {extra}\n"
        fail(msg.rstrip())

    # 3️⃣ Count check
    if len(found_cols) != EXPECTED_COUNT:
        fail(
            f"[{kit_name}] COLUMN COUNT MISMATCH\n"
            f"   Found: {len(found_cols)}\n"
            f"   Expected: {EXPECTED_COUNT}"
        )

    # 4️⃣ Order check
    for i, expected_col in enumerate(EXPECTED_COLUMNS):
        if found_cols[i] != expected_col:
            fail(
                f"[{kit_name}] COLUMN ORDER MISMATCH @ position {i}\n"
                f"   Found: '{found_cols[i]}'\n"
                f"   Expected: '{expected_col}'"
            )


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    forecast_files = glob.glob(os.path.join("kits", "*", "forecast.csv"))

    if not forecast_files:
        print("[SCRIBE] No forecast.csv files found.")
        return 0

    print(f"[SCRIBE] Validating {len(forecast_files)} kit(s)\n")

    for path in forecast_files:
        kit_name = os.path.basename(os.path.dirname(path))
        print(f"[SCRIBE] Validating: {kit_name}")

        try:
            df = pd.read_csv(path)
        except Exception as e:
            fail(f"[{kit_name}] Unable to read forecast.csv: {e}")

        validate(df, kit_name, path)
        print(f"  ✅ {kit_name} OK ({EXPECTED_COUNT} columns)\n")

    print("=" * 60)
    print(" ✅ SCRIBE_PRODUCTION_v3_7 PASSED — ALL SCHEMAS VALID")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
