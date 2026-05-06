#!/usr/bin/env python3
"""
ev_observe_status.py

Phase 3D: Live Observation Runbook + Drift Monitor

Reads:
- data/ev_observe/ev_observe_log.jsonl
- data/ev_observe/ev_observe_log.settled.jsonl

Prints:
- observation days collected
- rows logged
- rows settled
- coverage %
- ALLOW count
- ALLOW win %
- baseline win %
- ALLOW lift
- ALLOW ROI
- baseline ROI
- duplicate grain count
- current verdict
- next mode

This file is read-only. It does not mutate raw or settled logs.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_OBSERVE_DIR = Path("data/ev_observe")
DEFAULT_RAW_LOG = DEFAULT_OBSERVE_DIR / "ev_observe_log.jsonl"
DEFAULT_SETTLED_LOG = DEFAULT_OBSERVE_DIR / "ev_observe_log.settled.jsonl"


@dataclass
class BucketStats:
    rows: int = 0
    hits: int = 0
    stake: float = 0.0
    payout: float = 0.0
    profit: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.hits / self.rows if self.rows else 0.0

    @property
    def roi(self) -> float:
        return self.profit / self.stake if self.stake else 0.0


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({
                    "_parse_error": True,
                    "_line_no": line_no,
                    "_raw": line,
                })

    return rows


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_day(row: Dict[str, Any]) -> Optional[str]:
    value = row.get("date") or row.get("draw_date") or row.get("created_date")
    if not value:
        return None

    value = str(value)
    return value[:10]


def _grain_id(row: Dict[str, Any]) -> Optional[str]:
    return row.get("grain_id")


def _is_settled(row: Dict[str, Any]) -> bool:
    if row.get("_parse_error"):
        return False

    if "hit_flag" not in row:
        return False

    if row.get("result") in (None, "", "UNKNOWN"):
        return False

    return True


def _is_allow(row: Dict[str, Any]) -> bool:
    return str(row.get("ev_decision", "")).upper() == "ALLOW"


def _is_baseline(row: Dict[str, Any]) -> bool:
    decision = str(row.get("ev_decision", "")).upper()
    return decision in {"SHADOW_TRACK", "BLOCK"}


def _bucket_stats(rows: Iterable[Dict[str, Any]]) -> BucketStats:
    stats = BucketStats()

    for row in rows:
        if not _is_settled(row):
            continue

        stats.rows += 1
        stats.hits += 1 if bool(row.get("hit_flag")) else 0
        stats.stake += _safe_float(row.get("stake"), 0.0)
        stats.payout += _safe_float(row.get("payout"), 0.0)

        if "profit" in row:
            stats.profit += _safe_float(row.get("profit"), 0.0)
        else:
            stats.profit += _safe_float(row.get("payout"), 0.0) - _safe_float(row.get("stake"), 0.0)

    return stats


def _count_duplicates(rows: Iterable[Dict[str, Any]]) -> int:
    grain_ids = [_grain_id(row) for row in rows if _grain_id(row)]
    counts = Counter(grain_ids)
    return sum(count - 1 for count in counts.values() if count > 1)


def _missing_result_summary(raw_rows: List[Dict[str, Any]], settled_rows: List[Dict[str, Any]]) -> Tuple[int, List[str], List[str]]:
    settled_grains = {
        _grain_id(row)
        for row in settled_rows
        if _grain_id(row) and _is_settled(row)
    }

    missing_rows = []
    missing_dates = set()
    missing_draws = set()

    for row in raw_rows:
        gid = _grain_id(row)
        if not gid:
            continue

        if gid not in settled_grains:
            missing_rows.append(row)

            day = _extract_day(row)
            if day:
                missing_dates.add(day)

            draw = row.get("draw")
            if draw:
                missing_draws.add(str(draw).upper())

    return len(missing_rows), sorted(missing_dates), sorted(missing_draws)


def _try_promotion_audit() -> Dict[str, Any]:
    try:
        from settle_ev_log import promotion_audit  # type: ignore

        verdict = promotion_audit()

        if isinstance(verdict, dict):
            return verdict

        return {
            "verdict": str(verdict),
            "next_mode": "UNKNOWN",
            "source": "settle_ev_log.promotion_audit",
        }

    except Exception as exc:
        return {
            "verdict": "UNKNOWN",
            "next_mode": "UNKNOWN",
            "audit_error": str(exc),
        }


def build_status(raw_log: Path, settled_log: Path) -> Dict[str, Any]:
    raw_rows = _read_jsonl(raw_log)
    settled_rows = _read_jsonl(settled_log)

    raw_parse_errors = sum(1 for row in raw_rows if row.get("_parse_error"))
    settled_parse_errors = sum(1 for row in settled_rows if row.get("_parse_error"))

    settled_valid_rows = [row for row in settled_rows if _is_settled(row)]

    raw_days = sorted({
        day for row in raw_rows
        if (day := _extract_day(row))
    })

    settled_days = sorted({
        day for row in settled_valid_rows
        if (day := _extract_day(row))
    })

    raw_rows_count = len([row for row in raw_rows if not row.get("_parse_error")])
    settled_rows_count = len(settled_valid_rows)

    coverage_pct = (
        settled_rows_count / raw_rows_count
        if raw_rows_count
        else 0.0
    )

    allow_rows = [row for row in settled_valid_rows if _is_allow(row)]
    baseline_rows = [row for row in settled_valid_rows if _is_baseline(row)]

    allow_stats = _bucket_stats(allow_rows)
    baseline_stats = _bucket_stats(baseline_rows)

    allow_lift = (
        allow_stats.win_rate / baseline_stats.win_rate
        if baseline_stats.win_rate > 0
        else 0.0
    )

    raw_duplicate_grains = _count_duplicates(raw_rows)
    settled_duplicate_grains = _count_duplicates(settled_rows)

    missing_result_rows, missing_dates, missing_draws = _missing_result_summary(raw_rows, settled_rows)

    audit = _try_promotion_audit()

    return {
        "raw_log": str(raw_log),
        "settled_log": str(settled_log),

        "observation_days_collected": len(raw_days),
        "settled_days_collected": len(settled_days),

        "raw_rows": raw_rows_count,
        "settled_rows": settled_rows_count,
        "missing_result_rows": missing_result_rows,
        "coverage_pct": coverage_pct,

        "missing_dates": missing_dates,
        "missing_draws": missing_draws,

        "raw_duplicate_grain_count": raw_duplicate_grains,
        "settled_duplicate_grain_count": settled_duplicate_grains,

        "raw_parse_errors": raw_parse_errors,
        "settled_parse_errors": settled_parse_errors,

        "allow_count": allow_stats.rows,
        "allow_hits": allow_stats.hits,
        "allow_win_rate": allow_stats.win_rate,
        "allow_roi": allow_stats.roi,

        "baseline_count": baseline_stats.rows,
        "baseline_hits": baseline_stats.hits,
        "baseline_win_rate": baseline_stats.win_rate,
        "baseline_roi": baseline_stats.roi,

        "allow_lift": allow_lift,

        "current_verdict": audit.get("verdict", "UNKNOWN"),
        "next_mode": audit.get("next_mode", "UNKNOWN"),
        "promotion_audit": audit,
    }


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def print_status(status: Dict[str, Any]) -> None:
    print("")
    print("EV OBSERVATION STATUS")
    print("=" * 60)

    print(f"Observation days collected : {status['observation_days_collected']}")
    print(f"Settled days collected     : {status['settled_days_collected']}")
    print(f"Rows logged                : {status['raw_rows']}")
    print(f"Rows settled               : {status['settled_rows']}")
    print(f"Coverage                   : {_pct(status['coverage_pct'])}")
    print(f"Missing result rows        : {status['missing_result_rows']}")
    print(f"Duplicate grain count      : {status['raw_duplicate_grain_count']} raw / {status['settled_duplicate_grain_count']} settled")

    print("")
    print("ALLOW BUCKET")
    print("-" * 60)
    print(f"ALLOW count                : {status['allow_count']}")
    print(f"ALLOW hits                 : {status['allow_hits']}")
    print(f"ALLOW win %                : {_pct(status['allow_win_rate'])}")
    print(f"ALLOW ROI                  : {_pct(status['allow_roi'])}")

    print("")
    print("BASELINE BUCKET: SHADOW_TRACK + BLOCK")
    print("-" * 60)
    print(f"Baseline count             : {status['baseline_count']}")
    print(f"Baseline hits              : {status['baseline_hits']}")
    print(f"Baseline win %             : {_pct(status['baseline_win_rate'])}")
    print(f"Baseline ROI               : {_pct(status['baseline_roi'])}")

    print("")
    print("SEPARATION")
    print("-" * 60)
    print(f"ALLOW lift                 : {status['allow_lift']:.2f}x")
    print(f"Current verdict            : {status['current_verdict']}")
    print(f"Next mode                  : {status['next_mode']}")

    if status["missing_dates"]:
        print("")
        print("MISSING DATES")
        print("-" * 60)
        for day in status["missing_dates"][:20]:
            print(f"- {day}")
        if len(status["missing_dates"]) > 20:
            print(f"... plus {len(status['missing_dates']) - 20} more")

    if status["missing_draws"]:
        print("")
        print("MISSING DRAWS")
        print("-" * 60)
        for draw in status["missing_draws"]:
            print(f"- {draw}")

    if status["raw_parse_errors"] or status["settled_parse_errors"]:
        print("")
        print("PARSE WARNINGS")
        print("-" * 60)
        print(f"Raw parse errors           : {status['raw_parse_errors']}")
        print(f"Settled parse errors       : {status['settled_parse_errors']}")

    audit_error = status.get("promotion_audit", {}).get("audit_error")
    if audit_error:
        print("")
        print("PROMOTION AUDIT WARNING")
        print("-" * 60)
        print(audit_error)

    print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3D EV observation status monitor")
    parser.add_argument("--raw-log", default=str(DEFAULT_RAW_LOG), help="Path to raw EV observation JSONL")
    parser.add_argument("--settled-log", default=str(DEFAULT_SETTLED_LOG), help="Path to settled EV observation JSONL")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    raw_log = Path(args.raw_log)
    settled_log = Path(args.settled_log)

    status = build_status(raw_log=raw_log, settled_log=settled_log)

    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print_status(status)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
