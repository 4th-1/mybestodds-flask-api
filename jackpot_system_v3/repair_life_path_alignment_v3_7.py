#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_life_path_alignment_v3_7.py
--------------------------------------
Backfill LIFE_PATH_ALIGNMENT and PERSONAL_DAY_ALIGNMENT
for all v3.7 kits using DOB + DRAW_DATE.

Assumptions:
- All kits (BOOK3, BOOK, BOSK) have subscriber DOB in JSON.
- Each kit corresponds to a single SUBSCRIBER_ID.
- Subscriber JSON paths follow:
    data/subscribers/<KIT_TYPE>/<SUBSCRIBER_ID>.json

Where KIT_TYPE is one of: BOOK3, BOOK, BOSK.

Usage (run from project root):
    python repair_life_path_alignment_v3_7.py
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

KITS_ROOT = "kits"
SUBSCRIBERS_ROOT = os.path.join("data", "subscribers")
SUMMARY_FILE = "repair_life_path_alignment_summary_v3_7.json"


# ------------- Numerology Helpers ------------- #

def digit_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(int(n))))


def reduce_to_numerology_number(n: int) -> int:
    """
    Reduce to 1–9 (simple reduction).
    We keep it simple for now and do NOT preserve master numbers.
    """
    n = abs(int(n))
    while n > 9:
        n = digit_sum(n)
    return n


def life_path_from_dob(dob_str: str) -> int:
    """
    Compute basic Life Path number from DOB string (YYYY-MM-DD).
    """
    try:
        dt = datetime.strptime(dob_str, "%Y-%m-%d")
    except ValueError:
        # Try common alternate format, if needed
        try:
            dt = datetime.strptime(dob_str, "%m/%d/%Y")
        except ValueError:
            raise ValueError(f"Unrecognized DOB format: {dob_str}")

    total = dt.year + dt.month + dt.day
    return reduce_to_numerology_number(total)


def universal_day_from_date(draw_date_str: str) -> int:
    """
    Compute Universal Day number from DRAW_DATE string (YYYY-MM-DD).
    """
    try:
        dt = datetime.strptime(draw_date_str, "%Y-%m-%d")
    except ValueError:
        # If stored with time, like '2025-09-01 00:00:00'
        try:
            dt = datetime.fromisoformat(draw_date_str)
        except ValueError:
            raise ValueError(f"Unrecognized DRAW_DATE format: {draw_date_str}")

    total = dt.year + dt.month + dt.day
    return reduce_to_numerology_number(total)


def personal_day_number(life_path: int, universal_day: int) -> int:
    """
    Personal Day = Life Path + Universal Day, reduced.
    """
    return reduce_to_numerology_number(life_path + universal_day)


def personal_day_alignment_score(life_path: int, pd_num: int) -> int:
    """
    Simple 1–5 alignment band between Life Path and Personal Day.
    - Exact match: 5
    - Distance 1: 4
    - Distance 2: 3
    - Distance 3: 2
    - Else: 1
    """
    # Map into 1–9 space consistently
    def wrap9(x):
        x = ((x - 1) % 9) + 1
        return x

    lp = wrap9(life_path)
    pdn = wrap9(pd_num)

    diff = abs(lp - pdn)
    # Because 1 and 9 are "close" in numerology, take circular min distance
    diff = min(diff, 9 - diff)

    if diff == 0:
        return 5
    elif diff == 1:
        return 4
    elif diff == 2:
        return 3
    elif diff == 3:
        return 2
    else:
        return 1


# ------------- Core Logic ------------- #

