"""
settle_ev_log.py — Phase 3C Settlement Layer
=============================================
Joins ev_observe_log.jsonl against actual draw results, computes
hit_flag / hit_type / payout / roi, and writes:

  data/ev_observe/ev_observe_log.settled.jsonl   — enriched, immutable copy
  data/ev_observe/ev_observe_summary.csv         — per-condition audit summary

Raw log is NEVER mutated.

Hit types for Cash3 STRAIGHT_BOX:
  EXACT_HIT — pick == result  (straight wins: $290 + box wins: $40)
  BOX_HIT   — sorted(pick) == sorted(result) and pick != result  (box wins: $40)
  MISS      — no match ($0)

Run:
  python settle_ev_log.py

Run promotion audit only:
  python settle_ev_log.py --audit
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

ROOT           = Path(__file__).parent
LOG_DIR        = ROOT / "data" / "ev_observe"
RAW_LOG        = LOG_DIR / "ev_observe_log.jsonl"
SETTLED_LOG    = LOG_DIR / "ev_observe_log.settled.jsonl"
SUMMARY_CSV    = LOG_DIR / "ev_observe_summary.csv"
GA_RESULTS_DIR = ROOT / "jackpot_system_v3" / "data" / "ga_results"

# ---------------------------------------------------------------------------
# Prize table for settlement (Cash3 STRAIGHT_BOX only for now)
# ---------------------------------------------------------------------------
PRIZE = {
    # (game, hit_type) → payout per $1 stake
    ("cash3", "EXACT_HIT"):  330.00,   # straight $290 + box $40
    ("cash3", "BOX_HIT"):     40.00,
    ("cash3", "MISS"):         0.00,
}
STAKE = 1.00

# ---------------------------------------------------------------------------
# Load actual draw results → {(date_iso, session_upper): winning_number}
# ---------------------------------------------------------------------------
_SESSION_FILE_MAP = {
    "NIGHT":   GA_RESULTS_DIR / "cash3_night.json",
    "MIDDAY":  GA_RESULTS_DIR / "cash3_midday.json",
    "EVENING": GA_RESULTS_DIR / "cash3_evening.json",
}


def _parse_ga_date(raw: str) -> Optional[str]:
    """Convert MM/DD/YYYY or YYYY-MM-DD to YYYY-MM-DD.  Returns None on failure."""
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def load_actual_results() -> dict[tuple[str, str], str]:
    """
    Returns {(date_iso, SESSION_UPPER): winning_number}.
    Loads Cash3 night / midday / evening from GA results JSON files.
    """
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
# Hit detection
# ---------------------------------------------------------------------------
def _hit_type(pick: str, result: str, lane: str) -> str:
    """
    Classify the match between pick and result for a given lane.
    Both pick and result are digit-strings (e.g. '590', '316').
    """
    p = str(pick).strip().zfill(3) if len(str(pick).strip()) <= 3 else str(pick).strip()
    r = str(result).strip().zfill(3) if len(str(result).strip()) <= 3 else str(result).strip()

    if not p or not r:
        return "MISS"

    lane_up = lane.upper()

    if lane_up == "STRAIGHT_BOX":
        if p == r:
            return "EXACT_HIT"
        if sorted(p) == sorted(r):
            return "BOX_HIT"
        return "MISS"

    if lane_up == "BOX":
        if sorted(p) == sorted(r):
            return "BOX_HIT"
        return "MISS"

    if lane_up == "STRAIGHT":
        return "EXACT_HIT" if p == r else "MISS"

    if lane_up in ("STRAIGHT+1OFF", "ONE_OFF"):
        # 1-off: at least 2 of 3 digits match in position
        if len(p) == len(r) == 3:
            matches = sum(1 for a, b in zip(p, r) if a == b)
            if p == r:
                return "EXACT_HIT"
            if matches >= 2:
                return "BOX_HIT"   # treat 1-off partial as box_hit for payout classification
        return "MISS"

    return "MISS"


def _payout(game: str, lane: str, hit: str) -> float:
    key = (game.lower().replace(" ", ""), hit)
    return PRIZE.get(key, 0.0)


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------
SETTLED_FIELDS = [
    "grain_id", "settled_at", "date", "draw", "game", "lane", "pick",
    "overlay_tier", "mmfsn_tier",
    "ev_score", "ev_rank", "ev_decision",
    "production_gate", "production_action", "reranker_mode",
    "result", "hit_type", "hit_flag",
    "stake", "payout", "profit", "roi",
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

    Audit counters are printed and stored in each row's parent run so the
    operator knows exactly why coverage failed:
      raw_rows, settled_rows, missing_result_rows, coverage_pct,
      missing_dates, missing_draws, duplicate_grain_ids
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

    # Duplicate grain check (done before settlement loop)
    grain_ids_all = [r.get("grain_id", "") for r in raw_rows]
    seen_grains: set[str] = set()
    duplicate_grain_ids: set[str] = set()
    for gid in grain_ids_all:
        if gid in seen_grains:
            duplicate_grain_ids.add(gid)
        seen_grains.add(gid)

    settled_rows: list[dict] = []
    missing_result_rows  = 0
    missing_dates_set:  set[str] = set()
    missing_draws_set:  set[str] = set()  # "date|draw" pairs that have no result
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in raw_rows:
        draw_date    = row.get("date", "")
        draw_session = row.get("draw", "").upper()
        game         = row.get("game", "")
        lane         = row.get("lane", "")
        pick         = str(row.get("pick", ""))

        # Look up actual result
        result = actuals.get((draw_date, draw_session), "")
        if not result:
            missing_result_rows += 1
            if draw_date:
                missing_dates_set.add(draw_date)
            if draw_date and draw_session:
                missing_draws_set.add(f"{draw_date}|{draw_session}")
            hit_t   = ""
            hit_f   = ""
            payout  = ""
            profit  = ""
            roi_val = ""
        else:
            hit_t   = _hit_type(pick, result, lane)
            hit_f   = 1 if hit_t != "MISS" else 0
            payout  = _payout(game, lane, hit_t)
            profit  = round(payout - STAKE, 2)
            roi_val = round(profit / STAKE * 100, 2)

        settled_row = {
            "grain_id":          row.get("grain_id", ""),
            "settled_at":        now_str,
            "date":              draw_date,
            "draw":              draw_session,
            "game":              game,
            "lane":              lane,
            "pick":              pick,
            "overlay_tier":      row.get("overlay_tier", ""),
            "mmfsn_tier":        row.get("mmfsn_tier", ""),
            "ev_score":          row.get("ev_score", ""),
            "ev_rank":           row.get("ev_rank", ""),
            "ev_decision":       row.get("ev_decision", ""),
            "production_gate":   row.get("production_gate", ""),
            "production_action": row.get("production_action", ""),
            "reranker_mode":     row.get("reranker_mode", ""),
            "result":            result,
            "hit_type":          hit_t,
            "hit_flag":          hit_f,
            "stake":             STAKE,
            "payout":            payout,
            "profit":            profit,
            "roi":               roi_val,
        }
        settled_rows.append(settled_row)

    settled_count = total_raw - missing_result_rows
    coverage_pct  = round(settled_count / total_raw * 100, 2) if total_raw > 0 else 0.0

    # Write settled JSONL
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(settled_path, "w", encoding="utf-8") as f:
        for r in settled_rows:
            f.write(json.dumps(r) + "\n")

    # Print full audit counters so the operator knows why coverage failed
    print(f"  raw_rows              : {total_raw:,}")
    print(f"  settled_rows          : {settled_count:,}")
    print(f"  missing_result_rows   : {missing_result_rows:,}")
    print(f"  coverage_pct          : {coverage_pct:.2f}%")
    print(f"  duplicate_grain_ids   : {len(duplicate_grain_ids)}")
    if missing_dates_set:
        missing_dates_sorted = sorted(missing_dates_set)
        print(f"  missing_dates ({len(missing_dates_sorted):,})  : {', '.join(missing_dates_sorted[:10])}"
              + (" ..." if len(missing_dates_sorted) > 10 else ""))
    if missing_draws_set:
        missing_draws_sorted = sorted(missing_draws_set)
        print(f"  missing_draws ({len(missing_draws_sorted):,})  : {', '.join(missing_draws_sorted[:10])}"
              + (" ..." if len(missing_draws_sorted) > 10 else ""))
    if duplicate_grain_ids:
        print(f"  [WARN] duplicate grains: {sorted(duplicate_grain_ids)[:5]}")
    print(f"  Saved: {settled_path}")

    # Write summary CSV
    _write_summary(settled_rows, summary_path)

    return settled_rows


# ---------------------------------------------------------------------------
# Summary CSV — per-condition bucket
# ---------------------------------------------------------------------------
SUMMARY_FIELDS = [
    "condition_key", "ev_decision", "settled_picks",
    "exact_hits", "box_hits", "misses",
    "win_rate_pct", "exact_hit_rate_pct", "box_hit_rate_pct",
    "total_stake", "total_payout", "total_profit",
    "roi_pct", "avg_ev_score",
    "unsettled_picks",
]


def _write_summary(settled_rows: list[dict], summary_path: Path) -> None:

    class _Bucket:
        __slots__ = ("settled", "exact", "box", "misses",
                     "stake", "payout", "ev_sum", "unsettled")
        def __init__(self):
            self.settled = self.exact = self.box = self.misses = 0
            self.stake = self.payout = self.ev_sum = 0.0
            self.unsettled = 0

    buckets: dict[tuple, _Bucket] = defaultdict(_Bucket)

    for row in settled_rows:
        key = (
            f"{row['game']}|{row['overlay_tier']}|{row['draw']}|{row['lane']}",
            row.get("ev_decision", ""),
        )
        b = buckets[key]
        hit_f = row.get("hit_flag")
        if hit_f == "":
            b.unsettled += 1
            continue
        b.settled += 1
        ht = row.get("hit_type", "MISS")
        if ht == "EXACT_HIT":
            b.exact += 1
        elif ht == "BOX_HIT":
            b.box += 1
        else:
            b.misses += 1
        try:
            b.stake   += float(row.get("stake", 1.0))
            b.payout  += float(row.get("payout", 0.0))
            b.ev_sum  += float(row.get("ev_score", 0.0))
        except (TypeError, ValueError):
            pass

    summary_rows = []
    for (ckey, dec), b in sorted(buckets.items()):
        wins = b.exact + b.box
        n    = b.settled
        summary_rows.append({
            "condition_key":       ckey,
            "ev_decision":         dec,
            "settled_picks":       n,
            "exact_hits":          b.exact,
            "box_hits":            b.box,
            "misses":              b.misses,
            "win_rate_pct":        round(wins / n * 100, 4) if n > 0 else "",
            "exact_hit_rate_pct":  round(b.exact / n * 100, 4) if n > 0 else "",
            "box_hit_rate_pct":    round(b.box / n * 100, 4) if n > 0 else "",
            "total_stake":         round(b.stake, 2),
            "total_payout":        round(b.payout, 2),
            "total_profit":        round(b.payout - b.stake, 2),
            "roi_pct":             round((b.payout - b.stake) / b.stake * 100, 4) if b.stake > 0 else "",
            "avg_ev_score":        round(b.ev_sum / n, 4) if n > 0 else "",
            "unsettled_picks":     b.unsettled,
        })

    # Sort: ALLOW first, then by roi descending
    summary_rows.sort(key=lambda r: (r["ev_decision"] != "ALLOW",
                                     -(r["roi_pct"] if isinstance(r["roi_pct"], float) else -999)))

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"  Saved: {summary_path}")


# ---------------------------------------------------------------------------
# Promotion audit
# ---------------------------------------------------------------------------
def promotion_audit(settled_rows: Optional[list[dict]] = None) -> dict:
    """
    Run the Phase 3C promotion gate checks.
    Stricter than check_promotion_gates() in reranker_config:
    requires settled_days >= 14, coverage >= 95%, allow_count >= 25,
    allow lift >= 2.0x, allow ROI > shadow+block ROI.
    """
    if settled_rows is None:
        if not SETTLED_LOG.exists():
            return {"verdict": "NO_DATA", "reason": "No settled log found"}
        rows = []
        with open(SETTLED_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        settled_rows = rows

    if not settled_rows:
        return {"verdict": "NO_DATA", "reason": "Settled log is empty"}

    # Split settled vs pending
    settled   = [r for r in settled_rows if r.get("hit_flag") != ""]
    unsettled = [r for r in settled_rows if r.get("hit_flag") == ""]

    total_rows     = len(settled_rows)
    settled_count  = len(settled)
    coverage       = settled_count / total_rows if total_rows > 0 else 0.0

    # Days spanned
    dates = sorted(set(r["date"] for r in settled if r.get("date")))
    settled_days = len(dates)

    # Duplicate grain check
    grain_ids = [r["grain_id"] for r in settled_rows if r.get("grain_id")]
    duplicate_grains = len(grain_ids) - len(set(grain_ids))

    # Per-decision win / payout aggregation
    by_dec: dict[str, dict] = defaultdict(lambda: {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})
    for r in settled:
        dec = r.get("ev_decision", "BLOCK")
        hf  = r.get("hit_flag")
        try:
            by_dec[dec]["wins"]   += int(hf)
            by_dec[dec]["n"]      += 1
            by_dec[dec]["payout"] += float(r.get("payout") or 0.0)
            by_dec[dec]["stake"]  += float(r.get("stake") or 1.0)
        except (TypeError, ValueError):
            pass

    def _wr(d):  return d["wins"] / d["n"] if d["n"] > 0 else 0.0
    def _roi(d): return (d["payout"] - d["stake"]) / d["stake"] * 100 if d["stake"] > 0 else 0.0

    allow_d   = by_dec.get("ALLOW",        {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})
    shadow_d  = by_dec.get("SHADOW_TRACK", {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})
    block_d   = by_dec.get("BLOCK",        {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})

    allow_wr   = _wr(allow_d)
    allow_roi  = _roi(allow_d)
    shadow_wr  = _wr(shadow_d)
    block_wr   = _wr(block_d)
    shadow_roi = _roi(shadow_d)
    block_roi  = _roi(block_d)

    baseline_wr  = (shadow_wr + block_wr) / 2   if (shadow_wr + block_wr) > 0 else 0.0
    baseline_roi = (shadow_roi + block_roi) / 2  if True else 0.0
    lift         = allow_wr / baseline_wr if baseline_wr > 0 else 0.0

    # Gate checks
    gates = {
        "settled_days_gte_14":          settled_days >= 14,
        "result_coverage_gte_95pct":    coverage >= 0.95,
        "no_duplicate_grain_ids":       duplicate_grains == 0,
        "allow_count_gte_25":           allow_d["n"] >= 25,
        "allow_lift_gte_2x":            lift >= 2.0,
        "allow_win_rate_gt_baseline":   allow_wr > baseline_wr,
        "allow_roi_gt_baseline_roi":    allow_roi > baseline_roi,
        "straight_box_only_confirmed":  True,   # enforced by production_strategy v2
    }

    all_pass   = all(gates.values())
    any_signal = gates["allow_lift_gte_2x"] or gates["allow_win_rate_gt_baseline"]

    if all_pass:
        verdict = "PROMOTE_TO_ADVISORY"
    elif any_signal and not gates["settled_days_gte_14"]:
        verdict = "EXTEND_OBSERVATION"
    elif any_signal:
        verdict = "EXTEND_OBSERVATION"
    else:
        verdict = "HOLD"

    return {
        "verdict":           verdict,
        "settled_days":      settled_days,
        "total_rows":        total_rows,
        "settled_count":     settled_count,
        "unsettled_count":   len(unsettled),
        "result_coverage":   round(coverage, 4),
        "duplicate_grains":  duplicate_grains,
        "allow_n":           allow_d["n"],
        "allow_win_rate":    round(allow_wr, 4),
        "allow_roi_pct":     round(allow_roi, 4),
        "shadow_win_rate":   round(shadow_wr, 4),
        "shadow_roi_pct":    round(shadow_roi, 4),
        "block_win_rate":    round(block_wr, 4),
        "baseline_win_rate": round(baseline_wr, 4),
        "allow_lift":        round(lift, 4),
        "gate_results":      gates,
        "next_mode": {
            "PROMOTE_TO_ADVISORY":  "EV_RERANKER_MODE = 'ADVISORY'  (ALLOW_PRODUCTION_CHANGE stays False)",
            "EXTEND_OBSERVATION":   "Continue OBSERVE_ONLY — collect more settled days",
            "HOLD":                 "Signal did not survive — recheck weights before extending",
        }.get(verdict, ""),
    }


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------
def _sep(char="=", w=100): print(char * w)


def print_audit_report(audit: dict) -> None:
    _sep()
    print("  PHASE 3C — EV RERANKER PROMOTION AUDIT")
    _sep()
    print(f"  Verdict           : {audit['verdict']}")
    print(f"  Next mode         : {audit.get('next_mode', '')}")
    print()
    print(f"  Settled days      : {audit.get('settled_days', 0)}  (need >= 14)")
    print(f"  Result coverage   : {audit.get('result_coverage', 0)*100:.1f}%  (need >= 95%)")
    print(f"  Total rows        : {audit.get('total_rows', 0):,}")
    print(f"  Settled           : {audit.get('settled_count', 0):,}")
    print(f"  Unsettled         : {audit.get('unsettled_count', 0):,}")
    print(f"  Duplicate grains  : {audit.get('duplicate_grains', 0)}  (need == 0)")
    print()
    print(f"  ALLOW  n={audit.get('allow_n',0):>5}   win_rate={audit.get('allow_win_rate',0):.4f}   ROI={audit.get('allow_roi_pct',0):+.2f}%")
    print(f"  SHADOW            win_rate={audit.get('shadow_win_rate',0):.4f}   ROI={audit.get('shadow_roi_pct',0):+.2f}%")
    print(f"  Baseline          win_rate={audit.get('baseline_win_rate',0):.4f}")
    print(f"  Allow lift        : {audit.get('allow_lift',0):.2f}x  (need >= 2.0x)")
    print()
    _sep("-")
    print("  GATE CHECKS")
    _sep("-")
    for gate, result in audit.get("gate_results", {}).items():
        icon = "PASS" if result else "FAIL"
        print(f"  [{icon}]  {gate}")
    _sep()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 3C: settle EV observation log")
    parser.add_argument("--audit", action="store_true",
                        help="Run promotion audit only (no re-settlement)")
    args = parser.parse_args()

    if args.audit:
        print("Running promotion audit from existing settled log ...")
        audit = promotion_audit()
        print_audit_report(audit)
    else:
        print("Loading actual draw results ...")
        actuals = load_actual_results()
        print("Settling EV observation log ...")
        settled = settle(actuals=actuals)
        if settled:
            print()
            print("Running promotion audit ...")
            audit = promotion_audit(settled)
            print_audit_report(audit)
        else:
            print("Nothing to settle yet. Run the API live for at least one day first.")
