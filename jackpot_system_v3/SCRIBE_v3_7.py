#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SCRIBE_PRODUCTION_v3_7.py  (ENGINE-ALIGNED STRICT MODE)
-----------------------------------------------------
Validates forecast.csv against the REAL v3.7 engine schema.

RULES:
- Column COUNT must match EXACTLY
- Column ORDER must match EXACTLY
- No missing primary fields
- HALTS pipeline on failure
"""

import os
import sys
import pandas as pd

# ------------------------------------------------------------------------------
# 🔒 PIPELINE-SAFE PATH HARDENING (CRITICAL FIX)
# ------------------------------------------------------------------------------
THIS_FILE = os.path.abspath(__file__)
AUDIT_DIR = os.path.dirname(THIS_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(AUDIT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------------------------
# SINGLE SOURCE OF TRUTH (ENGINE CONTRACT)
# ------------------------------------------------------------------------------
try:
    from core.forecast_writer_v3_7 import V37_COLUMNS
except Exception as e:
    print("❌ [SCRIBE-CRITICAL] Failed to import V37_COLUMNS")
    print(f"   Project root resolved as: {PROJECT_ROOT}")
    print(f"   sys.path = {sys.path}")
    print(f"   Error: {e}")
    sys.exit(1)

REQUIRED_COUNT = len(V37_COLUMNS)


def fail(msg):
    print(f"\n❌ [SCRIBE-ERROR] {msg}\n")
    sys.exit(1)


def validate_forecast_schema(df, kit_name):
    # 1️⃣ Column count
    if len(df.columns) != REQUIRED_COUNT:
        fail(
            f"[{kit_name}] COLUMN COUNT MISMATCH: "
            f"Found {len(df.columns)}, expected {REQUIRED_COUNT}"
        )

    # 2️⃣ Column order + names
    for i, col in enumerate(V37_COLUMNS):
        if df.columns[i] != col:
            fail(
                f"[{kit_name}] COLUMN ORDER MISMATCH at position {i}: "
                f"Found '{df.columns[i]}', expected '{col}'"
            )

    # 3️⃣ Required field values
    for required in ("game", "draw_date", "number"):
        if required not in df.columns:
            fail(f"[{kit_name}] REQUIRED COLUMN MISSING: {required}")

        if df[required].isna().any() or (df[required] == "").any():
            fail(
                f"[{kit_name}] NULL/EMPTY values found in required column: {required}"
            )

    print(f"  ✔ Schema validated for {kit_name}")


def main():
    kits_root = "kits"
    if not os.path.isdir(kits_root):
        fail("No kits directory found.")

    kit_paths = [
        p.path for p in os.scandir(kits_root)
        if p.is_dir() and not p.name.startswith("__")
    ]

    if not kit_paths:
        fail("No kit folders found.")

    for kit in kit_paths:
        kit_name = os.path.basename(kit)
        forecast_path = os.path.join(kit, "forecast.csv")

        if not os.path.isfile(forecast_path):
            fail(f"[{kit_name}] forecast.csv not found.")

        print(f"[SCRIBE] Validating schema for: {kit_name}")

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            fail(f"[{kit_name}] Unable to read forecast.csv: {e}")

        validate_forecast_schema(df, kit_name)

    print("\n✅ SCRIBE_PRODUCTION_v3_7 — ENGINE-ALIGNED SCHEMA VALID.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
