# ==============================================================================
# SCRIBE PRODUCTION VALIDATOR v3.7
# ==============================================================================
# Purpose: Final gatekeeper for production data integrity.
# Ensures forecast CSVs match the exact schema contract defined by the writer.
# ==============================================================================

import pandas as pd
import sys
import os
import glob

# ==============================================================================
# ✅ SINGLE SOURCE OF TRUTH (HARDENED)
# ==============================================================================
try:
    from core.forecast_writer_v3_7 import V37_COLUMNS
except ImportError:
    print("❌ [SCRIBE-CRITICAL] Could not import V37_COLUMNS from core.forecast_writer_v3_7.")
    print("   Ensure the 'core' module is in your Python path.")
    sys.exit(1)

# 🔒 HARDENING CHECK (OPTIONAL BUT RECOMMENDED)
if not isinstance(V37_COLUMNS, list) or len(V37_COLUMNS) == 0:
    print("❌ [SCRIBE-CRITICAL] V37_COLUMNS is empty or invalid.")
    print("   Schema contract is broken. Pipeline halted.")
    sys.exit(1)

# ==============================================================================
# SCHEMA DEFINITION (DYNAMIC)
# ==============================================================================
EXPECTED_COLUMNS = V37_COLUMNS
EXPECTED_COLUMN_COUNT = len(V37_COLUMNS)

print("=" * 60)
print(" RUNNING: SCRIBE_PRODUCTION_v3_7 (Final Schema Validation)")
print("=" * 60)
print(
    f"[SCRIBE] 🔥 Schema loaded from forecast_writer_v3_7."
    f" Expecting exactly {EXPECTED_COLUMN_COUNT} columns."
)
print("-" * 60)

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================
def fail(msg):
    print(f"\n❌ [SCRIBE-ERROR] {msg}")
    print("   Pipeline halted due to schema violation.")
    sys.exit(1)

def success(msg):
    print(f"✅ [SCRIBE] {msg}")

# ==============================================================================
# CORE VALIDATION LOGIC
# ==============================================================================
def validate_schema(df, kit_name, filename):
    # 1. Column count
    current_count = len(df.columns)
    if current_count != EXPECTED_COLUMN_COUNT:
        fail(
            f"[{kit_name}] COLUMN COUNT MISMATCH in {os.path.basename(filename)}:\n"
            f"   Found: {current_count}\n"
            f"   Expected: {EXPECTED_COLUMN_COUNT}"
        )

    # 2. Column order + names
    for ix, expected_col in enumerate(EXPECTED_COLUMNS):
        if ix >= current_count:
            fail(
                f"[{kit_name}] MISSING COLUMN at position {ix}: "
                f"expected '{expected_col}'"
            )

        found_col = df.columns[ix]
        if found_col != expected_col:
            fail(
                f"[{kit_name}] COLUMN ORDER / NAME MISMATCH at position {ix}:\n"
                f"   Found: '{found_col}'\n"
                f"   Expected: '{expected_col}'"
            )

    return True

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def run_scribe_validation(kits_dir="kits"):
    search_pattern = os.path.join(kits_dir, "*", "forecast.csv")
    forecast_files = glob.glob(search_pattern)

    if not forecast_files:
        print(f"[SCRIBE-WARNING] No forecast.csv files found under {kits_dir}.")
        return

    print(f"[SCRIBE] Found {len(forecast_files)} forecast file(s) to validate.")

    validated = 0
    for filepath in forecast_files:
        kit_name = os.path.basename(os.path.dirname(filepath))
        print(f"[SCRIBE] Validating schema for: {kit_name}")

        try:
            df = pd.read_csv(filepath)
            validate_schema(df, kit_name, filepath)
            success(f"{kit_name} schema verified ({EXPECTED_COLUMN_COUNT} columns).")
            validated += 1

        except pd.errors.EmptyDataError:
            fail(f"[{kit_name}] forecast.csv is empty.")
        except Exception as e:
            fail(f"[{kit_name}] Unexpected error reading file: {e}")

    print("-" * 60)
    print(f"✅ SCRIBE_PRODUCTION_v3_7 PASSED for {validated} kit(s).")
    print("=" * 60)

# ==============================================================================
# ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    run_scribe_validation()