def load_subscriber_dob(subscriber_id: str, kit_name: str) -> str:
    """
    Attempt to load DOB from subscriber JSON using kit prefix to infer kit type.
    Expected path:
        data/subscribers/<KIT_TYPE>/<SUBSCRIBER_ID>.json
    where KIT_TYPE is one of: BOOK3, BOOK, BOSK.
    """
    # Infer KIT_TYPE from kit_name (e.g., 'BOOK3_2025-09-01_to_2025-11-10')
    if kit_name.upper().startswith("BOOK3"):
        kit_type = "BOOK3"
    elif kit_name.upper().startswith("BOOK_") or kit_name.upper().startswith("BOOK"):
        kit_type = "BOOK"
    elif kit_name.upper().startswith("BOSK"):
        kit_type = "BOSK"
    else:
        raise FileNotFoundError(f"Cannot infer KIT_TYPE from kit name: {kit_name}")

    sub_dir = os.path.join(SUBSCRIBERS_ROOT, kit_type)
    sub_path = os.path.join(sub_dir, f"{subscriber_id}.json")

    if not os.path.isfile(sub_path):
        raise FileNotFoundError(f"Subscriber file not found: {sub_path}")

    with open(sub_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Try common DOB field names
    for key in ["dob", "date_of_birth", "birthdate", "birthday"]:
        if key in data and data[key]:
            return data[key]

    raise KeyError(
        f"No usable DOB field found in subscriber file: {sub_path} "
        f"(checked: dob, date_of_birth, birthdate, birthday)"
    )


def main() -> int:
    root = os.path.abspath(KITS_ROOT)
    if not os.path.isdir(root):
        print(f"[FATAL] Kits directory not found: {root}")
        return 1

    print("===============================================")
    print("  BEGINNING LIFE PATH & PERSONAL DAY REPAIR v3.7")
    print("===============================================")
    print(f"Kits root: {root}\n")

    summary = {
        "kits_root": root,
        "kits_processed": 0,
        "kits_skipped": 0,
        "details": {}
    }

    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        if entry.name.startswith("__"):
            # Skip __pycache__ or internal dirs
            continue

        kit_name = entry.name
        forecast_path = os.path.join(entry.path, "forecast.csv")

        if not os.path.isfile(forecast_path):
            print(f"[SKIP] No forecast.csv in {entry.path}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "SKIPPED",
                "reason": "forecast.csv missing",
            }
            continue

        print(f"[REPAIR] Processing kit: {kit_name}")

        try:
            df = pd.read_csv(forecast_path)
        except Exception as e:
            print(f"  ❌ Unable to read forecast.csv: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"read error: {e}",
            }
            continue

        # Ensure required columns exist
        if "LIFE_PATH_ALIGNMENT" not in df.columns:
            df["LIFE_PATH_ALIGNMENT"] = pd.NA
        if "PERSONAL_DAY_ALIGNMENT" not in df.columns:
            df["PERSONAL_DAY_ALIGNMENT"] = pd.NA

        if "DRAW_DATE" not in df.columns:
            print("  ❌ DRAW_DATE column missing; cannot compute numerology.")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": "DRAW_DATE column missing",
            }
            continue

        if "SUBSCRIBER_ID" not in df.columns:
            print("  ❌ SUBSCRIBER_ID column missing; cannot locate subscriber.")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": "SUBSCRIBER_ID column missing",
            }
            continue

        # Assume single subscriber per kit; take first non-null ID
        subs_ids = df["SUBSCRIBER_ID"].dropna().unique()
        if len(subs_ids) == 0:
            print("  ❌ No SUBSCRIBER_ID values found; cannot load DOB.")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": "No SUBSCRIBER_ID in forecast",
            }
            continue

        subscriber_id = str(subs_ids[0])

        # Load DOB from subscriber JSON
        try:
            dob_str = load_subscriber_dob(subscriber_id, kit_name)
        except Exception as e:
            print(f"  ❌ Failed to load DOB for subscriber {subscriber_id}: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"DOB load error: {e}",
            }
            continue

        # Compute Life Path number once per kit
        try:
            lp_number = life_path_from_dob(dob_str)
        except Exception as e:
            print(f"  ❌ Failed to compute Life Path from DOB '{dob_str}': {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"Life Path error: {e}",
            }
            continue

        repaired_rows = 0
        total_rows = len(df)

        for idx, draw_date_str in df["DRAW_DATE"].items():
            if pd.isna(draw_date_str) or str(draw_date_str).strip() == "":
                continue

            try:
                uday = universal_day_from_date(str(draw_date_str))
                pd_num = personal_day_number(lp_number, uday)
                pd_score = personal_day_alignment_score(lp_number, pd_num)
            except Exception as e:
                print(f"  [WARN] Row {idx}: numerology computation failed: {e}")
                continue

            # Life Path Alignment: for now, constant strong base (5)
            # (We can refine later with richer rules if desired.)
            df.at[idx, "LIFE_PATH_ALIGNMENT"] = 5
            df.at[idx, "PERSONAL_DAY_ALIGNMENT"] = pd_score
            repaired_rows += 1

        try:
            df.to_csv(forecast_path, index=False)
        except Exception as e:
            print(f"  ❌ Failed to write updated forecast.csv: {e}")
            summary["kits_skipped"] += 1
            summary["details"][kit_name] = {
                "status": "ERROR",
                "reason": f"write error: {e}",
            }
            continue

        print(
            f"  ✔ LIFE_PATH_ALIGNMENT & PERSONAL_DAY_ALIGNMENT repaired for {kit_name} "
            f"({repaired_rows}/{total_rows} rows updated)"
        )

        summary["kits_processed"] += 1
        summary["details"][kit_name] = {
            "status": "OK",
            "rows": int(total_rows),
            "rows_repaired": int(repaired_rows),
            "subscriber_id": subscriber_id,
            "dob": dob_str,
            "life_path": lp_number,
        }

    # Write summary JSON in project root
    out_path = os.path.join(os.path.abspath("."), SUMMARY_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n===============================================")
    print("  🎉 LIFE PATH & PERSONAL DAY REPAIR COMPLETE")
    print(f"  Summary written to: {SUMMARY_FILE}")
    print("===============================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
