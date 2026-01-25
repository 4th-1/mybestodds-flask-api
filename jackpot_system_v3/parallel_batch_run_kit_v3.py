# parallel_batch_run_kit_v3.py
"""
Parallel batch runner for Jackpot Engine V3.

Usage (from project root):

  # Run BOOK3 for ALL subscribers with 8 parallel workers
  python parallel_batch_run_kit_v3.py BOOK3 8

  # Run BOOK for ALL subscribers with 4 parallel workers (default)
  python parallel_batch_run_kit_v3.py BOOK

  # Run BOSK for ALL subscribers with 12 parallel workers
  python parallel_batch_run_kit_v3.py BOSK 12
"""

import sys
from kits.parallel_batch_runner import run_parallel_batch_for_kit


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(
            "Usage:\n"
            "  python parallel_batch_run_kit_v3.py <KIT_LABEL> [max_workers]\n\n"
            "Examples:\n"
            "  python parallel_batch_run_kit_v3.py BOOK3 8\n"
            "  python parallel_batch_run_kit_v3.py BOOK 4\n"
            "  python parallel_batch_run_kit_v3.py BOSK 12\n\n"
            "Default max_workers: 4\n"
        )
        return

    kit_label = argv[1].upper().strip()
    max_workers = int(argv[2]) if len(argv) > 2 else 4

    if kit_label not in {"BOOK3", "BOOK", "BOSK"}:
        print(f"[BATCH] WARNING: Unrecognized KIT_LABEL '{kit_label}'. Expected BOOK3, BOOK, or BOSK.")

    print(f"[BATCH] Starting parallel batch run for KIT = {kit_label} with {max_workers} workers")
    run_parallel_batch_for_kit(kit_label, max_workers)
    print(f"[BATCH] Completed parallel batch run for KIT = {kit_label}")


if __name__ == "__main__":
    main(sys.argv)
