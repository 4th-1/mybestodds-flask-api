# core/pick_engine_v3.py

import hashlib
import json
import random
import csv
from itertools import permutations as _iterperms
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

        # Base score: deterministic, noise applied later in _pick_top_combos()
        score = float(f) + recency_bonus - recency_penalty

        stats[combo] = {
            "freq": float(f), 
            "gap": float(gap), 
            "score": score
        }

    return stats


def _generate_signal_family(
    primary: str,
    stats: Dict[str, Dict[str, float]],
    top_pool: int = 25,
) -> List[str]:
    """
    Build a diversified "signal family" for distribution across subscribers.

    Phase 1 – top_pool highest-scoring combos from stats (the core signal pool).
    Phase 2 – all digit-permutations of the primary signal.
    Phase 3 – digit-neighbor variants (+/-1 on each position of the primary).

    Result is deduplicated and ordered: stats-ranked combos first, then extras.
    This gives ~30-50 valid variants so 999 subscribers spread across them
    (≈ 20-33 subscribers per pick instead of 999 on one pick).
    """
    ranked = sorted(stats.items(), key=lambda x: x[1]["score"], reverse=True)
    family: List[str] = []
    seen: set = set()

    # Phase 1: top stats combos
    for combo, _ in ranked[:top_pool]:
        if combo not in seen:
            family.append(combo)
            seen.add(combo)

    # Phase 2: permutations of primary
    for perm in _iterperms(primary):
        candidate = "".join(perm)
        if candidate not in seen:
            family.append(candidate)
            seen.add(candidate)

    # Phase 3: digit neighbors (+/-1 per position, wrapping mod 10)
    for pos in range(len(primary)):
        for delta in (-1, 1):
            d = (int(primary[pos]) + delta) % 10
            neighbor = primary[:pos] + str(d) + primary[pos + 1:]
            if neighbor not in seen:
                family.append(neighbor)
                seen.add(neighbor)

    return family


def _pick_top_combos(
    stats: Dict[str, Dict[str, float]],
    k: int,
    subscriber_seed: int = None,
    max_family_pool: int = 25,
) -> List[str]:
    """
    Pick k combos from stats.

    subscriber_seed=None  → legacy noise-based ranking (backwards-compat).
    subscriber_seed=int   → deterministic family-based selection.
                            Uses the subscriber's hash to index into a signal
                            family so each sub gets a distinct-but-related pick.
                            With 999 subs over a ~35-combo family, each pick
                            is assigned to ~28 subs (vs 999 under the old code).
    """
    if not stats:
        return []

    ranked = sorted(stats.items(), key=lambda x: x[1]["score"], reverse=True)
    if not ranked:
        return []

    # ── Diversified path (subscriber seed provided) ───────────────────────────
    if subscriber_seed is not None:
        primary = ranked[0][0]  # strongest signal this session/day
        family = _generate_signal_family(primary, stats, top_pool=max_family_pool)
        pool_size = min(len(family), max_family_pool + len(primary) * 2)  # reasonable cap
        pool = family[:max(pool_size, max_family_pool)]
        rng = random.Random(subscriber_seed)
        return rng.sample(pool, min(k, len(pool)))

    # ── Legacy path (no seed — used outside simulation context) ──────────────
    max_score = ranked[0][1]["score"]
    noise_factor = 0.15
    noisy_combos = [
        (combo, data["score"] + random.uniform(0, max_score * noise_factor))
        for combo, data in ranked
    ]
    noisy_combos.sort(key=lambda x: x[1], reverse=True)
    return [combo for combo, _ in noisy_combos[:k]]


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
#  JACKPOT FREQUENCY ENGINE
# ================================================================

