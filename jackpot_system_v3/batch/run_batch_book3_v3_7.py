"""
run_batch_book3_v3_7.py
Batch runner for BOOK3 subscribers using the v3.7 unified engine.
"""

import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB_DIR  = os.path.join(BASE_DIR, "data", "subscribers", "BOOK3")
OUT_ROOT = os.path.join(BASE_DIR, "output")

ENGINE_SCRIPT = os.path.join(BASE_DIR, "core", "v3_7", "run_kit_v3_7.py")

os.makedirs(OUT_ROOT, exist_ok=True)

def run_batch(start_date, end_date):
    print(f"\n[BOOK3 BATCH v3.7] RUNNING BOOK3 FORECASTS {start_date} → {end_date}\n")

    subscribers = sorted([
        f for f in os.listdir(SUB_DIR)
        if f.endswith(".json")
    ])

    for sub_file in subscribers:
        sub_path = os.path.join(SUB_DIR, sub_file)
        sub_name = sub_file.replace(".json", "")

        out_dir = os.path.join(OUT_ROOT, sub_name)
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            "python",
            ENGINE_SCRIPT,
            "BOOK3",
            start_date,
            end_date,
            sub_path
        ]

        print(f"[BOOK3 BATCH v3.7] Processing: {sub_file}")
        print(f"[CMD] {' '.join(cmd)}")

        subprocess.run(cmd, cwd=BASE_DIR)

    print("\n[BOOK3 BATCH v3.7] COMPLETED.\n")


if __name__ == "__main__":
    run_batch("2025-09-01", "2025-11-10")
