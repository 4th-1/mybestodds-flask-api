# -*- coding: utf-8 -*-
"""
left_builder_v3_7.py  
Creates Option-C compliant rows for SENTRY v3.7 & Excel v3.7

Takes v3.5 lane output and produces standardized fields:
    game, draw_date, draw_time, pick, play_type,
    confidence_score, win_odds_1_in, sum, legend_code, play_flag
"""

import re
from datetime import datetime

def digit_sum(val):
    s = str(val)
    digits = re.findall(r"\d", s)
    return sum(int(d) for d in digits) if digits else None

def normalize_draw_time(session):
    if not session:
        return ""
    s = session.lower()
    if "mid" in s: return "Midday"
    if "eve" in s: return "Evening"
    if "night" in s: return "Night"
    return session

def normalize_game(game):
    if not isinstance(game, str):
        return ""
    g = game.lower()
    if "cash3" in g or "cash 3" in g: return "Cash3"
    if "cash4" in g or "cash 4" in g: return "Cash4"
    if "mega" in g: return "MegaMillions"
    if "power" in g: return "Powerball"
    if "life" in g: return "Cash4Life"
    return game

def build_row_v3_7(lane_row, subscriber_id, kit_type):
    """
    Convert a v3.5 lane row → v3.7 strict format.
    lane_row keys expected:
        "game","draw_date","session","pick","confidence","best_odds","lane_sources"
    """

    game = normalize_game(lane_row.get("game", ""))
    draw_date = lane_row.get("draw_date", "")
    draw_time = normalize_draw_time(lane_row.get("session", ""))
    pick = lane_row.get("value") or lane_row.get("pick") or ""
    confidence = lane_row.get("confidence", "")
    odds = lane_row.get("best_odds", "")
    play_type = lane_row.get("pick_type", "Straight")   # fallback

    # 🧮 SUM validation
    sum_val = digit_sum(pick)

    # 🎯 Legend code selection
    legend_code = "A"   # default (we can enhance later)

    # 🟩 Play flag logic
    try:
        c = float(confidence)
        play_flag = "PLAY" if c >= 0.30 else "SKIP"
    except:
        play_flag = "SKIP"

    return {
        "kit_type": kit_type,
        "subscriber_id": subscriber_id,
        "game": game,
        "draw_date": draw_date,
        "draw_time": draw_time,
        "pick": pick,
        "play_type": play_type,
        "confidence_score": confidence,
        "win_odds_1_in": odds,
        "sum": sum_val,
        "legend_code": legend_code,
        "play_flag": play_flag,
    }
