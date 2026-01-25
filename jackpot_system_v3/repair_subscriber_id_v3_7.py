#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
repair_subscriber_id_v3_7.py
--------------------------------------
Populate SUBSCRIBER_ID into forecast.csv
for all v3.7 kits (BOOK3 / BOOK / BOSK).
"""

import os
import sys
import json
import pandas as pd

KITS_ROOT = "kits"
SUBSCRIBER_ROOT = "data/subscribers"

KIT_TO_SUBSCRIBER = {
    "BOOK3": "JDS_BOOK3",
    "BOOK":  "JDS_BOOK",
    "BOSK":  "JDS_BOSK",
}

def infer_kit_type(folder_name: str) -> str | None:
    for k in KIT_TO_SUBSCRIBER:
        if folder_name.startswith(k):
            return k
    return None

def main():
    print("===============================================")
    print("  BEGINNING SUBSCRIBER_ID REPAIR v3.7")
    print("===============================================")

    for entry in os.scandir(KITS_ROOT):
        if not entry.is_dir() or entry.name.startswith("__"):
            continue

        kit_type = infer_kit_type(entry.name)
        if not kit_type:
            print(f"[SKIP] Unknown kit type: {entry.name}")
            continue

        subscriber_id = KIT_TO_SUBSCRIBER[kit_type]
        forecast_path = os.path.join(entry.path, "forecast.csv")

        if not os.path.isfile(forecast_path):
            print(f"[SKIP] No forecast.csv in {entry.name}")
            continue

        print(f"[REPAIR] {entry.name} → SUBSCRIBER_ID={subscriber_id}")

        df = pd.read_csv(forecast_path)

        if "SUBSCRIBER_ID" not in df.columns:
            df["SUBSCRIBER_ID"] = subscriber_id
        else:
            df["SUBSCRIBER_ID"] = subscriber_id

        df.to_csv(forecast_path, index=False)
        print(f"  ✔ Injected SUBSCRIBER_ID into {len(df)} rows")

    print("\n🎉 SUBSCRIBER_ID REPAIR COMPLETE\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
