# core/pick_engine_v3.py

import json
import random
import csv
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from core.cash_pattern_model_v1 import (
    build_cash_history,
    pick_top_cash_combos_for_day
)

# ================================================================
#  GA RESULTS LOADING — NEW MULTI-SESSION CSV FORMAT  (CRITICAL)
# ================================================================
def load_ga_results(root: Path) -> Dict[str, Any]:
    """
    Load GA Cash3/Cash4 results from the NEW CSV files:

        Cash3_Midday_Evening_Night.csv
        Cash4_Midday_Evening_Night.csv

    Expected CSV structure:
        draw_date, winning_numbers, session

    Session values:
        "Midday", "Evening", "Night"

    Returns dict:
        {
          "cash3_mid": [...],
          "cash3_eve": [...],
          "cash3_night": [...],
          "cash4_mid": [...],
          "cash4_eve": [...],
          "cash4_night": [...],
        }
    """

    results_dir = root / "data" / "ga_results"

    def load_csv(name: str) -> List[Dict[str, Any]]:
        path = results_dir / name
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                clean_row = {
                    "draw_date": r.get("draw_date") or r.get("Draw Date"),
                    "winning_numbers": r.get("winning_numbers") or r.get("Winning Numbers"),
                    "session": r.get("session") or r.get("Session"),
                }
                rows.append(clean_row)
        return rows

    # Load new CSVs
    cash3_rows = load_csv("Cash3_Midday_Evening_Night.csv")
    cash4_rows = load_csv("Cash4_Midday_Evening_Night.csv")

    # Split by session
    out = {
        "cash3_mid":   [],
        "cash3_eve":   [],
        "cash3_night": [],
        "cash4_mid":   [],
        "cash4_eve":   [],
        "cash4_night": [],
    }

    for row in cash3_rows:
        sess = (row.get("session") or "").strip().lower()
        if sess == "midday":
            out["cash3_mid"].append(row)
        elif sess == "evening":
            out["cash3_eve"].append(row)
        elif sess == "night":
            out["cash3_night"].append(row)

    for row in cash4_rows:
        sess = (row.get("session") or "").strip().lower()
        if sess == "midday":
            out["cash4_mid"].append(row)
        elif sess == "evening":
            out["cash4_eve"].append(row)
        elif sess == "night":
            out["cash4_night"].append(row)

    return out


# ================================================================
#  HISTORY EXTRACTION / FREQUENCY + RECENCY MODEL
# ================================================================
def _extract_combo_history(results: List[Dict[str, Any]], length: int) -> List[str]:
    combos: List[str] = []
    for row in results:
        raw = (
            row.get("winning_numbers")
            or row.get("Winning Numbers")
            or row.get("result")
            or row.get("Result")
        )
        if raw is None:
            continue
        s = str(raw).strip().replace(" ", "")
        if not s.isdigit():
            continue
        s = s.zfill(length)
        if len(s) != length:
            continue
        combos.append(s)
    return combos


def _build_combo_stats(combos: List[str], *, min_occurrences: int = 1) -> Dict[str, Dict[str, float]]:
    from collections import Counter
    if not combos:
        return {}

    freq = Counter(combos)
    last_index = {}
    for idx, c in enumerate(combos):
        last_index[c] = idx

    total = len(combos)
    stats = {}

    for combo, f in freq.items():
        if f < min_occurrences:
            continue
        gap = total - 1 - last_index[combo]

        recency_penalty = 0.4 if gap <= 2 else 0.0
        recency_bonus = 0.4 if 5 <= gap <= 15 else 0.0

        score = float(f) + recency_bonus - recency_penalty

        stats[combo] = {"freq": float(f), "gap": float(gap), "score": score}

    return stats


def _pick_top_combos(stats: Dict[str, Dict[str, float]], k: int) -> List[str]:
    if not stats:
        return []
    sorted_items = sorted(stats.items(), key=lambda kv: kv[1]["score"], reverse=True)
    return [combo for combo, _ in sorted_items[:k]]


# ================================================================
#  LEGACY FALLBACK
# ================================================================
def last_digits_from_results(results: List[Dict[str, Any]], count: int = 20) -> List[str]:
    nums = []
    for item in results[-count:]:
        raw = item.get("winning_numbers")
        if raw:
            nums.append(str(raw))
    return nums


def build_digit_frequency(numbers: List[str], length: int) -> List[int]:
    freq = [0] * 10
    for n in numbers:
        s = str(n).strip().replace(" ", "")
        if len(s) == length:
            for d in s:
                if d.isdigit():
                    freq[int(d)] += 1
    return freq


def _weighted_digit(freq: List[int]) -> int:
    digits = list(range(10))
    weights = [x + 1 for x in freq]
    return random.choices(digits, weights=weights)[0]


