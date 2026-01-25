import os
from pathlib import Path

import pandas as pd


# ---------- CONFIG: KIT ROOTS (YOUR 3 COMBINED KITS) ----------
KIT_ROOTS = {
    "BOOK3": Path(r"C:\MyBestOdds\jackpot_system_v3\output\BOOK3_2025-09-01_to_2025-11-10"),
    "BOOK": Path(r"C:\MyBestOdds\jackpot_system_v3\output\BOOK_2025-09-01_to_2025-11-10"),
    "BOSK": Path(r"C:\MyBestOdds\jackpot_system_v3\output\BOSK_2025-09-01_to_2025-11-10"),
}

# Where to drop the Sentinel summary CSVs
AUDIT_DIR = Path(r"C:\MyBestOdds\jackpot_system_v3\outputs\AUDIT_V3_7")


def find_csv_files(root: Path):
    """
    Recursively find ALL CSV files under `root`.
    """
    if not root.exists():
        print(f"[SENTINEL] WARNING — Kit root does not exist: {root}")
        return []

    return list(root.rglob("*.csv"))


def audit_one_kit(kit_name: str, root: Path):
    """
    For one kit (BOOK3 / BOOK / BOSK):
    - Find CSVs
    - Keep only those with a `hit_type` column
    - Concatenate and compute hit_type counts
    - Save summary CSV
    """
    print(f"\n[SENTINEL] === Auditing {kit_name} ===")
    csv_files = find_csv_files(root)

    if not csv_files:
        print(f"[SENTINEL] No CSV files found under {root}")
        return None

    print(f"[SENTINEL:{kit_name}] Found {len(csv_files)} CSV file(s).")

    frames = []
    total_rows = 0
    used_files = 0

    for f in csv_files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"[SENTINEL:{kit_name}] Skipping {f.name} (read error: {e})")
            continue

        if "hit_type" not in df.columns:
            # Not an audit/forecast file we care about
            continue

        used_files += 1
        rows = len(df)
        total_rows += rows
        frames.append(df)

    if not frames:
        print(f"[SENTINEL:{kit_name}] No CSVs with 'hit_type' column found under {root}")
        return None

    all_df = pd.concat(frames, ignore_index=True)

    # Normalize hit_type a bit just in case of casing/spaces
    all_df["hit_type"] = all_df["hit_type"].astype(str).str.strip().str.upper()

    counts = all_df["hit_type"].value_counts().sort_index()

    print(f"[SENTINEL:{kit_name}] Used {used_files} CSV file(s), {total_rows} row(s).")
    print(f"[SENTINEL:{kit_name}] Hit summary:")
    print(counts)

    # Ensure audit directory exists
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # Save summary to CSV
    summary_path = AUDIT_DIR / f"{kit_name}_SENTINEL_v3_7_summary.csv"
    counts.to_csv(summary_path, header=["count"])

    print(f"[SENTINEL:{kit_name}] Summary saved to: {summary_path}")
    return counts


def main():
    print("[SENTINEL] ===============================================")
    print("[SENTINEL] v3.7 Multi-Kit Audit — BOOK3 + BOOK + BOSK")
    print("[SENTINEL] ===============================================")

    results = {}

    for kit_name, root in KIT_ROOTS.items():
        counts = audit_one_kit(kit_name, root)
        results[kit_name] = counts

    print("\n[SENTINEL] ============ COMBINED OVERVIEW ============")
    for kit_name, counts in results.items():
        if counts is None:
            print(f"[{kit_name}] NO DATA")
            continue
        total = int(counts.sum())
        straight = int(counts.get("STRAIGHT", 0))
        box = int(counts.get("BOX", 0))
        miss = int(counts.get("MISS", 0))
        print(
            f"[{kit_name}] TOTAL={total} | "
            f"STRAIGHT={straight} | BOX={box} | MISS={miss}"
        )

    print("[SENTINEL] ===============================================")


if __name__ == "__main__":
    main()
