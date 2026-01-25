"""
pick_engine_jackpot_v3_6.py

My Best Odds — Jackpot Pick Engine (v3.6, Option C)

Purpose:
    Transform raw jackpot modeling output (Mega Millions, Powerball, Cash4Life, etc.)
    into the unified flat v3.6 JSON schema used by:

        • excel_export_v3_6.py
        • merge_json_v3_6.py
        • BOOK / BOOK3 kit builders

Option C Enhancements:
    • Play Type (e.g., "Jackpot Only", "Jackpot + Small Prize", etc.)
    • Confidence %
    • Trend Arrow
    • Pattern Strength
    • Digit Energy
    • Sum & Sum Range
    • Jackpot-BONUS BOB 2.0 suggestion
    • Play Flag (PLAY / OPTIONAL / SKIP)
    • Legend (plain-English row interpretation)
"""

import json
from typing import Any, Dict, List


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def normalize_conf(value: Any) -> float:
    """Normalize confidence to 0–100."""
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0

    if 0 <= v <= 1:
        v *= 100.0

    return max(0.0, min(100.0, v))


def trend_to_arrow(t: Any) -> str:
    """Convert numeric/score trend into ⬆️ ➡️ ⬇️."""
    if t is None:
        return "➡️"
    try:
        v = float(t)
    except (TypeError, ValueError):
        return "➡️"

    if v > 0.15:
        return "⬆️"
    if v < -0.15:
        return "⬇️"
    return "➡️"


def classify_play_flag(conf: float) -> str:
    """Confidence % → PLAY / OPTIONAL / SKIP."""
    if conf >= 70:
        return "PLAY"
    if conf >= 40:
        return "OPTIONAL"
    return "SKIP"


def infer_play_type(game: str, row: Dict[str, Any]) -> str:
    """
    Jackpot-oriented play type description.

    You can refine this based on your existing logic,
    e.g., different types of wheel, coverage, etc.
    """
    coverage = row.get("coverage_mode", "")  # e.g., "jackpot_only", "balanced", "small_prize_focus"
    game_upper = (game or "").upper()

    if "MEGA" in game_upper or "POWER" in game_upper:
        if coverage == "jackpot_only":
            return "Jackpot Only"
        if coverage == "balanced":
            return "Jackpot + Small Prize"
        if coverage == "small_prize_focus":
            return "Small Prize Coverage"
        return "Standard Jackpot Play"

    if "CASH4LIFE" in game_upper or "CASH 4 LIFE" in game_upper:
        return "Daily Life Jackpot Play"

    return "Standard Play"


def compute_sum_and_range(main_balls: List[int]) -> (int, str):
    """
    Compute sum and crude sum range label for main balls.

    You can replace this with your richer distribution bands.
    """
    if not main_balls:
        return 0, ""

    s = sum(main_balls)

    # Very simple range bands; customize as needed
    if s < 60:
        label = "Low (0–59)"
    elif s < 120:
        label = "Medium (60–119)"
    else:
        label = "High (120+)"
    return s, label


def jackpot_bob_suggestion(conf: float, volatility: float, alt_lines: Dict[str, Any]) -> str:
    """
    Jackpot-flavored BOB 2.0 suggestion.

    Examples:
        - Add Extra Line (High Return)
        - Add Small-Prize Coverage
        - Keep Single Line Only (No BOB)
    """
    vol = 0.0
    try:
        vol = float(volatility or 0.0)
    except (TypeError, ValueError):
        vol = 0.0

    if conf >= 80 and vol <= 0.25:
        return "BOB Strong: Add Extra Line (High Return)"

    if alt_lines.get("has_small_prize_matrix"):
        return "Add Small-Prize Coverage Line"

    if conf >= 60:
        return "Straight Only (No BOB)"

    return ""


def build_number_string(game: str, main_balls: List[int], special_ball: int) -> str:
    """
    Build a compact representation string for the jackpot pick.
    E.g., "03-14-22-36-49 + 10"
    """
    if not main_balls:
        return ""

    main_str = "-".join(f"{b:02d}" for b in main_balls)

    game_upper = (game or "").upper()
    if "MEGA" in game_upper or "POWER" in game_upper or "CASH4LIFE" in game_upper:
        if special_ball is not None:
            return f"{main_str} + {special_ball:02d}"

    return main_str


