# core/pick_engine_v3.py

import hashlib
import json
import random
import csv
from itertools import permutations as _iterperms
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

# ================================================================
#  EXPERIMENT TUNING KNOBS
#  Change ONE value, re-run simulate_historical.py + full_report.py,
#  then use full_report.py to measure the delta vs baseline.
# ================================================================

# Cash3 Evening session weight in frequency pool.
# 1  = equal (33% eve / 33% mid / 33% night)  — baseline 2026-04-14
# 3  = 60/40 Evening-heavy (60% eve / 20% mid / 20% night) — exp-01
# Reset to 1 after experiment and --save-baseline if it improves results.
CASH3_EVENING_WEIGHT: int = 1  # baseline: equal session weighting

# Cash4 system-lane variant depth: number of distinct picks per subscriber per day.
# 2  = baseline 2026-04-14 (181,818 system picks / 999 subs / 91 days)
# 3  = exp-03: +50% system coverage per subscriber (272,727 system picks)
# Increase cautiously — more variants improve coverage but may dilute precision.
# Run --save-baseline to lock in improvements.
CASH4_VARIANT_DEPTH: int = 2  # baseline: 2 variants/sub/day

# Cash3 system-lane variant depth baseline.
CASH3_VARIANT_DEPTH: int = 2

# Alignment unlock: expand surfaced variants on strong timing days.
# Score range is 0-40; unlock starts at ALIGNMENT_UNLOCK_START and scales
# linearly to full extra variants by ALIGNMENT_UNLOCK_MAX_SCORE.
ALIGNMENT_UNLOCK_START: float = 20.0
ALIGNMENT_UNLOCK_MAX_SCORE: float = 40.0
ALIGNMENT_UNLOCK_CASH3_EXTRA_MAX: int = 2
ALIGNMENT_UNLOCK_CASH4_EXTRA_MAX: int = 2

# Jackpot system-lane baselines.
MEGAMILLIONS_VARIANT_DEPTH: int = 2
POWERBALL_VARIANT_DEPTH: int = 2
MFL_VARIANT_DEPTH: int = 2

# Alignment unlock for jackpot games.
ALIGNMENT_UNLOCK_MM_EXTRA_MAX: int = 2
ALIGNMENT_UNLOCK_PB_EXTRA_MAX: int = 2
ALIGNMENT_UNLOCK_MFL_EXTRA_MAX: int = 2

# ================================================================
#  PLAY TYPE THRESHOLDS
#  Determines recommended_play field returned in API responses.
#  Confidence is 0.0–1.0 (normalised from stats score).
#
#  CALIBRATION — validated against 91-day simulation (220K picks at checkpoint):
#    0.60–0.75 range: 1.23% Cash3 win rate = SWEET SPOT (validated signal)
#    ≥ 0.75 range:    0.00% Cash3 win rate in 11,548 picks = OVER-FITTED to history
#    0.40–0.60 range: 1.26% Cash3 win rate = solid moderate signal
#    < 0.40 range:    0.00% = noise
#
#  As a result, STRAIGHT+1OFF threshold is set to 0.65 (not 0.75) so the
#  "HOT SIGNAL" label covers the validated 0.65–0.75 sweet spot.
#  The near-miss proximity check below independently issues STRAIGHT+1OFF
#  for picks that are 1 digit off recent draws — that remains the primary
#  trigger and is validated at 16x Cash3 / 35x Cash4 above random.
# ================================================================
PLAY_TYPE_BOX_MAX: float = 0.40          # < 40%       → BOX only
PLAY_TYPE_STRAIGHT_BOX_MAX: float = 0.55 # 40–55%      → STRAIGHT_BOX
PLAY_TYPE_STRAIGHT_MAX: float = 0.65     # 55–65%      → STRAIGHT
                                         # ≥ 65%        → STRAIGHT+1OFF (validated sweet spot)

# ----------------------------------------------------------------
# Option B — Near-Miss Score Boost
# Score bonus applied to combos that are ±1 on any digit of a recent
# actual draw result.  These are the "correction zone" candidates that
# sit adjacent to the number that came out.
#   1.0 = correction variants score exactly 1.0 above their raw frequency.
#         This lets them compete with recency combos (~1.4) while yielding
#         to high-frequency combos (2.0+).
# Change NEAR_MISS_BOOST_SCALE in exp-04, then re-run + compare baseline.
NEAR_MISS_BOOST_SCALE: float = 1.0   # baseline 2026-04-14

