import os
import csv
import sys
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

KIT_PREFIXES = ["BOOK3", "BOOK", "BOSK"]  # Jackpot kits for v3.7


def find_kit_dirs():
    """
    Find kit-level directories like:
      output/BOOK3_2025-09-01_to_2025-11-10
      output/BOOK_2025-09-01_to_2025-11-10
      output/BOSK_2025-09-01_to_2025-11-10
    """
    if not os.path.isdir(OUTPUT_DIR):
        print(f"[ERROR] OUTPUT_DIR not found: {OUTPUT_DIR}")
        return []

    kit_dirs = []
    for name in os.listdir(OUTPUT_DIR):
        full = os.path.join(OUTPUT_DIR, name)
        if not os.path.isdir(full):
            continue
        if any(name.startswith(prefix + "_") for prefix in KIT_PREFIXES):
            kit_dirs.append(full)

    return sorted(kit_dirs)


def build_hitlog_for_kit(kit_dir: str):
    """
    For a single kit directory, read its root-level forecast.csv,
    insert a 'hit_type' column (default 'PENDING') right after
    'primary_play_type', and write hitlog_<KIT>_v3_7.csv into the same folder.
    """
    kit_name = os.path.basename(kit_dir)
    # e.g. BOSK_2025-09-01_to_2025-11-10 -> BOSK
    kit_prefix = kit_name.split("_")[0]

    forecast_path = os.path.join(kit_dir, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[WARN] {kit_name}: forecast.csv not found at {forecast_path}, skipping.")
        return

    print(f"[BUILD] {kit_name}: Loading {forecast_path} ...")
    df = pd.read_csv(forecast_path)

    # Ensure 'hit_type' column exists and is positioned right after 'primary_play_type'
    cols = list(df.columns)
    if "hit_type" not in cols:
        insert_idx = len(cols)
        if "primary_play_type" in cols:
            insert_idx = cols.index("primary_play_type") + 1

        # Build new column order with 'hit_type' inserted
        new_cols = cols[:insert_idx] + ["hit_type"] + cols[insert_idx:]
        # Initialize hit_type = 'PENDING'
        df["hit_type"] = "PENDING"
        # Reorder
        df = df[new_cols]
        print(f"[BUILD] {kit_name}: Inserted 'hit_type' column after 'primary_play_type'.")
    else:
        # If hit_type already present, just ensure it's there and fill missing with PENDING
        df["hit_type"] = df["hit_type"].fillna("PENDING")
        print(f"[BUILD] {kit_name}: 'hit_type' already present; filling missing with 'PENDING'.")

    # Output hitlog path
    hitlog_name = f"hitlog_{kit_prefix}_v3_7.csv"
    hitlog_path = os.path.join(kit_dir, hitlog_name)

    df.to_csv(hitlog_path, index=False)
    print(f"[DONE] {kit_name}: Hitlog written -> {hitlog_path} (rows={len(df)})")


def main():
    print("[HITLOG v3.7] Building kit-level hit logs from forecast.csv (Option C scaffold).")
    print(f"[HITLOG v3.7] ROOT_DIR:   {ROOT_DIR}")
    print(f"[HITLOG v3.7] OUTPUT_DIR: {OUTPUT_DIR}")

    kit_dirs = find_kit_dirs()
    if not kit_dirs:
        print("[HITLOG v3.7] No kit directories found. Nothing to do.")
        return

    print(f"[HITLOG v3.7] Found {len(kit_dirs)} kit directory(ies):")
    for kd in kit_dirs:
        print(f"  - {os.path.basename(kd)}")

    for kd in kit_dirs:
        build_hitlog_for_kit(kd)

    print("[HITLOG v3.7] All done.")


if __name__ == "__main__":
    # So you can run:  python audit/build_hitlog_v3_7.py
    main()