def build_legend(row: Dict[str, Any]) -> str:
    """
    Build Option C jackpot legend line.
    """
    date = row.get("date", "")
    game = row.get("game", "")
    draw_time = row.get("draw_time", "")
    number = row.get("number", "")
    play_type = row.get("play_type", "")
    conf = row.get("confidence_percent", 0)
    trend = row.get("trend_arrow", "")
    bob = row.get("bob_20", "")
    sum_val = row.get("sum", "")
    sum_range = row.get("sum_range", "")
    play_flag = row.get("play_flag", "")

    core = f"{number} for {game} {draw_time} as {play_type} (~{conf:.0f}% conf | {trend})"

    if sum_range:
        core += f" | main sum {sum_val} in {sum_range}"

    if bob:
        core += f" | BOB: {bob}"

    if play_flag:
        core += f" | Flag: {play_flag}"

    return core


# ============================================================
# CORE TRANSFORM
# ============================================================

def transform_jackpot_output(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert raw jackpot model output → flat v3.6 rows.
    Expected raw fields (you can adjust names to match your engine):

        date            (YYYY-MM-DD)
        game            ("Mega Millions", "Powerball", "Cash4Life", etc.)
        draw_time       ("Tuesday", "Friday", "Mon", etc. — or leave blank)
        main_balls      (list of ints)
        special_ball    (int or None)
        jackpot_score   (0–1 or 0–100)
        trend_value     (float, positive = rising, negative = cooling)
        pattern_score   (pattern strength)
        digit_energy    (right-side analog; optional)
        coverage_mode   (jackpot_only / balanced / small_prize_focus)

        optional:
            signal_a
            signal_b
            volatility
            alt_lines (dict with flags like has_small_prize_matrix, etc.)
    """
    out_rows: List[Dict[str, Any]] = []

    for r in raw_rows:
        game = r.get("game", "")
        main_balls = r.get("main_balls") or []
        special_ball = r.get("special_ball")

        # skip if no main balls
        if not main_balls:
            continue

        conf = normalize_conf(r.get("jackpot_score"))
        trend_arrow = trend_to_arrow(r.get("trend_value"))

        # Sum & Range
        sum_val, sum_range = compute_sum_and_range(main_balls)

        # Play Type
        play_type = infer_play_type(game, r)

        # BOB 2.0 (jackpot version)
        volatility = r.get("volatility", 0.0)
        alt_lines = r.get("alt_lines", {}) or {}
        bob = jackpot_bob_suggestion(conf, volatility, alt_lines)

        # Play Flag
        play_flag = classify_play_flag(conf)

        # Number string
        number_str = build_number_string(game, main_balls, special_ball)

        row_out: Dict[str, Any] = {
            "date": r.get("date"),
            "game": game,
            "draw_time": r.get("draw_time", ""),  # can be blank or "Tue/Fri", etc.
            "number": number_str,

            "play_type": play_type,
            "confidence_percent": conf,
            "signal_a": r.get("signal_a", ""),
            "signal_b": r.get("signal_b", ""),
            "bob_20": bob,
            "trend_arrow": trend_arrow,
            "digit_energy": r.get("digit_energy", r.get("digit_energy_value", "")),
            "pattern_strength": r.get("pattern_score", ""),

            "sum": sum_val,
            "sum_range": sum_range,
            "play_flag": play_flag,
        }

        # Legend AFTER we have all fields
        row_out["legend"] = build_legend(row_out)

        out_rows.append(row_out)

    return out_rows


# ============================================================
# IO WRAPPER
# ============================================================

def build_jackpot_json(input_raw_json: str, output_json: str):
    """
    Load raw jackpot model output → transform → save flat v3.6 JSON.
    """
    with open(input_raw_json, "r", encoding="utf-8") as f:
        raw_rows = json.load(f)

    # Raw may be a dict keyed by game or simply a list
    if isinstance(raw_rows, dict):
        combined: List[Dict[str, Any]] = []
        for game_key, rows in raw_rows.items():
            if isinstance(rows, list):
                for r in rows:
                    if "game" not in r:
                        r["game"] = game_key
                    combined.append(r)
        raw_rows = combined

    final_rows = transform_jackpot_output(raw_rows)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=4)

    print(f"[MBO] Jackpot v3.6 JSON built → {output_json}")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Jackpot JSON v3.6 (Option C).")
    parser.add_argument("input_raw_json", help="Path to raw jackpot model output JSON.")
    parser.add_argument("output_json", help="Path to write flat v3.6 jackpot JSON.")
    args = parser.parse_args()

    build_jackpot_json(args.input_raw_json, args.output_json)