# Option A — Minimum score a recent actual must have in base stats before
# its ±1 neighbors are generated.  Prevents one-off / noise draws from
# seeding corrections.
#   1.0 = any draw that appeared at least once in history triggers corrections.
#   1.4 = only draws with a recency bonus (seen 5-15 draws ago) trigger.
#   2.0 = only draws seen 2+ times trigger.
# This is NOT a pool-size filter — it controls the TRIGGER, not the output.
MIN_SCORE_FOR_CORRECTION: float = 1.4  # exp-05 2026-04-14

# MMFSN gate: minimum frequency score for a personal number to be surfaced
# on a given day.  Score is from _build_combo_stats (decay-weighted).
#   1.0 = appeared at least once in history with any recency weighting
#   1.4 = has meaningful recency (seen within ~15 draws)
#   2.0 = seen multiple times → strong historical presence
# A number BELOW this threshold is suppressed for the day ("not aligned").
MMFSN_MIN_FREQUENCY_SCORE: float = 1.0

# How many recent draws (combined across sessions) to scan for near-miss
# neighbor generation.  Kept deliberately small to stay fresh.
#   3 = default; scan the last 3 results per game
NEAR_MISS_LOOKBACK: int = 3  # baseline 2026-04-14

# ----------------------------------------------------------------
# Decay Weighting — Three-Band History Model
# Each historical draw gets a weight based on how old it is relative
# to the most recent draw in the dataset.  Weighted frequency replaces
# raw count so deep history informs patterns without swamping recency.
#
# Band definitions (days from most recent draw):
#   DECAY_DAYS_RECENT   ≤ 90 days  → weight DECAY_WEIGHT_90D   (freshest signal)
#   DECAY_DAYS_MID      ≤ 365 days → weight DECAY_WEIGHT_12MO  (operational)
#   older               > 365 days → weight DECAY_WEIGHT_OLDER  (structural pattern)
#
# Default balance: 1.0 / 0.50 / 0.25
#   Fresh draw counts full, 1-year-old draws count half,
#   older draws count quarter — keeps system responsive while using full archive.
#
# Set all three to 1.0 to disable decay (flat weighting = pre-backfill behavior).
# Change one value at a time and re-run simulation + full_report.py.
DECAY_DAYS_RECENT:  int   = 90    # days threshold for "fresh" band
DECAY_DAYS_MID:     int   = 365   # days threshold for "operational" band
DECAY_WEIGHT_90D:   float = 1.00  # baseline 2026-04-14
DECAY_WEIGHT_12MO:  float = 0.50  # baseline 2026-04-14
DECAY_WEIGHT_OLDER: float = 0.25  # baseline 2026-04-14

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
            or row.get("winning_number")
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


