"""
run_batch_bosk_v3_7.py
Batch runner for BOSK subscribers using the v3.7 unified engine.
"""

import os
import subprocess
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_SCRIPT = os.path.join(BASE_DIR, "core", "v3_7", "run_kit_v3_7.py")

def run_batch(start_date, end_date, kit_name="BOSK", single_subscriber=None):
    print(f"\n[BOSK BATCH v3.7] RUNNING {kit_name} FORECASTS {start_date} → {end_date}\n")

    sub_dir = os.path.join(BASE_DIR, "data", "subscribers", kit_name)
    out_root = os.path.join(BASE_DIR, "outputs")

    if not os.path.exists(sub_dir):
        raise FileNotFoundError(f"Subscriber folder not found: {sub_dir}")

    os.makedirs(out_root, exist_ok=True)

    subscriber_files = [
        f for f in os.listdir(sub_dir)
        if f.endswith(".json")
    ]

    if single_subscriber:
        subscriber_files = [f"{single_subscriber}.json"]

    for sub_file in sorted(subscriber_files):
        sub_path = os.path.join(sub_dir, sub_file)
        sub_name = sub_file.replace(".json", "")
        out_dir = os.path.join(out_root, sub_name)
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            "python",
            ENGINE_SCRIPT,
            kit_name,
            start_date,
            end_date,
            sub_path
        ]

        print(f"[{kit_name} BATCH v3.7] Processing: {sub_file}")
        print(f"[CMD] {' '.join(cmd)}")

        subprocess.run(cmd, cwd=BASE_DIR)

    print(f"\n[{kit_name} BATCH v3.7] COMPLETED.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", required=True, help="Kit name, e.g. BOSK_TEST")
    parser.add_argument("--date", required=True, help="Single forecast date (YYYY-MM-DD)")
    parser.add_argument("--subscriber", required=False, help="Single subscriber ID")
    args = parser.parse_args()

    run_batch(args.date, args.date, kit_name=args.kit, single_subscriber=args.subscriber)
