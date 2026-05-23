"""
june4_settle.py — June 4 EV Observation verdict runner.

Runs the full 14-day Cash3 settlement, prints a per-lane verdict table,
and outputs the exact one-line change needed to enable Cash4 observation.

Usage:
    python june4_settle.py            # settle + verdict + show Cash4 flip
    python june4_settle.py --dry-run  # verdict only, no file writes

Run this on or after June 4, 2026 once the final Night draw completes.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT         = Path(__file__).parent
LOG_DIR      = ROOT / "data" / "ev_observe"
SUMMARY_CSV  = LOG_DIR / "ev_observe_extended_summary.csv"
API_SERVER   = ROOT / "api_server.py"

# Minimum ROI to promote a lane to production
PROMOTE_ROI_THRESHOLD = 0.15   # ≥ 15% positive ROI
PROMOTE_HIT_THRESHOLD = 0.03   # ≥ 3% hit rate (meaningful signal above noise)
MIN_TRIALS            = 20     # ignore lanes with fewer entries


def run_settlement(dry_run: bool) -> bool:
    """Run settle_ev_extended.py to write settled JSONL + summary CSV."""
    if dry_run:
        print("[dry-run] Skipping settlement — using existing summary CSV.\n")
        return SUMMARY_CSV.exists()

    print("Running settle_ev_extended.py ...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "settle_ev_extended.py")],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def load_summary(csv_path: Path) -> list[dict]:
    """Load the per-lane summary CSV written by settle_ev_extended."""
    if not csv_path.exists():
        print(f"ERROR: Summary CSV not found at {csv_path}")
        print("       Run settle_ev_extended.py first, or pass --dry-run if it already exists.")
        sys.exit(1)
    rows = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def print_verdict(rows: list[dict]) -> None:
    """Print a formatted per-lane verdict table with PROMOTE / HOLD / REJECT status."""

    # Group by game × session × lane
    from collections import defaultdict
    buckets: dict[tuple, dict] = defaultdict(lambda: {
        "trials": 0, "hits": 0, "roi_sum": 0.0
    })

    for r in rows:
        game  = (r.get("game")    or "cash3").lower()
        sess  = (r.get("session") or r.get("draw") or "").upper()
        lane  = (r.get("lane")    or "").upper()
        key   = (game, sess, lane)
        b     = buckets[key]
        b["trials"] += 1
        if str(r.get("hit_flag", "0")) == "1":
            b["hits"] += 1
        try:
            b["roi_sum"] += float(r.get("roi", 0) or 0)
        except (ValueError, TypeError):
            pass

    print("\n" + "=" * 72)
    print("  EV OBSERVATION WINDOW — 14-DAY VERDICT   (June 4, 2026)")
    print("=" * 72)
    fmt = "  {:<8} {:<12} {:<16} {:>7} {:>7} {:>8}  {}"
    print(fmt.format("GAME", "SESSION", "LANE", "TRIALS", "HIT%", "ROI%", "VERDICT"))
    print("  " + "-" * 68)

    promotes, holds, rejects = [], [], []

    for (game, sess, lane), b in sorted(buckets.items()):
        n      = b["trials"]
        if n < MIN_TRIALS:
            verdict = "SKIP (low n)"
        else:
            hit_rate = b["hits"] / n
            avg_roi  = b["roi_sum"] / n
            if avg_roi >= PROMOTE_ROI_THRESHOLD and hit_rate >= PROMOTE_HIT_THRESHOLD:
                verdict = "PROMOTE ✓"
                promotes.append(f"{game.upper()} {sess} {lane}")
            elif avg_roi > 0:
                verdict = "HOLD ~"
                holds.append(f"{game.upper()} {sess} {lane}")
            else:
                verdict = "REJECT ✗"
                rejects.append(f"{game.upper()} {sess} {lane}")

            hit_pct = f"{hit_rate*100:.1f}%"
            roi_pct = f"{avg_roi*100:+.1f}%"
            print(fmt.format(game.upper(), sess, lane, n, hit_pct, roi_pct, verdict))
            continue

        print(fmt.format(game.upper(), sess, lane, n, "--", "--", verdict))

    print("  " + "-" * 68)
    print(f"\n  PROMOTE ({len(promotes)}): " + (", ".join(promotes) if promotes else "none"))
    print(f"  HOLD    ({len(holds)}):    " + (", ".join(holds) if holds else "none"))
    print(f"  REJECT  ({len(rejects)}):  " + (", ".join(rejects) if rejects else "none"))
    print()


def show_cash4_flip_instructions() -> None:
    """Show the exact edit needed to enable Cash4 observation."""
    print("=" * 72)
    print("  NEXT STEP: Enable Cash4 EV Observation")
    print("=" * 72)
    print()
    print("  File:  api_server.py  (line ~12)")
    print()
    print("  Change:")
    print("    CASH4_OBSERVE_ENABLED: bool = False  # TODO(June 4): flip to True")
    print()
    print("  To:")
    print("    CASH4_OBSERVE_ENABLED: bool = True   # Cash4 window active")
    print()
    print("  Then commit and push:")
    print("    git add api_server.py")
    print('    git commit -m "feat: enable Cash4 EV observation window"')
    print("    git push origin main")
    print()
    print("  Cash4 cron jobs reuse the same 3 daily slots (MIDDAY/EVENING/NIGHT).")
    print("  No new cron-job.org setup needed.")
    print()
    print("  Settle Cash4 after its own 14-day window using:")
    print("    python settle_ev_extended.py")
    print()


def flip_cash4_flag(dry_run: bool) -> None:
    """Optionally apply the CASH4_OBSERVE_ENABLED flip automatically."""
    old = "CASH4_OBSERVE_ENABLED: bool = False  # TODO(June 4): flip to True"
    new = "CASH4_OBSERVE_ENABLED: bool = True   # Cash4 window active"

    content = API_SERVER.read_text(encoding="utf-8")
    if old not in content:
        if new in content:
            print("  Cash4 flag already True — no change needed.")
        else:
            print("  WARNING: Could not find CASH4_OBSERVE_ENABLED line in api_server.py.")
            print("           Apply the change manually (see instructions above).")
        return

    if dry_run:
        print("  [dry-run] Would flip CASH4_OBSERVE_ENABLED = True in api_server.py")
        return

    API_SERVER.write_text(content.replace(old, new), encoding="utf-8")
    print("  Flipped CASH4_OBSERVE_ENABLED = True in api_server.py  ✓")
    print("  Commit and push to deploy:")
    print('    git add api_server.py && git commit -m "feat: enable Cash4 EV observation window" && git push origin main')


def main():
    parser = argparse.ArgumentParser(description="June 4 EV verdict runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print verdict from existing CSV; skip settlement write and flag flip",
    )
    parser.add_argument(
        "--flip-cash4",
        action="store_true",
        help="Apply the CASH4_OBSERVE_ENABLED=True change to api_server.py",
    )
    args = parser.parse_args()

    # 1. Run settlement (writes JSONL + CSV)
    ok = run_settlement(args.dry_run)
    if not ok:
        print("Settlement failed — check settle_ev_extended.py output above.")
        sys.exit(1)

    # 2. Load summary and print verdict table
    rows = load_summary(SUMMARY_CSV)
    print_verdict(rows)

    # 3. Show or apply Cash4 flip
    show_cash4_flip_instructions()
    if args.flip_cash4:
        flip_cash4_flag(args.dry_run)


if __name__ == "__main__":
    main()
