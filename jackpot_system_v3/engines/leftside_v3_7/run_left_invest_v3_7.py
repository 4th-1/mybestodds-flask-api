"""
run_left_ingest_v3_7.py

Purpose:
    Test the v3.7 LEFT ENGINE ingest pipeline
    and confirm Cash3/Cash4 history loads correctly.

This validates:
    - CSV paths
    - v3.7 left_ingest_v3_7.py
    - v3.7 daily_index_v3_7.py
    - DataFrame integrity

Usage:
    python scripts/run_left_ingest_v3_7.py
"""

import os
import sys
import pprint

# -------------------------------------------------------------------
# Ensure project root is on sys.path
# -------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -------------------------------------------------------------------
# Import the v3.7 left ingest module
# -------------------------------------------------------------------
from engines.leftside_v3_7.left_ingest_v3_7 import build_left_feature_context


# -------------------------------------------------------------------
# MAIN EXECUTION
# -------------------------------------------------------------------
def main():
    print("\n========================================================")
    print("🧪 LEFT ENGINE INGEST TEST — v3.7")
    print("========================================================")

    # -------------------------------------------------------------------
    # SHARED HISTORY LOCATION
    # -------------------------------------------------------------------
    shared_root = os.path.abspath(
        os.path.join(PROJECT_ROOT, "..", "shared_history", "ga_results")
    )

    cash3_csv = os.path.join(shared_root, "cash3_history.csv")
    cash4_csv = os.path.join(shared_root, "cash4_history.csv")

    print("\n📂 Checking for required CSV files:")
    print("  •", cash3_csv)
    print("  •", cash4_csv)

    if not os.path.exists(cash3_csv):
        print("\n❌ Missing file:", cash3_csv)
        print("Create or copy this file before running again.")
        return

    if not os.path.exists(cash4_csv):
        print("\n❌ Missing file:", cash4_csv)
        print("Create or copy this file before running again.")
        return

    # -------------------------------------------------------------------
    # LOAD LEFT ENGINE CONTEXT
    # -------------------------------------------------------------------
    print("\nLoading history dataframes...")
    left_ctx = build_left_feature_context(cash3_csv, cash4_csv)

    print("\n========================================================")
    print("LEFT ENGINE INGEST RESULTS")
    print("========================================================")

    for key, df in left_ctx.items():
        print(f"\n📌 {key}: {len(df)} rows loaded")
        print(df.head())

    print("\n✅ LEFT ENGINE INGEST COMPLETED SUCCESSFULLY\n")


if __name__ == "__main__":
    main()