def _load_jackpot_history(root: Path, game: str) -> tuple:
    """
    Load all available historical draws for a jackpot game.
    Returns (white_ball_counts, special_ball_counts) as Counter objects.
    Handles both old schema (n1-n5/bonus) and new 2026 schema (numbers col).
    """
    from collections import Counter
    white = Counter()
    special = Counter()

    base = root.resolve().parent / "historical_data" / "jackpot_results"
    if not base.exists():
        # Walk up from root to find historical_data
        candidate = root.resolve()
        for _ in range(4):
            candidate = candidate.parent
            if (candidate / "historical_data" / "jackpot_results").exists():
                base = candidate / "historical_data" / "jackpot_results"
                break

    def _parse_new_format(numbers_str):
        """Parse '01 15 22 34 56 + 04' → ([1,15,22,34,56], 4)"""
        try:
            parts = numbers_str.split("+")
            whites = [int(x) for x in parts[0].strip().split()]
            sp = int(parts[1].strip())
            return whites, sp
        except Exception:
            return [], None

    def _ingest_file(path):
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return
        fields = list(rows[0].keys())
        for row in rows:
            if "numbers" in fields:
                # 2026 format
                ws, sp = _parse_new_format(row.get("numbers", ""))
                for w in ws:
                    white[w] += 1
                if sp:
                    special[sp] += 1
            elif "winning_numbers" in fields:
                # yearly format: winning_numbers is space- or dash-separated
                ws_str = row.get("winning_numbers", "").strip().replace("-", " ")
                ws = [int(x) for x in ws_str.split() if x.isdigit()]
                for w in ws:
                    white[w] += 1
                # special ball column: try bonus_ball first (may be float string), then megaball/powerball
                for col in ["bonus_ball", "megaball", "powerball"]:
                    v = row.get(col, "").strip()
                    if v:
                        try:
                            sp_val = int(float(v))
                            if sp_val > 0:
                                special[sp_val] += 1
                                break
                        except ValueError:
                            pass
            elif "n1" in fields:
                # old master format
                for col in ["n1", "n2", "n3", "n4", "n5"]:
                    v = row.get(col, "").strip()
                    if v.isdigit():
                        white[int(v)] += 1
                v = row.get("bonus", "").strip()
                if v.isdigit():
                    special[int(v)] += 1

    # Determine file patterns per game
    if game == "MegaMillions":
        patterns = ["MegaMillions_Complete_2005_2025.csv", "2026/MegaMillions.csv"]
    elif game == "Powerball":
        patterns = ["Powerball_Complete_2005_2025.csv", "2026/Powerball.csv"]
    elif game == "Millionaire For Life":
        patterns = ["Cash4Life_Master.csv", "2026/Millionaire_For_Life.csv"]
    else:
        return white, special

    for pattern in patterns:
        path = base / pattern
        if path.exists():
            _ingest_file(path)

    return white, special


def _frequency_pick_line(white_counts, white_range, white_n,
                         special_counts, special_range) -> str:
    """
    Pick a jackpot line using frequency-weighted sampling.
    - Builds a weighted pool from the top 60% most-drawn numbers
    - Uses random.choices (with weights) so picks vary per call
    """
    # ── White balls ──
    all_whites = list(range(white_range[0], white_range[1] + 1))
    if white_counts:
        weights = [white_counts.get(n, 0) + 1 for n in all_whites]  # +1 floor
        # Sample 2× needed, deduplicate, take first white_n
        pool_size = min(len(all_whites), white_n * 4)
        pool = []
        seen = set()
        attempts = 0
        while len(pool) < white_n and attempts < 200:
            pick = random.choices(all_whites, weights=weights, k=1)[0]
            if pick not in seen:
                seen.add(pick)
                pool.append(pick)
            attempts += 1
        # Pad with random if needed
        remaining = [n for n in all_whites if n not in seen]
        while len(pool) < white_n:
            pool.append(remaining.pop(random.randrange(len(remaining))))
    else:
        pool = random.sample(all_whites, white_n)

    pool.sort()

    # ── Special ball ──
    all_specials = list(range(special_range[0], special_range[1] + 1))
    if special_counts:
        sp_weights = [special_counts.get(n, 0) + 1 for n in all_specials]
        sp = random.choices(all_specials, weights=sp_weights, k=1)[0]
    else:
        sp = random.choice(all_specials)

    return f"{' '.join(f'{m:02d}' for m in pool)} + {sp:02d}"


