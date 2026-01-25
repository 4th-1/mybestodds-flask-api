#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_kit_v3_7.py

My Best Odds Engine v3.7 – Execution Driver
-------------------------------------------

This script:
    - Loads subscriber JSON
    - Loads config_v3_7.json
    - Runs MyBestOddsEngineV37 across the date range
    - Writes forecast.json, forecast.csv, audit_preview.json
"""

from __future__ import annotations

import json
import csv
import os
import sys
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# PATH FIX – ensure project root + core/ are importable
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR  # jackpot_system_v3 folder

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CORE_DIR = os.path.join(PROJECT_ROOT, "core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

# ---------------------------------------------------------------------------
# FIXED ENGINE IMPORT (the correct file you actually have)
# ---------------------------------------------------------------------------
from core.engine_v3_7 import MyBestOddsEngineV37


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_folder(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def write_json(path: str, data: Any) -> None:
    ensure_folder(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    ensure_folder(os.path.dirname(path))

    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            pass
        return

    fieldnames = sorted({k for r in rows for k in r.keys()})

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in rows:
            writer.writerow({key: r.get(key, "") for key in fieldnames})


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 5:
        print("\nUsage:")
        print("  python run_kit_v3_7.py KITNAME START_DATE END_DATE SUBSCRIBER_JSON\n")
        sys.exit(1)

    KITNAME = sys.argv[1]
    START_DATE = sys.argv[2]
    END_DATE = sys.argv[3]
    SUB_PATH = sys.argv[4]

    # Resolve subscriber path
    subscriber_path = (
        SUB_PATH if os.path.isabs(SUB_PATH) else os.path.join(PROJECT_ROOT, SUB_PATH)
    )

    config_path = os.path.join(PROJECT_ROOT, "config", "config_v3_7.json")

    # Validate paths
    if not os.path.exists(config_path):
        print(f"[ERROR] Missing config file: {config_path}")
        sys.exit(1)

    if not os.path.exists(subscriber_path):
        print(f"[ERROR] Missing subscriber file: {subscriber_path}")
        sys.exit(1)

    # Load configuration
    config = load_json(config_path)
    subscriber = load_json(subscriber_path)

    # Create engine
    engine = MyBestOddsEngineV37(config)

    print(f"\n[RUNNING V3.7 ENGINE] {KITNAME}: {START_DATE} → {END_DATE}\n")

    # Generate forecast rows
    rows = engine.generate_forecast(START_DATE, END_DATE, subscriber)

    print(f"[INFO] Total rows generated: {len(rows)}")
    print("[INFO] Rows include Rubix + BOB + Confidence + Option-C.\n")

    # Output folder
    folder_name = f"{KITNAME}_{START_DATE}_to_{END_DATE}"
    out_dir = os.path.join(PROJECT_ROOT, "output", folder_name)
    ensure_folder(out_dir)

    # Output paths
    json_path = os.path.join(out_dir, "forecast.json")
    csv_path = os.path.join(out_dir, "forecast.csv")
    audit_preview_path = os.path.join(out_dir, "audit_preview.json")

    # Write files
    write_json(json_path, rows)
    write_csv(csv_path, rows)

    # SENTRY audit preview
    audit_preview = [
        {
            "game_code": r.get("game_code"),
            "forecast_date": r.get("forecast_date"),
            "draw_time": r.get("draw_time"),
            "number": r.get("number"),
            "confidence_score": r.get("confidence_score"),
            "win_odds_1_in": r.get("win_odds_1_in"),
            "play_flag": r.get("play_flag"),
            "primary_play_type": r.get("primary_play_type"),
            "legend_code": r.get("legend_code"),
            "option_c_pass": r.get("option_c_pass"),
            "sentry_ready": r.get("sentry_ready"),
        }
        for r in rows
    ]

    write_json(audit_preview_path, audit_preview)

    print("[SUCCESS] Forecast files saved:")
    print(f"         {json_path}")
    print(f"         {csv_path}")
    print(f"         {audit_preview_path}\n")
    print("[READY] Files are SENTRY-ready.\n")


if __name__ == "__main__":
    main()
