# update_book3_subscribers.py
import json
from pathlib import Path

root = Path(__file__).resolve().parent
book3_dir = root / "data" / "subscribers" / "BOOK3"

# choose your coverage window here
COVERAGE_START = "2025-09-01"
COVERAGE_END   = "2025-11-10"

def make_initials(stem: str) -> str:
    """
    Reasonable default initials generator.
    For BOOK3_Test_001 -> 'T001'
    Otherwise use first 2 letters of stem uppercased.
    """
    if stem.startswith("BOOK3_Test_"):
        suffix = stem[len("BOOK3_Test_"):]
        return f"T{suffix}"
    return stem[:2].upper()

def normalize_file(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    changed = False
    stem = path.stem

    # name
    if "name" not in data:
        data["name"] = data.get("subscriber_name", stem)
        changed = True

    # initials
    if "initials" not in data:
        data["initials"] = data.get("abbr", make_initials(stem))
        changed = True

    # coverage_start / coverage_end
    if "coverage_start" not in data:
        data["coverage_start"] = COVERAGE_START
        changed = True
    if "coverage_end" not in data:
        data["coverage_end"] = COVERAGE_END
        changed = True

    if changed:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Fixed: {path.name}")

def main():
    if not book3_dir.exists():
        print(f"BOOK3 dir not found: {book3_dir}")
        return
    for p in book3_dir.glob("*.json"):
        normalize_file(p)

if __name__ == "__main__":
    main()