# Cache loaded history so we don't re-read CSVs on every call
_jackpot_history_cache: Dict[str, Any] = {}

def _get_jackpot_history(root: Path, game: str):
    if game not in _jackpot_history_cache:
        _jackpot_history_cache[game] = _load_jackpot_history(root, game)
    return _jackpot_history_cache[game]


def generate_megamillions_picks(lines=2, root: Path = None):
    if root:
        wc, sc = _get_jackpot_history(root, "MegaMillions")
    else:
        from collections import Counter
        wc, sc = Counter(), Counter()
    return [_frequency_pick_line(wc, (1, 70), 5, sc, (1, 25)) for _ in range(lines)]


def generate_powerball_picks(lines=2, root: Path = None):
    if root:
        wc, sc = _get_jackpot_history(root, "Powerball")
    else:
        from collections import Counter
        wc, sc = Counter(), Counter()
    return [_frequency_pick_line(wc, (1, 69), 5, sc, (1, 26)) for _ in range(lines)]


def generate_millionaire_for_life_picks(lines=2, root: Path = None):
    """Generate Millionaire For Life picks with frequency-weighted selection.
    White balls: 1-60, pick 5 | Millionaire Ball: 1-5"""
    if root:
        wc, sc = _get_jackpot_history(root, "Millionaire For Life")
    else:
        from collections import Counter
        wc, sc = Counter(), Counter()
    return [_frequency_pick_line(wc, (1, 60), 5, sc, (1, 5)) for _ in range(lines)]



# ================================================================
#  MAIN PICK ENGINE V3 (DUAL-LANE)
# ================================================================
def generate_picks_v3(subscriber: Dict[str, Any], score_result: Any, ga_data: Dict[str, Any], root: Path) -> Dict[str, Any]:

    initials = subscriber.get("initials", "").upper()

    # Deterministic seed from subscriber initials — distributes family picks
    # uniformly so no two adjacent subs pick the same number.
    # MD5 is used purely as a hash (not for security); first 8 hex chars → uint32.
    _h = hashlib.md5(initials.encode()).hexdigest()[:8]
    subscriber_seed = int(_h, 16)

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
        system_cash3 = _pick_top_combos(stats3, k=2, subscriber_seed=subscriber_seed)
    else:
        freq3 = build_digit_frequency(last_digits_from_results(cash3_history, 30), 3)
        rng3 = random.Random(subscriber_seed)
        system_cash3 = [_fallback_generate_cash3(freq3) for _ in range(2)]
        # Shuffle the fallback list so different subs get different orderings
        rng3.shuffle(system_cash3)

    # ------------------ CASH 4 SYSTEM LANE (All Sessions) ------------------
    cash4_history = (
        ga_data.get("cash4_mid", [])
        + ga_data.get("cash4_eve", [])
        + ga_data.get("cash4_night", [])
    )

    c4_combos = _extract_combo_history(cash4_history, 4)
    stats4 = _build_combo_stats(c4_combos)

    if stats4:
        system_cash4 = _pick_top_combos(stats4, k=2, subscriber_seed=subscriber_seed)
    else:
        freq4 = build_digit_frequency(last_digits_from_results(cash4_history, 30), 4)
        rng4 = random.Random(subscriber_seed + 1)
        system_cash4 = [_fallback_generate_cash4(freq4) for _ in range(2)]
        rng4.shuffle(system_cash4)

    # ------------------ JACKPOT ------------------
    mm_lines = generate_megamillions_picks(2, root=root)
    pb_lines = generate_powerball_picks(2, root=root)
    c4l_lines = generate_millionaire_for_life_picks(2, root=root)

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
        "Millionaire For Life": {"lane_system": c4l_lines},
    }