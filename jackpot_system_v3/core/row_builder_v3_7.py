#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
row_builder_v3_7.py
-------------------
Builds FULLY ENRICHED v3.7 forecast rows.

Integrates:
✔ Rubik Engine
✔ BOB Engine
✔ Confidence Engine
✔ MBO '1-in-X' Odds
✔ Invalid-number protection

Mandatory v3.7 identity:
✔ forecast_date
✔ game_code
"""

# -------------------------------------------------------------
# Imports
# -------------------------------------------------------------
import sys
import os
import csv
from pprint import pprint

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.forecast_writer_v3_7 import (
    V37_COLUMNS,
    make_placeholder_row,
    write_forecast_v37,
)
from core.row_enricher_v3_7 import enrich_row_v3_7


# -------------------------------------------------------------
# GAME CODE MAP (required v3.7)
# -------------------------------------------------------------
GAME_CODE_MAP = {
    "cash3": "C3",
    "cash 3": "C3",
    "cash4": "C4",
    "cash 4": "C4",
    "mega millions": "MM",
    "megamillions": "MM",
    "powerball": "PB",
    "cash4life": "C4L",
    "cash 4 life": "C4L",
}


def resolve_game_code(game_name: str) -> str:
    if not game_name:
        return "GEN"
    key = str(game_name).strip().lower()
    return GAME_CODE_MAP.get(key, "GEN")


# -------------------------------------------------------------
# CORE BUILDER
# -------------------------------------------------------------
def build_v37_rows(core_rows: list) -> list:
    """
    Accepts core engine rows:
        {
            "kit_name": ...,
            "game": ...,
            "draw_date": ...,
            "draw_time": ...,
            "number": ...
        }

    Returns FULLY enriched v3.7 forecast rows.
    """
    v37_rows = []

    for core in core_rows:
        # 1. Base placeholder (schema-complete)
        base_row = make_placeholder_row({
            "kit_name": core.get("kit_name", ""),
            "game": core.get("game", ""),
            "draw_date": core.get("draw_date", ""),
            "draw_time": core.get("draw_time", ""),
            "number": core.get("number", ""),
        })

        # 2. REQUIRED v3.7 identity fields
        base_row["forecast_date"] = core.get("draw_date", "")
        base_row["game_code"] = resolve_game_code(core.get("game", ""))

        # 3. Enrich
        enriched = enrich_row_v3_7(base_row)
        v37_rows.append(enriched)

    return v37_rows


# -------------------------------------------------------------
# PIPELINE ENTRY POINT
# -------------------------------------------------------------
def main():
    kits_root = "kits"
    if not os.path.isdir(kits_root):
        print("[ROW_BUILDER] No kits directory found.")
        return 1

    kit_dirs = [
        p.path for p in os.scandir(kits_root)
        if p.is_dir() and not p.name.startswith("__")
    ]

    if not kit_dirs:
        print("[ROW_BUILDER] No kit folders found under /kits.")
        return 1

    for kit_path in kit_dirs:
        kit_name = os.path.basename(kit_path)
        print(f"[ROW_BUILDER] Building forecast.csv for {kit_name}")

        # -------------------------------------------------
        # LOAD core.csv DIRECTLY (NO core_loader dependency)
        # -------------------------------------------------
        core_csv = os.path.join(kit_path, "core.csv")
        if not os.path.isfile(core_csv):
            print(f"[ROW_BUILDER] Skipping {kit_name} (no core.csv found)")
            continue

        with open(core_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            core_rows = list(reader)

        if not core_rows:
            print(f"[ROW_BUILDER] Skipping {kit_name} (core.csv empty)")
            continue

        v37_rows = build_v37_rows(core_rows)

        out_path = os.path.join(kit_path, "forecast.csv")
        write_forecast_v37(v37_rows, out_path)

    print("\n✅ ROW_BUILDER_v3_7 COMPLETE.\n")
    return 0


# -------------------------------------------------------------
# SAMPLE MODE (SAFE)
# -------------------------------------------------------------
def run_sample():
    test = [{
        "kit_name": "BOOK3_SAMPLE",
        "game": "Cash3",
        "draw_date": "2025-12-03",
        "draw_time": "Evening",
        "number": "406",
    }]
    rows = build_v37_rows(test)
    print("Sample Enriched Row:")
    pprint(rows[0])


if __name__ == "__main__":
    if "--sample" in sys.argv:
        sys.exit(run_sample() or 0)
    sys.exit(main())
