import os
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
    kit_prefix = kit_name.split("_")[0]  # e.g. BOSK_ → BOSK

    forecast_path = os.path.join(kit_dir, "forecast.csv")
    if not os.path.isfile(forecast_path):
        print(f"[WARN] {kit_name}: forecast.csv not found, skipping.")
        return

    print(f"[BUILD] {kit_name}: Loading {forecast_path} ...")
    df = pd.read_csv(forecast_path)

    # Ensure hit_type column exists in correct position
    cols = list(df.columns)

    if "hit_type" not in cols:
        insert_idx = len(cols)
        if "primary_play_type" in cols:
            insert_idx = cols.index("primary_play_type") + 1

        new_cols = cols[:insert_idx] + ["hit_type"] + cols[insert_idx:]
        df["hit_type"] = "PENDING"
        df = df[new_cols]
        print(f"[BUILD] {kit_name}: Inserted hit_type.")
    else:
        df["hit_type"] = df["hit_type"].fillna("PENDING")
        print(f"[BUILD] {kit_name}: hit_type already present.")

    # Save hitlog
    hitlog_name = f"hitlog_{kit_prefix}_v3_7.csv"
    hitlog_path = os.path.join(kit_dir, hitlog_name)

    df.to_csv(hitlog_path, index=False)
    print(f"[DONE] {kit_name}: Hitlog saved → {hitlog_path} (rows={len(df)})")


def main():
    print("[HITLOG v3.7] Building hitlogs for all kit directories...")
    kit_dirs = find_kit_dirs()

    if not kit_dirs:
        print("[HITLOG v3.7] No kits found to process.")
        return

    for kd in kit_dirs:
        build_hitlog_for_kit(kd)

    print("[HITLOG v3.7] All hitlogs completed.")


if __name__ == "__main__":
    main()
