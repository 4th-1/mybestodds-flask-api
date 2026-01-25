#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
My Best Odds — v3.5 → v3.7 Forecast Upgrader (Option C)

Purpose:
    - Take a v3.5 / v3.6 BOOK / BOOK3 / BOSK forecast JSON
      (lane-based structure with fields like `value`, `pick_type`, `main`, `bonus`,
       plus overlay fields like `play_flag`, `legend`, `sum`, etc.)
    - Convert each row into a clean v3.7 Option-C compatible row with:

        game
        draw_date
        draw_time
        pick
        play_type
        confidence_score
        win_odds_1_in
        sum
        legend_code
        play_flag

    - Keep kit + subscriber_id for tracing.

Usage:
    python upgrade_forecast_to_v3_7.py input_v3_5.json output_v3_7.json
"""

import json
import sys
import re
from typing import Any, Dict, List


# ------------------------
# Helper functions
# ------------------------

CASH3_HINTS = {"cash3", "cash 3"}
CASH4_HINTS = {"cash4", "cash 4"}


def looks_like_cash3(game: str) -> bool:
    if not isinstance(game, str):
        return False
    g = game.lower()
    return any(h in g for h in CASH3_HINTS)


def looks_like_cash4(game: str) -> bool:
    if not isinstance(game, str):
        return False
    g = game.lower()
    return any(h in g for h in CASH4_HINTS)


def compute_digit_sum_from_pick(pick: str) -> int:
    digits = re.findall(r"\d", pick or "")
    return sum(int(d) for d in digits) if digits else 0


def compute_digit_sum_from_main_bonus(main: List[Any], bonus: List[Any]) -> int:
    total = 0
    for x in main or []:
        try:
            total += int(x)
        except (ValueError, TypeError):
            continue
    for x in bonus or []:
        try:
            total += int(x)
        except (ValueError, TypeError):
            continue
    return total


def parse_best_odds(best_odds: Any) -> int:
    """
    best_odds examples: "1 in 50", "1 in 62", maybe already just "50".
    Return integer 0 if unknown.
    """
    if best_odds is None:
        return 0
    s = str(best_odds).strip()
    m = re.search(r"1\\s*in\\s*(\\d+)", s, flags=re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    # fallback: try to parse the whole thing as int
    try:
        return int(s)
    except ValueError:
        return 0


def normalize_confidence(old: Dict[str, Any]) -> float:
    """
    Normalize confidence to 0–1 scale.

    - Prefer `confidence` if present (usually 0–1)
    - Else use `confidence_percent` / 100 if present.
    """
    raw = old.get("confidence", None)
    if raw in (None, ""):
        raw = old.get("confidence_percent", None)

    if raw in (None, ""):
        return 0.0

    try:
        c = float(raw)
    except (ValueError, TypeError):
        return 0.0

    # If it looks like a percent (e.g., 2.0 == 2%), convert to 0.02
    if c > 1.1:
        return round(c / 100.0, 6)
    return round(c, 6)


def classify_play_flag_from_conf(conf_0_1: float) -> str:
    """
    Fallback play_flag rules on 0–1 confidence:

      - PLAY  : conf >= 0.033
      - WATCH : 0.020 <= conf < 0.033
      - HOLD  : 0.010 <= conf < 0.020
      - SKIP  : conf < 0.010
    """
    c = conf_0_1
    if c >= 0.033:
        return "PLAY"
    if c >= 0.020:
        return "WATCH"
    if c >= 0.010:
        return "HOLD"
    return "SKIP"


def choose_play_flag(old: Dict[str, Any], conf_0_1: float) -> str:
    """
    Prefer existing engine decision (old['play_flag']) if present.
    Otherwise, derive from confidence.
    """
    pf = (old.get("play_flag") or "").strip().upper()
    if pf in {"PLAY", "WATCH", "HOLD", "SKIP"}:
        return pf
    return classify_play_flag_from_conf(conf_0_1)


def choose_legend_code(old: Dict[str, Any], play_flag: str) -> str:
    """
    Simple stable legend code.

    - If old row has a short code in `legend_code`, use it.
    - Else if `legend` exists, we keep its text in `legend_code` for now.
    - Else, map from play_flag.
    """
    # If there was already a legend_code, keep it
    if "legend_code" in old and old["legend_code"]:
        return str(old["legend_code"])

    # If there is full legend text, we can keep it for now
    if "legend" in old and old["legend"]:
        return str(old["legend"])

    pf = play_flag.upper()
    if pf == "PLAY":
        return "PLAY_STRONG"
    if pf == "WATCH":
        return "WATCH_WINDOW"
    if pf == "HOLD":
        return "HOLD_PATTERN"
    if pf == "SKIP":
        return "SKIP_LOW_CONF"
    return "GENERIC"


def build_pick_string(old: Dict[str, Any]) -> str:
    """
    Build a human pick string.

    - For Cash3 / Cash4: use `value` or `number`
    - For jackpot games: "d1-d2-d3-d4-d5 + b1" from main + bonus
    """
    value = old.get("value")
    number = old.get("number")
    main = old.get("main") or []
    bonus = old.get("bonus") or []

    # Prefer explicit single-string value
    if value not in (None, ""):
        return str(value)
    if number not in (None, ""):
        return str(number)

    # Otherwise join main / bonus
    if main:
        main_str = "-".join(str(x) for x in main)
        if bonus:
            return f"{main_str} + {bonus[0]}"
        return main_str

    # Fallback empty
    return ""


def transform_record(old: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert one v3.5/v3.6 lane-style row → v3.7 Option-C record.
    We assume the input looks like:

        {
          "kit": "BOOK3",
          "subscriber_id": "JDS_BOOK3",
          "game": "Cash3",
          "draw_date": "2025-12-05",
          "session": "Midday",
          "pick_type": "pick",
          "value": "822",
          "main": [],
          "bonus": [],
          "confidence": 0.02,
          "best_odds": "1 in 50",
          "confidence_band": "🟩",
          "lane_sources": ["P_A"],
          "date": "",
          "draw_time": "",
          "number": "",
          "play_type": "STRAIGHT",
          "confidence_percent": 2.0,
          "signal_a": "CORE",
          "signal_b": "",
          "bob_20": "",
          "trend_arrow": "➡️",
          "digit_energy": "MED",
          "pattern_strength": "MED",
          "sum": 0,
          "sum_range": "Low Sum",
          "play_flag": "SKIP",
          "legend": "as STRAIGHT | ...",
          ...
        }
    """
    kit = old.get("kit", "")
    subscriber_id = old.get("subscriber_id", "")

    game = old.get("game", "")
    draw_date = old.get("draw_date", "") or old.get("date", "")
    draw_time = old.get("session") or old.get("draw_time") or "All"

    pick = build_pick_string(old)

    # Play type: use existing text if present, fallback by game
    play_type_raw = old.get("play_type") or old.get("pick_type") or ""
    play_type = str(play_type_raw).strip()
    if not play_type:
        g_lower = game.lower()
        if looks_like_cash3(g_lower) or looks_like_cash4(g_lower):
            play_type = "STRAIGHT"
        else:
            play_type = "STANDARD"

    # Confidence + odds
    conf_0_1 = normalize_confidence(old)
    best_odds = old.get("best_odds", "")
    win_odds_1_in = parse_best_odds(best_odds)

    # Play flag: prefer engine decision
    play_flag = choose_play_flag(old, conf_0_1)

    # SUM
    g_lower = game.lower()
    if looks_like_cash3(g_lower) or looks_like_cash4(g_lower):
        sum_val = compute_digit_sum_from_pick(pick)
    else:
        main = old.get("main") or []
        bonus = old.get("bonus") or []
        sum_val = compute_digit_sum_from_main_bonus(main, bonus)

    # Legend code
    legend_code = choose_legend_code(old, play_flag)

    # Build final v3.7 record (Option-C fields + trace)
    new_row: Dict[str, Any] = {
        # trace
        "kit_type": kit,
        "subscriber_id": subscriber_id,

        # required Option-C logical fields
        "game": game,
        "draw_date": draw_date,
        "draw_time": draw_time,
        "pick": pick,
        "play_type": play_type,
        "confidence_score": conf_0_1,
        "win_odds_1_in": win_odds_1_in,
        "sum": sum_val,
        "legend_code": legend_code,
        "play_flag": play_flag,

        # optional carry-over (for debugging / dashboards)
        "confidence_band": old.get("confidence_band", ""),
        "lane_sources": old.get("lane_sources", []),
        "best_odds_raw": best_odds,
    }

    return new_row


