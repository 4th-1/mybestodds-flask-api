# core/subscriber_normalizer.py

import os
import json
from pathlib import Path

REQUIRED_FIELDS = [
    "name",
    "initials",
    "coverage_start",
    "coverage_end"
]

def normalize_subscriber_files():
    """
    Automatically normalizes subscriber filenames inside:
    jackpot_system_v3/data/subscribers/

    - Validates required fields inside each JSON
    - Renames file to <INITIALS>.json
    - Prevents missing or malformed files from breaking the engine
    """

    root = Path(__file__).resolve().parents[1]
    sub_dir = root / "data" / "subscribers"

    # Skip if directory doesn't exist (e.g., on Railway with no subscribers yet)
    if not sub_dir.exists():
        print(f"[NORMALIZER] Subscribers directory not found: {sub_dir}. Skipping normalization.")
        return

    for file in sub_dir.iterdir():
        if not file.name.lower().endswith(".json"):
            continue

        try:
            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[NORMALIZER WARNING] Could not read JSON file: {file.name} → {e}")
            continue

        # Validate required fields exist
        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            print(f"[NORMALIZER ERROR] Missing required fields {missing} in {file.name}. File skipped.")
            continue

        initials = data["initials"].strip().upper()
        new_filename = f"{initials}.json"
        new_path = sub_dir / new_filename

        # If the filename is already correct, skip renaming
        if file.name == new_filename:
            print(f"[NORMALIZER] {file.name} already normalized.")
            continue

        # Rename the file
        try:
            file.rename(new_path)
            print(f"[NORMALIZER] Renamed {file.name} → {new_filename}")
        except Exception as e:
            print(f"[NORMALIZER ERROR] Could not rename {file.name}: {e}")

# Force rebuild: 2026-01-26-09-36-26
