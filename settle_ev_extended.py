"""
settle_ev_extended.py — Full 7-Lane Cash3 Settlement Layer
===========================================================
Extends the frozen settle_ev_log.py prize/hit logic to cover ALL Cash3
play types logged during the 14-day OBSERVE_ALL window:

  STRAIGHT      — exact order wins $500
  BOX           — any order wins $80 (6-way) or $160 (3-way)
  STRAIGHT_BOX  — exact=$290+$40, any-order=$40
  COMBO         — buy all permutations as straights; wins $500 on any match
                  cost scales with permutation count (3-way: $1.50, 6-way: $3.00)
  STRAIGHT+1OFF — exact 1 digit off in position; prize $25 per 50¢ ticket
  FRONT_PAIR    — first 2 digits match regardless of last digit; wins $50
  BACK_PAIR     — last 2 digits match regardless of first digit; wins $50

The frozen settle_ev_log.py only handles STRAIGHT_BOX, BOX, STRAIGHT, and
STRAIGHT+1OFF with a fixed prize table.  This script handles all 7 and
produces a SEPARATE settled file + summary so the frozen layer is untouched.

Output:
  data/ev_observe/ev_observe_log.extended.settled.jsonl
  data/ev_observe/ev_observe_extended_summary.csv

Run:
  python settle_ev_extended.py

Run promotion audit only:
  python settle_ev_extended.py --audit
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from itertools import permutations
from pathlib import Path
from typing import Optional

ROOT           = Path(__file__).parent
LOG_DIR        = ROOT / "data" / "ev_observe"
RAW_LOG        = LOG_DIR / "ev_observe_log.jsonl"
SETTLED_LOG    = LOG_DIR / "ev_observe_log.extended.settled.jsonl"
SUMMARY_CSV    = LOG_DIR / "ev_observe_extended_summary.csv"
GA_RESULTS_DIR = ROOT / "jackpot_system_v3" / "data" / "ga_results"

# ---------------------------------------------------------------------------
# Georgia Cash3 prize table (per $1 stake, based on $0.50 base ticket × 2)
#
#  STRAIGHT      — $500 (exact order)
#  BOX 6-way     — $80  (all 3 digits unique, any order)
#  BOX 3-way     — $160 (one repeated digit, any order)
#  STRAIGHT_BOX  — $290 straight + $40 box = $330 exact; $40 box only
#  COMBO 6-way   — $500 win, cost $3.00 (6 tickets × $0.50)
#  COMBO 3-way   — $500 win, cost $1.50 (3 tickets × $0.50)
#  STRAIGHT+1OFF — $25 (one digit off in position)
#  FRONT_PAIR    — $50 (first 2 digits match, any last digit)
#  BACK_PAIR     — $50 (last 2 digits match, any first digit)
# ---------------------------------------------------------------------------

# Payouts per $1.00 stake (we normalise all as "per $1 wagered")
PRIZE: dict[tuple[str, str, str], float] = {
    # (game, lane, hit_type) → payout per $1 stake
    ("cash3", "STRAIGHT",     "EXACT_HIT"):   500.00,
    ("cash3", "STRAIGHT",     "MISS"):          0.00,
    ("cash3", "BOX",          "BOX_HIT"):       80.00,  # 6-way default; see _payout() for 3-way
    ("cash3", "BOX",          "MISS"):           0.00,
    ("cash3", "STRAIGHT_BOX", "EXACT_HIT"):    330.00,  # $290 straight + $40 box
    ("cash3", "STRAIGHT_BOX", "BOX_HIT"):       40.00,
    ("cash3", "STRAIGHT_BOX", "MISS"):           0.00,
    # COMBO: win is $500, but cost scales with permutation count.
    # We store hit_type as EXACT_HIT (any permutation matched = straight win).
    # ROI is handled in _payout() by dividing by combo_cost.
    ("cash3", "COMBO",        "EXACT_HIT"):    500.00,
    ("cash3", "COMBO",        "MISS"):           0.00,
    # STRAIGHT+1OFF: $25 prize on $0.50 ticket ($50 per $1 stake)
    ("cash3", "STRAIGHT+1OFF","ONE_OFF_HIT"):   50.00,
    ("cash3", "STRAIGHT+1OFF","MISS"):           0.00,
    # FRONT_PAIR / BACK_PAIR: $50 per $1 stake
    ("cash3", "FRONT_PAIR",   "PAIR_HIT"):      50.00,
    ("cash3", "FRONT_PAIR",   "MISS"):           0.00,
    ("cash3", "BACK_PAIR",    "PAIR_HIT"):      50.00,
    ("cash3", "BACK_PAIR",    "MISS"):           0.00,
}

STAKE = 1.00  # $1 normalised stake for ROI calculation


# ---------------------------------------------------------------------------
# Permutation helpers
# ---------------------------------------------------------------------------

def _combo_perms(number: str) -> list[str]:
    """All unique ordered permutations of the digits in number."""
    return list({"".join(p) for p in permutations(number)})


def _combo_cost(number: str) -> float:
    """Cost of a COMBO ticket in $0.50 increments (one ticket per permutation)."""
    return len(_combo_perms(number)) * 0.50


def _is_3way(number: str) -> bool:
    """True if number has a repeated digit (3 unique permutations)."""
    return len(set(number)) < len(number)


# ---------------------------------------------------------------------------
# Hit detection — all 7 play types
# ---------------------------------------------------------------------------

def _hit_type(pick: str, result: str, lane: str) -> str:
    """Classify match between pick and result for the given lane."""
    p = str(pick).strip().zfill(3)
    r = str(result).strip().zfill(3)
    if not p or not r:
        return "MISS"
    lane_up = lane.upper()

    if lane_up == "STRAIGHT":
        return "EXACT_HIT" if p == r else "MISS"

    if lane_up == "BOX":
        return "BOX_HIT" if sorted(p) == sorted(r) else "MISS"

    if lane_up == "STRAIGHT_BOX":
        if p == r:
            return "EXACT_HIT"
        if sorted(p) == sorted(r):
            return "BOX_HIT"
        return "MISS"

    if lane_up == "COMBO":
        # Win if drawn number is ANY permutation of pick
        if sorted(p) == sorted(r):
            return "EXACT_HIT"
        return "MISS"

    if lane_up in ("STRAIGHT+1OFF", "ONE_OFF"):
        if len(p) == len(r) == 3:
            if p == r:
                return "ONE_OFF_HIT"  # exact match also wins
            diffs = sum(1 for a, b in zip(p, r) if a != b)
            if diffs == 1:
                return "ONE_OFF_HIT"
        return "MISS"

    if lane_up == "FRONT_PAIR":
        return "PAIR_HIT" if p[:2] == r[:2] else "MISS"

    if lane_up == "BACK_PAIR":
        return "PAIR_HIT" if p[-2:] == r[-2:] else "MISS"

    return "MISS"


def _payout(game: str, lane: str, hit: str, pick: str = "") -> float:
    """
    Return gross payout per $1.00 stake.
    BOX 3-way and COMBO cost scaling are handled here.
    """
    g = game.lower().replace(" ", "")
    l = lane.upper()

    # BOX 3-way pays $160 instead of $80
    if l == "BOX" and hit == "BOX_HIT" and _is_3way(pick):
        return 160.00

    # COMBO: normalise to $1 stake by scaling by combo cost
    # e.g. 3-way COMBO: cost=$1.50, payout=$500 → per-$1-stake = 500/1.50 = $333
    if l == "COMBO" and hit == "EXACT_HIT" and pick:
        cost = _combo_cost(pick)
        return round(500.00 / cost, 2) if cost > 0 else 0.0

    key = (g, l, hit)
    return PRIZE.get(key, 0.0)


# ---------------------------------------------------------------------------
# GA results loader
# ---------------------------------------------------------------------------

_SESSION_FILE_MAP = {
    "NIGHT":   GA_RESULTS_DIR / "cash3_night.json",
    "MIDDAY":  GA_RESULTS_DIR / "cash3_midday.json",
    "EVENING": GA_RESULTS_DIR / "cash3_evening.json",
}


def _parse_ga_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def load_actual_results() -> dict[tuple[str, str], str]:
    """Returns {(date_iso, SESSION_UPPER): winning_number}."""
    actuals: dict[tuple[str, str], str] = {}
    for session, fpath in _SESSION_FILE_MAP.items():
        if not fpath.exists():
            print(f"  [warn] missing GA results file: {fpath.name}")
            continue
        with open(fpath, encoding="utf-8") as f:
            rows = json.load(f)
        for row in rows:
            date_iso = _parse_ga_date(row.get("date") or row.get("draw_date", ""))
            wn = str(row.get("winning_number", "") or row.get("winning_numbers", "")).strip()
            if date_iso and wn:
                actuals[(date_iso, session)] = wn
    print(f"  Loaded {len(actuals):,} actual draw results")
    return actuals


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

SETTLED_FIELDS = [
    "grain_id", "settled_at", "date", "draw", "game", "lane", "pick",
    "overlay_tier", "mmfsn_tier",
    "ev_score", "ev_decision",
    "result", "hit_type", "hit_flag",
    "stake", "payout", "profit", "roi",
    "combo_cost", "combo_perms",
]


def settle(
    raw_path: Path = RAW_LOG,
    settled_path: Path = SETTLED_LOG,
    summary_path: Path = SUMMARY_CSV,
    actuals: Optional[dict] = None,
) -> list[dict]:
    """
    Load raw log, join to actuals, write settled JSONL + summary CSV.
    Returns list of settled rows.
    """
    if not raw_path.exists():
        print(f"  [info] No raw log found at {raw_path} — nothing to settle yet.")
        return []

    if actuals is None:
        actuals = load_actual_results()

    raw_rows: list[dict] = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    raw_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    total_raw = len(raw_rows)
    print(f"  Raw log rows: {total_raw:,}")

    # Deduplicate grain_ids
    seen_grains: set[str] = set()
    unique_rows: list[dict] = []
    dup_count = 0
    for row in raw_rows:
        gid = row.get("grain_id", "")
        if gid and gid in seen_grains:
            dup_count += 1
            continue
        seen_grains.add(gid)
        unique_rows.append(row)
    if dup_count:
        print(f"  Deduplicated {dup_count} duplicate grain_ids → {len(unique_rows):,} unique rows")

    settled_rows: list[dict] = []
    missing_result_rows = 0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in unique_rows:
        draw_date    = row.get("date", "")
        draw_session = row.get("draw", "").upper()
        game         = row.get("game", "")
        lane         = row.get("lane", "")
        pick         = str(row.get("pick", ""))

        result = actuals.get((draw_date, draw_session), "")
        if not result:
            missing_result_rows += 1
            hit_t  = ""
            hit_f  = ""
            payout_val = ""
            profit_val = ""
            roi_val    = ""
        else:
            hit_t      = _hit_type(pick, result, lane)
            hit_f      = 1 if hit_t != "MISS" else 0
            payout_val = _payout(game, lane, hit_t, pick)
            profit_val = round(payout_val - STAKE, 2)
            roi_val    = round((profit_val / STAKE) * 100, 2)

        # COMBO metadata
        combo_cost  = round(_combo_cost(pick), 2) if lane.upper() == "COMBO" else ""
        combo_perms = len(_combo_perms(pick))     if lane.upper() == "COMBO" else ""

        settled_rows.append({
            "grain_id":    row.get("grain_id", ""),
            "settled_at":  now_str,
            "date":        draw_date,
            "draw":        draw_session,
            "game":        game,
            "lane":        lane,
            "pick":        pick,
            "overlay_tier": row.get("overlay_tier", ""),
            "mmfsn_tier":  row.get("mmfsn_tier", ""),
            "ev_score":    row.get("ev_score", ""),
            "ev_decision": row.get("decision", row.get("ev_decision", "")),
            "result":      result,
            "hit_type":    hit_t,
            "hit_flag":    hit_f,
            "stake":       STAKE,
            "payout":      payout_val,
            "profit":      profit_val,
            "roi":         roi_val,
            "combo_cost":  combo_cost,
            "combo_perms": combo_perms,
        })

    print(f"  Missing result rows : {missing_result_rows:,}")
    settled_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settled_path, "w", encoding="utf-8") as f:
        for row in settled_rows:
            f.write(json.dumps(row) + "\n")
    print(f"  Wrote {len(settled_rows):,} settled rows → {settled_path.name}")

    # Summary CSV
    _write_summary(settled_rows, summary_path)
    return settled_rows


# ---------------------------------------------------------------------------
# Per-lane summary
# ---------------------------------------------------------------------------

def _write_summary(settled_rows: list[dict], summary_path: Path) -> None:
    """Aggregate hit rate + ROI per (game, session, lane) condition."""
    stats: dict[tuple, dict] = defaultdict(lambda: {
        "picks": 0, "hits": 0, "total_payout": 0.0, "total_profit": 0.0
    })

    for row in settled_rows:
        if not row.get("result"):  # unsettled (draw result not yet available)
            continue
        key = (row["game"], row["draw"], row["lane"])
        s   = stats[key]
        s["picks"]        += 1
        s["hits"]         += int(row.get("hit_flag") or 0)
        s["total_payout"] += float(row.get("payout") or 0)
        s["total_profit"] += float(row.get("profit") or 0)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "game", "session", "lane",
            "picks", "hits", "hit_rate_pct",
            "total_payout", "total_profit", "roi_pct",
            "verdict",
        ])
        writer.writeheader()
        for (game, session, lane), s in sorted(stats.items()):
            picks        = s["picks"]
            hits         = s["hits"]
            hit_rate     = round((hits / picks * 100), 2) if picks else 0.0
            total_payout = round(s["total_payout"], 2)
            total_profit = round(s["total_profit"], 2)
            roi_pct      = round((total_profit / (picks * STAKE) * 100), 2) if picks else 0.0
            # Promotion criteria: roi_pct > 0 AND hit_rate > 1.0 AND >= 5 settled picks
            if picks >= 5 and roi_pct > 0 and hit_rate > 1.0:
                verdict = "PROMOTE"
            elif picks >= 5 and roi_pct < -50.0:
                verdict = "REJECT"
            else:
                verdict = "HOLD"
            writer.writerow({
                "game":          game,
                "session":       session,
                "lane":          lane,
                "picks":         picks,
                "hits":          hits,
                "hit_rate_pct":  hit_rate,
                "total_payout":  total_payout,
                "total_profit":  total_profit,
                "roi_pct":       roi_pct,
                "verdict":       verdict,
            })

    print(f"  Summary → {summary_path.name}  ({len(stats)} conditions)")


# ---------------------------------------------------------------------------
# Promotion audit
# ---------------------------------------------------------------------------

def audit(summary_path: Path = SUMMARY_CSV) -> None:
    """Print promotion/hold/reject verdicts per lane."""
    if not summary_path.exists():
        print("No summary found — run settle first.")
        return
    promotes, holds, rejects = [], [], []
    with open(summary_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = row.get("verdict", "HOLD")
            label = f"{row['game']}|{row['session']}|{row['lane']}  picks={row['picks']}  hits={row['hits']}  roi={row['roi_pct']}%"
            if v == "PROMOTE":
                promotes.append(label)
            elif v == "REJECT":
                rejects.append(label)
            else:
                holds.append(label)
    print(f"\n{'='*60}")
    print(f"PROMOTE ({len(promotes)}):")
    for l in promotes:
        print(f"  ✓ {l}")
    print(f"\nHOLD ({len(holds)}):")
    for l in holds:
        print(f"  ~ {l}")
    print(f"\nREJECT ({len(rejects)}):")
    for l in rejects:
        print(f"  ✗ {l}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="settle_ev_extended — full 7-lane Cash3 settlement")
    parser.add_argument("--audit", action="store_true", help="Print promotion audit only (no re-settle)")
    parser.add_argument("--raw",   default=str(RAW_LOG),     help="Path to raw JSONL log")
    parser.add_argument("--out",   default=str(SETTLED_LOG), help="Path for settled JSONL output")
    parser.add_argument("--csv",   default=str(SUMMARY_CSV), help="Path for summary CSV output")
    args = parser.parse_args()

    if args.audit:
        audit(Path(args.csv))
        sys.exit(0)

    print("\n=== settle_ev_extended — 7-lane Cash3 settlement ===\n")
    rows = settle(
        raw_path=Path(args.raw),
        settled_path=Path(args.out),
        summary_path=Path(args.csv),
    )
    hits  = sum(1 for r in rows if r.get("hit_flag") == 1)
    total = sum(1 for r in rows if r.get("result"))
    print(f"\n  Total settled : {total:,}  |  Hits : {hits}  |  Miss : {total - hits}")
    if total:
        print(f"  Overall hit rate: {hits/total*100:.1f}%")
    print("\nDone.  Run --audit to see per-lane verdicts.\n")
    audit(Path(args.csv))