def load_rows(path: str) -> List[Dict[str, Any]]:
    """
    Load v3.5 forecast rows from JSON.

    Supports:
      - Top-level list
      - { "rows": [...] }
      - { "forecast": [...] }
      - { "data": [...] }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("rows", "forecast", "forecast_rows", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]

    # If we get here, nothing matched
    return []


# ------------------------
# Main CLI
# ------------------------

def main(argv: List[str]) -> None:
    if len(argv) < 3:
        print("Usage:")
        print("  python upgrade_forecast_to_v3_7.py input_v3_5.json output_v3_7.json")
        sys.exit(1)

    in_path = argv[1]
    out_path = argv[2]

    print(f"[UPGRADE] Loading v3.5/v3.6 forecast: {in_path}")
    rows_v3_5 = load_rows(in_path)
    print(f"[UPGRADE] Rows loaded: {len(rows_v3_5)}")

    upgraded_rows: List[Dict[str, Any]] = []
    for r in rows_v3_5:
        if not isinstance(r, dict):
            continue
        upgraded_rows.append(transform_record(r))

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(upgraded_rows, f, indent=2)

    print(f"[UPGRADE] Wrote v3.7-compatible forecast: {out_path}")
    print("         (All required Option C fields created: game, draw_date, draw_time, pick,")
    print("          play_type, confidence_score, win_odds_1_in, sum, legend_code, play_flag)")


if __name__ == "__main__":
    main(sys.argv)