def _fallback_generate_cash3(freq: List[int]) -> str:
    return "".join(str(_weighted_digit(freq)) for _ in range(3))


def _fallback_generate_cash4(freq: List[int]) -> str:
    return "".join(str(_weighted_digit(freq)) for _ in range(4))


# ================================================================
#  JACKPOT LINES
# ================================================================
def _generate_jackpot_line(main_min, main_max, main_count, special_min, special_max) -> str:
    mains = random.sample(range(main_min, main_max + 1), main_count)
    mains.sort()
    special = random.randint(special_min, special_max)
    return f"{' '.join(f'{m:02d}' for m in mains)} + {special:02d}"


def generate_megamillions_picks(lines=2): return [_generate_jackpot_line(1, 70, 5, 1, 25) for _ in range(lines)]
def generate_powerball_picks(lines=2):    return [_generate_jackpot_line(1, 69, 5, 1, 26) for _ in range(lines)]

def generate_cash4life_picks(lines=2):    
    """Generate Cash4Life picks with adjacent number enhancement"""
    base_picks = [_generate_jackpot_line(1, 60, 5, 1, 4) for _ in range(lines)]
    
    # Apply adjacent number enhancement to each pick
    try:
        from ..adjacent_number_enhancement_v3_7 import enhance_cash4life_prediction
        enhanced_picks = []
        for pick in base_picks:
            main_nums = pick.get("main", [])
            if len(main_nums) == 5:
                enhanced_nums = enhance_cash4life_prediction(main_nums)
                enhanced_pick = pick.copy()
                enhanced_pick["main"] = enhanced_nums
                enhanced_picks.append(enhanced_pick)
            else:
                enhanced_picks.append(pick)
        return enhanced_picks
    except ImportError:
        # Fallback if enhancement module not available
        return base_picks


# ================================================================
#  MAIN PICK ENGINE V3 (DUAL-LANE)
# ================================================================
def generate_picks_v3(subscriber: Dict[str, Any], score_result: Any, ga_data: Dict[str, Any], root: Path) -> Dict[str, Any]:

    initials = subscriber.get("initials", "").upper()

    # ------------------ MMFSN ------------------
    mmfsn_path = root / "data" / "mmfsn_profiles" / f"{initials}_mmfsn.json"
    if mmfsn_path.exists():
        mm = json.loads(mmfsn_path.read_text(encoding="utf-8"))
        mmfsn_cash3 = mm.get("mmfsn_numbers", {}).get("Cash3", []) or []
        mmfsn_cash4 = mm.get("mmfsn_numbers", {}).get("Cash4", []) or []
    else:
        mmfsn_cash3 = []
        mmfsn_cash4 = []

    # ------------------ CASH 3 SYSTEM LANE (All Sessions) ------------------
    cash3_history = (
        ga_data.get("cash3_mid", [])
        + ga_data.get("cash3_eve", [])
        + ga_data.get("cash3_night", [])
    )

    c3_combos = _extract_combo_history(cash3_history, 3)
    stats3 = _build_combo_stats(c3_combos)

    if stats3:
        system_cash3 = _pick_top_combos(stats3, k=2)
    else:
        freq3 = build_digit_frequency(last_digits_from_results(cash3_history, 30), 3)
        system_cash3 = [_fallback_generate_cash3(freq3) for _ in range(2)]

    # ------------------ CASH 4 SYSTEM LANE (All Sessions) ------------------
    cash4_history = (
        ga_data.get("cash4_mid", [])
        + ga_data.get("cash4_eve", [])
        + ga_data.get("cash4_night", [])
    )

    c4_combos = _extract_combo_history(cash4_history, 4)
    stats4 = _build_combo_stats(c4_combos)

    if stats4:
        system_cash4 = _pick_top_combos(stats4, k=2)
    else:
        freq4 = build_digit_frequency(last_digits_from_results(cash4_history, 30), 4)
        system_cash4 = [_fallback_generate_cash4(freq4) for _ in range(2)]

    # ------------------ JACKPOT ------------------
    mm_lines = generate_megamillions_picks(2)
    pb_lines = generate_powerball_picks(2)
    c4l_lines = generate_cash4life_picks(2)

    return {
        "Cash3": {
            "lane_mmfsn": mmfsn_cash3,
            "lane_system": system_cash3,
        },
        "Cash4": {
            "lane_mmfsn": mmfsn_cash4,
            "lane_system": system_cash4,
        },
        "MegaMillions": {"lane_system": mm_lines},
        "Powerball": {"lane_system": pb_lines},
        "Cash4Life": {"lane_system": c4l_lines},
    }