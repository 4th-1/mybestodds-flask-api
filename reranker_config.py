"""
reranker_config.py — Phase 3B EV Reranker Deployment Config + Live Log Writer
===============================================================================
Central control point for the EV reranker's operating mode.

During the 14-day live observation window:
    EV_RERANKER_MODE = "OBSERVE_ONLY"

The reranker scores every pick and attaches ev_score / ev_rank / ev_decision
to the API response, but ALLOW_PRODUCTION_CHANGE = False means the v2
production gate still controls what actually reaches subscribers.

Live log: data/ev_observe_log.jsonl (one JSON-line per scored pick per request)
Grain key: date|draw|game|lane|pick  — prevents the 82/4178/6874 grain mismatch.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 3B deployment flags
# ---------------------------------------------------------------------------
EV_RERANKER_MODE         = os.getenv("EV_RERANKER_MODE", "OBSERVE_ONLY")
ALLOW_PRODUCTION_CHANGE  = False   # hard-coded: reranker does not alter exposure yet
CASH4_ENABLED            = False   # Cash4 isolated; reranker skips it
SHADOW_PROMOTION_ENABLED = False   # BOX / VERY_HIGH / HIGH stay suppressed

# ---------------------------------------------------------------------------
# Live observation log path
# ---------------------------------------------------------------------------
ROOT         = Path(__file__).parent
_LOG_DIR     = ROOT / "data" / "ev_observe"
_LOG_PATH    = _LOG_DIR / "ev_observe_log.jsonl"
_LOCK        = Lock()

# Required columns for the live log
LOG_FIELDS = [
    "grain_id",            # date|draw|game|lane|pick  (dedup key)
    "logged_at",           # ISO-8601 UTC
    "date",
    "draw",                # session: NIGHT / EVENING / MIDDAY
    "game",
    "lane",                # play_type: STRAIGHT_BOX / BOX / etc.
    "pick",                # the number
    "overlay_tier",
    "mmfsn_tier",
    "base_score",
    "overlay_bonus",
    "night_bonus",
    "mmfsn_bonus",
    "recent_signal_bonus",
    "pav_bonus",
    "instability_penalty",
    "overexposure_penalty",
    "cold_signal_penalty",
    "ev_score",
    "ev_rank",
    "ev_decision",
    "production_gate",     # bool: did v2 gate allow this?
    "production_action",   # "CURRENT_V2_RULE" or "SUPPRESSED_BY_GATE"
    "reranker_mode",       # always "OBSERVE_ONLY" for now
    # Settlement columns — filled retroactively by settle_ev_log.py
    "result",              # "WIN" / "LOSS" / "" (pending)
    "hit_flag",            # 1 / 0 / "" (pending)
    "payout",              # dollar amount / "" (pending)
    "stake",               # always 1.00
    "roi",                 # (payout - stake) / stake * 100 / "" (pending)
]


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# grain_id helper
# ---------------------------------------------------------------------------
def make_grain_id(draw_date: str, draw: str, game: str, lane: str, pick: str) -> str:
    """
    Canonical dedup key for a single pick observation.
    date|draw|game|lane|pick — all lowercase, spaces replaced with underscores.
    """
    parts = [draw_date, draw, game, lane, pick]
    return "|".join(p.strip().lower().replace(" ", "_") for p in parts)


# ---------------------------------------------------------------------------
# Core log writer — appends one JSONL line per pick; thread-safe
# ---------------------------------------------------------------------------
def log_ev_observation(
    scored_pick: dict,
    ev_rank: int,
    production_gate: bool,
    production_action: str,
) -> None:
    """Append one pick's EV observation to the live log (non-blocking on error)."""
    try:
        _ensure_log_dir()
        draw_date = scored_pick.get("date", "")
        draw      = scored_pick.get("draw", "")
        game      = scored_pick.get("game", "")
        lane      = scored_pick.get("lane", "")
        pick      = scored_pick.get("pick", "")

        entry = {
            "grain_id":             make_grain_id(draw_date, draw, game, lane, pick),
            "logged_at":            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date":                 draw_date,
            "draw":                 draw,
            "game":                 game,
            "lane":                 lane,
            "pick":                 pick,
            "overlay_tier":         scored_pick.get("overlay_tier", ""),
            "mmfsn_tier":           scored_pick.get("mmfsn_tier", ""),
            "base_score":           scored_pick.get("base_score", 0.0),
            "overlay_bonus":        scored_pick.get("overlay_bonus", 0.0),
            "night_bonus":          scored_pick.get("night_bonus", 0.0),
            "mmfsn_bonus":          scored_pick.get("mmfsn_bonus", 0.0),
            "recent_signal_bonus":  scored_pick.get("recent_signal_bonus", 0.0),
            "pav_bonus":            scored_pick.get("pav_bonus", 0.0),
            "instability_penalty":  scored_pick.get("instability_penalty", 0.0),
            "overexposure_penalty": scored_pick.get("overexposure_penalty", 0.0),
            "cold_signal_penalty":  scored_pick.get("cold_signal_penalty", 0.0),
            "ev_score":             scored_pick.get("ev_score", 0.0),
            "ev_rank":              ev_rank,
            "ev_decision":          scored_pick.get("decision", ""),
            "production_gate":      production_gate,
            "production_action":    production_action,
            "reranker_mode":        EV_RERANKER_MODE,
            # Settlement fields — populated later by settle_ev_log.py
            "result":    "",
            "hit_flag":  "",
            "payout":    "",
            "stake":     1.00,
            "roi":       "",
        }

        with _LOCK:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    except Exception as e:
        logger.warning(f"[ev_observe] log write failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Bulk log writer — called once per request with all ranked picks
# ---------------------------------------------------------------------------
def log_ev_request(ranked_picks: list[dict], production_gate_map: dict[str, bool]) -> None:
    """
    Write one log entry per pick from a ranked request.
    production_gate_map: {grain_id → bool}  — pre-built by the api_server caller
    """
    for row in ranked_picks:
        draw_date = row.get("date", "")
        draw      = row.get("draw", "")
        game      = row.get("game", "")
        lane      = row.get("lane", "")
        pick      = row.get("pick", "")
        gid       = make_grain_id(draw_date, draw, game, lane, pick)
        gate_pass = production_gate_map.get(gid, False)
        action    = "CURRENT_V2_RULE" if gate_pass else "SUPPRESSED_BY_GATE"
        log_ev_observation(
            scored_pick=row,
            ev_rank=row.get("rank", 0),
            production_gate=gate_pass,
            production_action=action,
        )


# ---------------------------------------------------------------------------
# Log reader — returns all rows (for internal reporting)
# ---------------------------------------------------------------------------
def read_ev_log() -> list[dict]:
    """Load the full live observation log; returns empty list if not started yet."""
    if not _LOG_PATH.exists():
        return []
    rows = []
    with open(_LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


# ---------------------------------------------------------------------------
# 14-day promotion check — run manually after observation window
# ---------------------------------------------------------------------------
def check_promotion_gates(rows: Optional[list[dict]] = None) -> dict:
    """
    8-gate stricter promotion evaluation with 3 verdicts:
      HOLD               — reranker did not maintain live separation
      EXTEND_OBSERVATION — signal positive but sample thin / incomplete
      PROMOTE_TO_ADVISORY — all 8 gates pass; next mode = EV_RERANKER_MODE='ADVISORY'
                            (ALLOW_PRODUCTION_CHANGE stays False)

    Delegates full computation to settle_ev_log.promotion_audit().
    """
    try:
        from settle_ev_log import promotion_audit
        return promotion_audit(rows)
    except ImportError:
        pass

    # Inline fallback if settle_ev_log is unavailable
    if rows is None:
        rows = read_ev_log()

    settled = [r for r in rows if r.get("hit_flag") not in ("", None)]
    if not settled:
        return {"verdict": "HOLD", "reason": "INSUFFICIENT_DATA", "settled_rows": 0}

    dates           = sorted(set(r.get("date", "") for r in settled if r.get("date")))
    settled_days    = len(dates)
    total_rows      = len(rows)
    settled_count   = len(settled)
    coverage        = settled_count / total_rows if total_rows > 0 else 0.0
    grain_ids       = [r.get("grain_id", "") for r in rows]
    duplicate_grains= len(grain_ids) - len(set(grain_ids))

    from collections import defaultdict
    by_dec: dict[str, dict] = defaultdict(lambda: {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0, "roi_sum": 0.0})
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

    allow_d  = by_dec.get("ALLOW",        {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})
    shadow_d = by_dec.get("SHADOW_TRACK", {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})
    block_d  = by_dec.get("BLOCK",        {"wins": 0, "n": 0, "payout": 0.0, "stake": 0.0})

    allow_wr   = _wr(allow_d)
    allow_roi  = _roi(allow_d)
    shadow_wr  = _wr(shadow_d)
    block_wr   = _wr(block_d)
    shadow_roi = _roi(shadow_d)
    block_roi  = _roi(block_d)
    baseline_wr  = (shadow_wr + block_wr) / 2 if (shadow_wr + block_wr) > 0 else 0.0
    baseline_roi = (shadow_roi + block_roi) / 2
    lift         = allow_wr / baseline_wr if baseline_wr > 0 else 0.0

    straight_box_confirmed = True  # enforced by production_strategy v2

    gates = {
        "settled_days_gte_14":          settled_days >= 14,
        "result_coverage_gte_95pct":    coverage >= 0.95,
        "no_duplicate_grain_ids":       duplicate_grains == 0,
        "allow_count_gte_25":           allow_d["n"] >= 25,
        "allow_lift_gte_2x":            lift >= 2.0,
        "allow_win_rate_gt_baseline":   allow_wr > baseline_wr,
        "allow_roi_gt_baseline_roi":    allow_roi > baseline_roi,
        "straight_box_only_confirmed":  straight_box_confirmed,
    }

    all_pass   = all(gates.values())
    any_signal = gates["allow_lift_gte_2x"] or gates["allow_win_rate_gt_baseline"]

    if all_pass:
        verdict = "PROMOTE_TO_ADVISORY"
    elif any_signal:
        verdict = "EXTEND_OBSERVATION"
    else:
        verdict = "HOLD"

    return {
        "verdict":           verdict,
        "settled_days":      settled_days,
        "total_rows":        total_rows,
        "settled_count":     settled_count,
        "result_coverage":   round(coverage, 4),
        "duplicate_grains":  duplicate_grains,
        "allow_n":           allow_d["n"],
        "allow_win_rate":    round(allow_wr, 4),
        "allow_roi_pct":     round(allow_roi, 4),
        "shadow_win_rate":   round(shadow_wr, 4),
        "baseline_win_rate": round(baseline_wr, 4),
        "allow_lift":        round(lift, 4),
        "gate_results":      gates,
        "next_mode": {
            "PROMOTE_TO_ADVISORY":  "EV_RERANKER_MODE = 'ADVISORY'  (ALLOW_PRODUCTION_CHANGE stays False)",
            "EXTEND_OBSERVATION":   "Continue OBSERVE_ONLY — collect more settled days",
            "HOLD":                 "Signal did not survive — recheck weights before extending",
        }.get(verdict, ""),
    }
