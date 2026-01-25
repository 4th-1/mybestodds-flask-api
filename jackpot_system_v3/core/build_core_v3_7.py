#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
build_core_v3_7.py
------------------
Builds core.csv for each kit.
This is the REQUIRED upstream step before row_builder_v3_7.
"""

import os
import csv
from datetime import date

KITS_ROOT = "kits"


def build_core_for_kit(kit_path: str):
    kit_name = os.path.basename(kit_path)
    core_csv = os.path.join(kit_path, "core.csv")

    # 🔹 TEMPORARY / DEFAULT CORE ROWS
    # (Replace later with real generator logic)
    rows = [
        {
            "kit_name": kit_name,
            "game": "Cash3",
            "draw_date": "2025-12-03",
            "draw_time": "Evening",
            "number": "406",
        }
    ]

    with open(core_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["kit_name", "game", "draw_date", "draw_time", "number"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[CORE_BUILDER] Built core.csv for {kit_name}")


def main():
    if not os.path.isdir(KITS_ROOT):
        print("[CORE_BUILDER] No kits directory found.")
        return 1

    kits = [
        p.path for p in os.scandir(KITS_ROOT)
        if p.is_dir() and not p.name.startswith("__")
    ]

    for kit in kits:
        build_core_for_kit(kit)

    print("\n✅ CORE BUILDER COMPLETE.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