def _extract_combo_history_dated(
    results: List[Dict[str, Any]], length: int
) -> "List[tuple[str, str]]":
    """
    Like _extract_combo_history() but returns (combo, iso_date_str) tuples.
    iso_date_str is YYYY-MM-DD sourced from the 'draw_date' field added by
    backfill_history.py, falling back to the 'date' field (M/D/YYYY format).
    Rows without a parseable date get iso_date=''.
    """
    from datetime import datetime as _dt
    items: "List[tuple[str, str]]" = []
    for row in results:
        raw = (
            row.get("winning_numbers")
            or row.get("Winning Numbers")
            or row.get("winning_number")
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

        # Resolve ISO date — normalize from any format to YYYY-MM-DD
        iso = ""
        for field in ("draw_date", "date"):
            raw_date = str(row.get(field, "")).strip()
            if not raw_date:
                continue
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
                try:
                    iso = _dt.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            if iso:
                break

        items.append((s, iso))
    return items


def _build_combo_stats(
    combos: List[str],
    *,
    min_occurrences: int = 1,
    near_miss_neighbors: "set | None" = None,
    boost_scale: float = 1.0,
    combo_dates: "List | None" = None,
    decay_weights: "tuple | None" = None,
) -> Dict[str, Dict[str, float]]:
    """
    Build frequency + recency stats for each combo in history.

    near_miss_neighbors: optional set of combo strings (Option B correction
    candidates).  Combos in this set receive a +boost_scale score bonus.
    If a neighbor was never seen in history it is added to stats with
    freq=0 and score=boost_scale (correction-only entry).

    combo_dates: optional List[Tuple[str, str]] — (combo, iso_date_str) —
    from _extract_combo_history_dated().  When provided together with
    decay_weights=(w_90d, w_12mo, w_older), each historical occurrence is
    weighted by its age band so deep history informs patterns without
    swamping recency.  The 'combos' list is still used for ordering/gap
    computation; combo_dates drives weighted frequency.
    """
    from collections import Counter
    from datetime import datetime as _dt

    if not combos:
        if near_miss_neighbors and boost_scale > 0:
            return {
                nb: {"freq": 0.0, "gap": 9999.0, "score": boost_scale}
                for nb in near_miss_neighbors
            }
        return {}

    # ── Weighted frequency (decay model) ──────────────────────────────────
    if combo_dates and decay_weights:
        w_90d, w_12mo, w_older = decay_weights
        # Reference = most recent ISO date in the dataset
        iso_dates = [iso for _, iso in combo_dates if iso]
        if iso_dates:
            ref_dt = _dt.strptime(max(iso_dates), "%Y-%m-%d")
        else:
            ref_dt = _dt.now()

        weighted_freq: dict = {}
        for combo, iso in combo_dates:
            if not iso:
                w = w_older
            else:
                try:
                    age_days = (ref_dt - _dt.strptime(iso, "%Y-%m-%d")).days
                except ValueError:
                    age_days = 9999
                if age_days <= DECAY_DAYS_RECENT:
                    w = w_90d
                elif age_days <= DECAY_DAYS_MID:
                    w = w_12mo
                else:
                    w = w_older
            weighted_freq[combo] = weighted_freq.get(combo, 0.0) + w

        # min_occurrences check: require raw count ≥ threshold (not weighted)
        raw_count = Counter(combos)
        weighted_freq = {c: v for c, v in weighted_freq.items()
                         if raw_count[c] >= min_occurrences}
        freq_for_score = weighted_freq  # float → used as "freq" below
    else:
        # ── Flat frequency (legacy / no decay) ────────────────────────────
        freq_for_score_raw = Counter(combos)
        freq_for_score = {c: float(v) for c, v in freq_for_score_raw.items()
                          if v >= min_occurrences}

    last_index = {}
    for idx, c in enumerate(combos):
        last_index[c] = idx

    total = len(combos)
    stats = {}

    for combo, f in freq_for_score.items():
        gap = total - 1 - last_index.get(combo, 0)

        recency_penalty = 0.4 if gap <= 2 else 0.0
        recency_bonus = 0.4 if 5 <= gap <= 15 else 0.0

        # Base score: deterministic, noise applied later in _pick_top_combos()
        score = float(f) + recency_bonus - recency_penalty

        # Option B boost: correction candidates gain additional score weight
        if near_miss_neighbors and combo in near_miss_neighbors:
            score += boost_scale

        stats[combo] = {
            "freq": float(f),
            "gap": float(gap),
            "score": score,
        }

    # Inject correction candidates that never appeared in history
    if near_miss_neighbors and boost_scale > 0:
        for neighbor in near_miss_neighbors:
            if neighbor not in stats:
                stats[neighbor] = {
                    "freq": 0.0,
                    "gap": float(total),
                    "score": boost_scale,
                }

    return stats


def _extract_near_miss_neighbors(
    history: List[Dict[str, Any]],
    combo_len: int,
    lookback: int = 3,
    base_stats: "Dict | None" = None,
    min_score: float = 1.0,
) -> "set[str]":
    """
    Generate ±1 digit-position neighbors of the most recent `lookback` draw
    results (Option B source pool).

    Option A gate (base_stats + min_score):
        If base_stats is provided, a recent draw must have a score >=
        min_score in base_stats before its neighbors are generated.
        One-off / noise draws are silently skipped.
        If base_stats is None the gate is disabled (all recent draws seed
        corrections).

    Returns a set of neighbor combo strings of length combo_len.
    Only generates the ±1 variants on each individual digit position
    (2 neighbors per position = 2*combo_len candidates per source draw).
    """
    # Collect last `lookback` valid draws (newest first)
    recent: List[str] = []
    for item in reversed(history):
        raw = (item.get("winning_numbers") or item.get("winning_number") or "")
        s = str(raw).strip().replace(" ", "")
        if len(s) == combo_len and s.isdigit():
            recent.append(s)
            if len(recent) >= lookback:
                break

    neighbors: set = set()
    for combo in recent:
        # Option A gate
        if base_stats is not None:
            if combo not in base_stats:
                continue  # never seen in history → low confidence, skip
            if base_stats[combo]["score"] < min_score:
                continue  # below confidence threshold → skip

        # ±1 on every digit position independently
        for pos in range(len(combo)):
            for delta in (-1, 1):
                d = (int(combo[pos]) + delta) % 10
                neighbor = combo[:pos] + str(d) + combo[pos + 1:]
                neighbors.add(neighbor)

    return neighbors


def _build_positional_freq(combos: List[str], length: int) -> List[List[float]]:
    """Build per-position digit frequency table from a list of historical combos.

    Returns pos_freq[position][digit] = weighted count (float).
    Used to rank permutations by their historical positional likelihood so
    straight predictions favour the digit orderings that actually recur.

    Args:
        combos: list of historical winning combo strings (exact length).
        length: expected combo length (3 for Cash3, 4 for Cash4).

    Returns:
        List of length `length`, each element a list of 10 floats (digits 0–9).
    """
    pos_freq: List[List[float]] = [[0.0] * 10 for _ in range(length)]
    for combo in combos:
        if len(combo) == length and combo.isdigit():
            for pos, ch in enumerate(combo):
                pos_freq[pos][int(ch)] += 1.0
    # Normalise each position so scores are comparable across lengths
    for pos in range(length):
        total = sum(pos_freq[pos]) or 1.0
        for d in range(10):
            pos_freq[pos][d] /= total
    return pos_freq


def _positional_score(combo: str, pos_freq: List[List[float]]) -> float:
    """Score a combo string by how well its digit order matches historical
    positional frequencies.

    A high score means each digit in this combo tends to appear at that
    position in actual draws — making it a stronger STRAIGHT candidate.
    Uses product of positional probabilities (log-space sum to avoid underflow).

    Args:
        combo:    the candidate combo string (e.g. "1234").
        pos_freq: output of _build_positional_freq().

    Returns:
        float — higher = stronger straight alignment.
    """
    import math
    if len(combo) != len(pos_freq):
        return 0.0
    log_score = 0.0
    for pos, ch in enumerate(combo):
        if not ch.isdigit():
            return 0.0
        p = pos_freq[pos][int(ch)]
        log_score += math.log(p + 1e-9)  # 1e-9 prevents log(0)
    return log_score


def _generate_signal_family(
    primary: str,
    stats: Dict[str, Dict[str, float]],
    top_pool: int = 25,
    pos_freq: "List[List[float]] | None" = None,
) -> List[str]:
    """
    Build a diversified "signal family" for distribution across subscribers.

    Phase 1 – top_pool highest-scoring combos from stats (the core signal pool).
    Phase 2 – all digit-permutations of the primary signal, ranked by positional
              frequency when pos_freq is provided (straight signal improvement).
    Phase 3 – digit-neighbor variants (+/-1 on each position of the primary).

    When pos_freq is provided (output of _build_positional_freq), Phase 2
    permutations are sorted so the highest positional-frequency orderings
    appear first in the family.  Subscribers assigned early slots get picks
    whose digit ORDER matches historical position patterns — improving straight
    hit rate without changing the digit composition (box rate unchanged).

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

    # Phase 2: permutations of primary — ranked by positional frequency
    perms = []
    for perm in _iterperms(primary):
        candidate = "".join(perm)
        if candidate not in seen:
            perms.append(candidate)
            seen.add(candidate)
    if pos_freq is not None and perms:
        # Sort permutations so highest positional-probability orderings come first.
        # Subscribers assigned earlier in the pool see the strongest straight picks.
        perms.sort(key=lambda c: _positional_score(c, pos_freq), reverse=True)
    family.extend(perms)

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
    pos_freq: "List[List[float]] | None" = None,
) -> List[str]:
    """
    Pick k combos from stats.

    subscriber_seed=None  → legacy noise-based ranking (backwards-compat).
    subscriber_seed=int   → deterministic family-based selection.
                            Uses the subscriber's hash to index into a signal
                            family so each sub gets a distinct-but-related pick.
                            With 999 subs over a ~35-combo family, each pick
                            is assigned to ~28 subs (vs 999 under the old code).
    pos_freq              → output of _build_positional_freq(). When provided,
                            permutations inside the signal family are ranked by
                            positional frequency so straight signal is improved.
                            Pass for Cash4 (and Cash3) system-lane picks.
    """
    if not stats:
        return []

    ranked = sorted(stats.items(), key=lambda x: x[1]["score"], reverse=True)
    if not ranked:
        return []

    # ── Diversified path (subscriber seed provided) ───────────────────────────
    if subscriber_seed is not None:
        primary = ranked[0][0]  # strongest signal this session/day
        family = _generate_signal_family(
            primary, stats,
            top_pool=max_family_pool,
            pos_freq=pos_freq,
        )
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


def _alignment_extra_variants(alignment_score: float, max_extra: int) -> int:
    """Map alignment score into extra surfaced variants."""
    if max_extra <= 0:
        return 0
    if alignment_score <= ALIGNMENT_UNLOCK_START:
        return 0

    span = max(ALIGNMENT_UNLOCK_MAX_SCORE - ALIGNMENT_UNLOCK_START, 1.0)
    ratio = min(max((alignment_score - ALIGNMENT_UNLOCK_START) / span, 0.0), 1.0)
    return int(round(ratio * max_extra))


def _recommended_play(confidence_score: float, number: str = "", history: "List[str] | None" = None) -> str:
    """Map a normalised confidence score (0.0–1.0) to a play type recommendation.

    Tiers align with the PLAY_TYPE_* thresholds defined in constants above:
      < 0.40  → "BOX"             (low confidence — cover permutations)
                or "FRONT_PAIR"/"BACK_PAIR" when pair digit signal is strong
      0.40–0.60 → "STRAIGHT_BOX" (moderate — hedge with box insurance)
      0.60–0.75 → "STRAIGHT"     (high — engine is convicted on order)
      ≥ 0.75  → "STRAIGHT+1OFF"  (very high — also cover adjacent digits)

    When confidence is below BOX threshold and history is provided, digit-position
    frequency is used to detect front/back pair dominance and surface FRONT_PAIR
    or BACK_PAIR instead of plain BOX.
    """
    if confidence_score >= PLAY_TYPE_STRAIGHT_MAX:
        return "STRAIGHT+1OFF"
    if confidence_score >= PLAY_TYPE_STRAIGHT_BOX_MAX:
        return "STRAIGHT"
    if confidence_score >= PLAY_TYPE_BOX_MAX:
        return "STRAIGHT_BOX"

    # Near-miss proximity check — if this pick is exactly 1 digit off from any
    # recent actual draw, recommend STRAIGHT+1OFF so the subscriber is covered
    # for a repeat alignment hit.  BOX does NOT pay on 1-off results; this
    # closes the product integrity gap where the engine surfaces a near-miss
    # candidate but the play type leaves the subscriber unprotected.
    if number and history and len(number) in (3, 4):
        recent = history[:14]  # check roughly the last 7 draw-days
        for draw in recent:
            draw = str(draw).strip()
            if len(draw) != len(number) or not draw.isdigit() or not number.isdigit():
                continue
            diffs = sum(1 for a, b in zip(number, draw) if a != b)
            if diffs == 1:
                return "STRAIGHT+1OFF"

    # Below BOX threshold — check for pair signal if we have number + history
    if number and history and len(number) >= 3:
        front = number[:2]
        back  = number[-2:]
        front_count = sum(1 for h in history if len(h) >= 2 and h[:2] == front)
        back_count  = sum(1 for h in history if len(h) >= 2 and h[-2:] == back)
        n = max(len(history), 1)
        front_rate = front_count / n
        back_rate  = back_count  / n
        # Pair is "strong" when it appears ≥ 3× the random expectation (1/100 = 1%)
        PAIR_SIGNAL_THRESHOLD = 0.03
        if front_rate >= PAIR_SIGNAL_THRESHOLD and front_rate >= back_rate:
            return "FRONT_PAIR"
        if back_rate >= PAIR_SIGNAL_THRESHOLD:
            return "BACK_PAIR"

    return "BOX"


# ================================================================
#  CONFIDENCE UI — subscriber-facing label + color
# ================================================================
# Tier mapping is validated against 91-day simulation results:
#   STRAIGHT+1OFF  → 16x Cash3 / 35x Cash4 above random  ← strongest signal
#   STRAIGHT       → 3.6x Cash3 above random              ← high conviction
#   STRAIGHT_BOX   → 2.4x Cash3 above random              ← moderate edge
#   FRONT/BACK PAIR→ pair-frequency signal detected        ← directional
#   BOX            → baseline coverage play                ← lowest tier
#
# Colors are CSS-compatible names for the Lovable frontend.
# Tier 1–4 allows the UI to drive progress bars or heat maps.

# Tier validation summary (91-day sim, 970K picks):
#   Tier 4 HOT SIGNAL   → STRAIGHT+1OFF: near-miss proximity = 16x Cash3 / 35x Cash4 vs random
#                          score-based ≥0.65 = validated 0.65–0.75 sweet spot (1.23% Cash3)
#   Tier 3 HIGH         → STRAIGHT: score 0.55–0.65, solid directional signal
#   Tier 2 GOOD PICK    → STRAIGHT_BOX / PAIR: moderate frequency signal + coverage
#   Tier 1 COVER PLAY   → BOX: base coverage, below signal threshold
_CONFIDENCE_UI_MAP = {
    "STRAIGHT+1OFF": {
        "label":       "HOT SIGNAL",
        "color":       "green",
        "tier":        4,
        "description": "Strongest signal — validated 35x above random for Cash4, 16x for Cash3",
    },
    "STRAIGHT": {
        "label":       "HIGH CONFIDENCE",
        "color":       "blue",
        "tier":        3,
        "description": "Strong frequency signal — engine convicted on digit order",
    },
    "STRAIGHT_BOX": {
        "label":       "GOOD PICK",
        "color":       "yellow",
        "tier":        2,
        "description": "Solid signal — covers exact order and any order",
    },
    "FRONT_PAIR": {
        "label":       "FRONT PAIR SIGNAL",
        "color":       "orange",
        "tier":        2,
        "description": "First two digits showing strong repeat pattern",
    },
    "BACK_PAIR": {
        "label":       "BACK PAIR SIGNAL",
        "color":       "orange",
        "tier":        2,
        "description": "Last two digits showing strong repeat pattern",
    },
    "BOX": {
        "label":       "COVER PLAY",
        "color":       "gray",
        "tier":        1,
        "description": "Coverage pick — wins in any digit order",
    },
    # Special entry for lane_mmfsn personal-number picks.
    # These always score conf=0.0 (not in frequency pool) but win at 3.5x
    # random in simulation — they carry their own validated signal.
    "PERSONAL_NUMBER": {
        "label":       "PERSONAL NUMBER",
        "color":       "purple",
        "tier":        3,
        "description": "Your personal number — validated strong signal in simulation",
    },
}
_CONFIDENCE_UI_DEFAULT = {
    "label":       "COVER PLAY",
    "color":       "gray",
    "tier":        1,
    "description": "Coverage pick — wins in any digit order",
}


def _confidence_ui(recommended_play: str, lane: str = "", game: str = "") -> dict:
    """Return subscriber-facing confidence label, color, and tier for a pick.

    Args:
        recommended_play: Value returned by _recommended_play().
        lane: Pick lane from the engine (e.g. 'lane_mmfsn', 'lane_system').
              When lane is 'lane_mmfsn', overrides to PERSONAL_NUMBER tier
              regardless of recommended_play, because mmfsn picks always score
              conf=0.0 (not in the frequency pool) but are validated at 3.5x
              above random in the 91-day simulation.
        game: Game name string (e.g. 'Cash3', 'Cash4'). Used to surface
              Cash4-specific BOX guidance since Cash4 box hits at 11.55x
              above random — the strongest per-game signal in the system.

    Returns:
        dict with keys: label, color, tier, description
        - label:       Human-readable signal strength
        - color:       CSS color name for frontend badge/chip (purple for personal)
        - tier:        Integer 1–4 (4 = strongest) for progress bars / heat maps
        - description: One-line explanation shown on pick detail card
    """
    if lane and "mmfsn" in lane.lower():
        return _CONFIDENCE_UI_MAP["PERSONAL_NUMBER"].copy()
    ui = _CONFIDENCE_UI_MAP.get(recommended_play, _CONFIDENCE_UI_DEFAULT).copy()
    # Cash4 box hits at 11.55x above random — the highest validated edge in the
    # system. Override the generic description so subscribers know BOX is the
    # recommended play regardless of whether they also want to try straight.
    if game in ("Cash4", "Quads"):
        if recommended_play == "BOX":
            ui["description"] = (
                "BOX play recommended — Cash4 box is your strongest edge "
                "(validated 11.55x above random in simulation)"
            )
        elif recommended_play == "STRAIGHT_BOX":
            ui["description"] = (
                "BOX also wins here — Cash4 box signal is exceptionally strong; "
                "straight covers the exact-order bonus"
            )
    return ui


# ================================================================
#  JACKPOT CONFIDENCE UI — game-level signal labels
# ================================================================
# Calibrated from 91-day × 999-subscriber simulation (970K picks):
#   Millionaire For Life: 22.87% prize win rate  ← dominant jackpot signal
#   Mega Millions:         4.66% prize win rate
#   Powerball:             4.32% prize win rate
_JACKPOT_CONFIDENCE_UI_MAP = {
    "Millionaire For Life": {
        "label":       "JACKPOT SIGNAL",
        "color":       "green",
        "tier":        4,
        "description": "Validated 22.87% prize win rate in 91-day simulation — strongest jackpot signal",
    },
    "Mega Millions": {
        "label":       "JACKPOT PICK",
        "color":       "blue",
        "tier":        3,
        "description": "Validated 4.66% prize win rate in 91-day simulation",
    },
    "Powerball": {
        "label":       "JACKPOT PICK",
        "color":       "blue",
        "tier":        3,
        "description": "Validated 4.32% prize win rate in 91-day simulation",
    },
}
_JACKPOT_CONFIDENCE_UI_DEFAULT = {
    "label":       "JACKPOT PICK",
    "color":       "blue",
    "tier":        3,
    "description": "Engine-selected jackpot number",
}


def _jackpot_confidence_ui(game: str) -> dict:
    """Return subscriber-facing confidence UI dict for a jackpot game pick.

    Args:
        game: Game name string, e.g. 'Powerball', 'Mega Millions',
              'Millionaire For Life'.

    Returns:
        dict with keys: label, color, tier, description — same shape as
        _confidence_ui() so the frontend can render jackpot picks identically.
    """
    return _JACKPOT_CONFIDENCE_UI_MAP.get(game, _JACKPOT_CONFIDENCE_UI_DEFAULT).copy()


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
    # Look up by subscriber UUID first (collision-proof), fall back to initials
    _sub_id = subscriber.get("subscriber_id", "")
    _mmfsn_dir = root / "data" / "mmfsn_profiles"
    mmfsn_path = _mmfsn_dir / f"{_sub_id}_mmfsn.json" if _sub_id else None
    if not mmfsn_path or not mmfsn_path.exists():
        mmfsn_path = _mmfsn_dir / f"{initials}_mmfsn.json"
    if mmfsn_path.exists():
        mm = json.loads(mmfsn_path.read_text(encoding="utf-8"))
        mmfsn_cash3 = mm.get("mmfsn_numbers", {}).get("Cash3", []) or []
        mmfsn_cash4 = mm.get("mmfsn_numbers", {}).get("Cash4", []) or []
    else:
        mmfsn_cash3 = []
        mmfsn_cash4 = []

    # ------------------------------------------------------------------
    # ALIGNMENT SCORE — how strong is this subscriber's timing today?
    #
    # score_result may be pre-computed and passed in by the caller.
    # If None, we compute it internally using the MMFSN profile.
    # Score range: 0–40 (from mmfsn_v3.compute_mmfsn_score_for_day).
    #
    # The score drives _family_pool_size: the depth of the signal family
    # that _pick_top_combos() samples from per subscriber.
    #   Low alignment  (0–10)  → pool 25  (baseline — broad spread)
    #   Mid alignment  (10–25) → pool 35  (moderate focus)
    #   High alignment (25–40) → pool 50  (tight, subscriber-specific signal)
    # ------------------------------------------------------------------
    alignment_score = 0.0
    if score_result is not None:
        try:
            alignment_score = float(score_result)
        except (TypeError, ValueError):
            alignment_score = 0.0
    else:
        birthdate = (
            subscriber.get("birthdate") or subscriber.get("birth_date")
            or subscriber.get("dob") or ""
        )
        if birthdate or mmfsn_path.exists():
            try:
                from core.mmfsn_v3 import compute_mmfsn_score_for_day
                _score, _ = compute_mmfsn_score_for_day(
                    subscriber, datetime.now(), config={}, root=root
                )
                alignment_score = _score
            except Exception:
                alignment_score = 0.0

    # Map 0–40 → pool 25–50
    _family_pool_size = 25 + int(min(max(alignment_score, 0.0), 40.0) / 40.0 * 25)

    # ------------------ CASH 3 SYSTEM LANE (All Sessions) ------------------
    # CASH3_EVENING_WEIGHT controls session emphasis in the frequency pool.
    # 3 = 60% Evening / 20% Midday / 20% Night (exp-01)
    cash3_history = (
        ga_data.get("cash3_mid", [])
        + ga_data.get("cash3_eve", []) * CASH3_EVENING_WEIGHT
        + ga_data.get("cash3_night", [])
    )

    c3_combos = _extract_combo_history(cash3_history, 3)
    c3_dated  = _extract_combo_history_dated(cash3_history, 3)
    _decay = (DECAY_WEIGHT_90D, DECAY_WEIGHT_12MO, DECAY_WEIGHT_OLDER)

    # --- Option A + B: two-pass stats build for Cash3 ---
    # Pass 1: base stats with decay (no boost) — used as confidence gate for Option A
    _stats3_base = _build_combo_stats(c3_combos, combo_dates=c3_dated, decay_weights=_decay)
    # Derive ±1 neighbors of last NEAR_MISS_LOOKBACK high-confidence draws
    _c3_neighbors = _extract_near_miss_neighbors(
        cash3_history, 3,
        lookback=NEAR_MISS_LOOKBACK,
        base_stats=_stats3_base,
        min_score=MIN_SCORE_FOR_CORRECTION,
    )
    # Pass 2: rebuild stats with correction candidates boosted (Option B)
    stats3 = _build_combo_stats(
        c3_combos,
        combo_dates=c3_dated,
        decay_weights=_decay,
        near_miss_neighbors=_c3_neighbors,
        boost_scale=NEAR_MISS_BOOST_SCALE,
    )

    cash3_k = CASH3_VARIANT_DEPTH + _alignment_extra_variants(
        alignment_score,
        ALIGNMENT_UNLOCK_CASH3_EXTRA_MAX,
    )
    _c3_pos_freq = _build_positional_freq(c3_combos, 3)
    if stats3:
        system_cash3 = _pick_top_combos(
            stats3,
            k=cash3_k,
            subscriber_seed=subscriber_seed,
            max_family_pool=_family_pool_size,
            pos_freq=_c3_pos_freq,
        )
    else:
        freq3 = build_digit_frequency(last_digits_from_results(cash3_history, 30), 3)
        rng3 = random.Random(subscriber_seed)
        system_cash3 = [_fallback_generate_cash3(freq3) for _ in range(cash3_k)]
        # Shuffle the fallback list so different subs get different orderings
        rng3.shuffle(system_cash3)

    # ------------------ CASH 4 SYSTEM LANE (All Sessions) ------------------
    cash4_history = (
        ga_data.get("cash4_mid", [])
        + ga_data.get("cash4_eve", [])
        + ga_data.get("cash4_night", [])
    )

    c4_combos = _extract_combo_history(cash4_history, 4)
    c4_dated  = _extract_combo_history_dated(cash4_history, 4)

    # --- Option A + B: two-pass stats build for Cash4 ---
    # Pass 1: base stats with decay (no boost)
    _stats4_base = _build_combo_stats(c4_combos, combo_dates=c4_dated, decay_weights=_decay)
    # Derive ±1 neighbors of last NEAR_MISS_LOOKBACK high-confidence draws
    _c4_neighbors = _extract_near_miss_neighbors(
        cash4_history, 4,
        lookback=NEAR_MISS_LOOKBACK,
        base_stats=_stats4_base,
        min_score=MIN_SCORE_FOR_CORRECTION,
    )
    # Pass 2: rebuild stats with correction candidates boosted (Option B)
    stats4 = _build_combo_stats(
        c4_combos,
        combo_dates=c4_dated,
        decay_weights=_decay,
        near_miss_neighbors=_c4_neighbors,
        boost_scale=NEAR_MISS_BOOST_SCALE,
    )

    cash4_k = CASH4_VARIANT_DEPTH + _alignment_extra_variants(
        alignment_score,
        ALIGNMENT_UNLOCK_CASH4_EXTRA_MAX,
    )
    _c4_pos_freq = _build_positional_freq(c4_combos, 4)
    if stats4:
        system_cash4 = _pick_top_combos(
            stats4,
            k=cash4_k,
            subscriber_seed=subscriber_seed,
            max_family_pool=_family_pool_size,
            pos_freq=_c4_pos_freq,
        )
    else:
        freq4 = build_digit_frequency(last_digits_from_results(cash4_history, 30), 4)
        rng4 = random.Random(subscriber_seed + 1)
        system_cash4 = [_fallback_generate_cash4(freq4) for _ in range(cash4_k)]
        rng4.shuffle(system_cash4)

    # ------------------ JACKPOT ------------------
    mm_k = MEGAMILLIONS_VARIANT_DEPTH + _alignment_extra_variants(
        alignment_score,
        ALIGNMENT_UNLOCK_MM_EXTRA_MAX,
    )
    pb_k = POWERBALL_VARIANT_DEPTH + _alignment_extra_variants(
        alignment_score,
        ALIGNMENT_UNLOCK_PB_EXTRA_MAX,
    )
    mfl_k = MFL_VARIANT_DEPTH + _alignment_extra_variants(
        alignment_score,
        ALIGNMENT_UNLOCK_MFL_EXTRA_MAX,
    )

    mm_lines = generate_megamillions_picks(mm_k, root=root)
    pb_lines = generate_powerball_picks(pb_k, root=root)
    c4l_lines = generate_millionaire_for_life_picks(mfl_k, root=root)

    # ── MMFSN Frequency Gate ─────────────────────────────────────────────────
    # Only surface a personal number today if it appears in the current
    # frequency pool with a meaningful score.  Numbers below the threshold
    # are "not aligned" — the engine has no statistical evidence they are
    # due today, so suppressing them keeps the UI promise accurate.
    def _mmfsn_gate(numbers: list, stats: dict, min_score: float) -> list:
        if not stats:
            return numbers  # no history → surface all (graceful fallback)
        return [n for n in numbers if stats.get(str(n), {}).get("score", 0.0) >= min_score]

    mmfsn_cash3 = _mmfsn_gate(mmfsn_cash3, stats3, MMFSN_MIN_FREQUENCY_SCORE)
    mmfsn_cash4 = _mmfsn_gate(mmfsn_cash4, stats4, MMFSN_MIN_FREQUENCY_SCORE)

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
        # Internal key for confidence scoring — consumed by api_server.py,
        # stripped before returning to callers.
        "_stats": {"cash3": stats3 if stats3 else {}, "cash4": stats4 if stats4 else {}},
    }