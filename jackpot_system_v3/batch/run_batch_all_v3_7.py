"""
run_batch_all_v3_7.py
Master batch runner for BOOK3, BOOK, and BOSK using the unified v3.7 engine.

This script:
• Finds all .json subscriber files in each kit folder
• Calls run_kit_v3_7.py for each subscriber
• Writes outputs into /output/<subscriber_name>
• Produces clean console logs for easy monitoring
"""

import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_SCRIPT = os.path.join(BASE_DIR, "core", "v3_7", "run_kit_v3_7.py")

SUB_FOLDERS = {
    "BOOK3": os.path.join(BASE_DIR, "data", "subscribers", "BOOK3"),
    "BOOK":  os.path.join(BASE_DIR, "data", "subscribers", "BOOK"),
    "BOSK":  os.path.join(BASE_DIR, "data", "subscribers", "BOSK"),
}

OUTPUT_ROOT = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_ROOT, exist_ok=True)


def run_kit_batch(kit_name, sub_dir, start_date, end_date):
    print(f"\n==============================")
    print(f"  RUNNING {kit_name} BATCH v3.7")
    print(f"  {start_date} → {end_date}")
    print(f"==============================\n")

    subscribers = sorted([f for f in os.listdir(sub_dir) if f.endswith(".json")])

    if not subscribers:
        print(f"[WARNING] No subscriber files found in {sub_dir}")
        return

    for sub_file in subscribers:
        sub_path = os.path.join(sub_dir, sub_file)
        sub_name = sub_file.replace(".json", "")

        print(f"[BATCH] {kit_name}: Processing {sub_file}")

        cmd = [
            "python",
            ENGINE_SCRIPT,
            kit_name,
            start_date,
            end_date,
            sub_path
        ]

        print(f"[CMD] {' '.join(cmd)}")
        subprocess.run(cmd, cwd=BASE_DIR)

    print(f"\n[{kit_name} BATCH v3.7] Completed.\n")


def run_all(start_date, end_date):
    for kit, folder in SUB_FOLDERS.items():
        run_kit_batch(kit, folder, start_date, end_date)

    print("\n==============================")
    print(" ALL KITS COMPLETE — v3.7 BATCH ")
    print("==============================\n")


if __name__ == "__main__":
    # Default range — you can modify before running
    run_all("2025-09-01", "2025-11-10")
