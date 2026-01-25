# batch_run_kit_v3.py
"""
Batch runner for Jackpot Engine V3.

Usage (from project root):

  # Run BOOK3 for ALL subscribers
  "C:\\Users\\suppo\\AppData\\Local\\Programs\\Python\\Python310\\python.exe" batch_run_kit_v3.py ALL BOOK3

  # Run BOOK for ALL subscribers
  "C:\\Users\\suppo\\AppData\\Local\\Programs\\Python\\Python310\\python.exe" batch_run_kit_v3.py ALL BOOK

  # Run BOSK for ALL subscribers
  "C:\\Users\\suppo\\AppData\\Local\\Programs\\Python\\Python310\\python.exe" batch_run_kit_v3.py ALL BOSK
"""

import sys
from kits.batch_kit_runner import run_batch_for_kit


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(
            "Usage:\n"
            "  python batch_run_kit_v3.py ALL <KIT_LABEL>\n\n"
            "Examples:\n"
            "  python batch_run_kit_v3.py ALL BOOK3\n"
            "  python batch_run_kit_v3.py ALL BOOK\n"
            "  python batch_run_kit_v3.py ALL BOSK\n"
        )
        return

    # argv[1] is the sentinel (ALL / A.L.L. etc.) — we ignore exact spelling for now
    kit_label = argv[2].upper().strip()

    if kit_label not in {"BOOK3", "BOOK", "BOSK"}:
        print(f"[BATCH] WARNING: Unrecognized KIT_LABEL '{kit_label}'. Expected BOOK3, BOOK, or BOSK.")
        # still allow it, in case you later add more kits
        # return

    print(f"[BATCH] Starting batch run for KIT = {kit_label} (ALL subscribers)")
    run_batch_for_kit(kit_label)
    print(f"[BATCH] Completed batch run for KIT = {kit_label}")


if __name__ == "__main__":
    main(sys.argv)
