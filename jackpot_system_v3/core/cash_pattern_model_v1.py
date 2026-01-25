"""
core/cash_pattern_model_v1.py

Recalibrated Cash3 / Cash4 prediction engine for My Best Odds V3.

- Learns from historical results (Cash3 / Cash4) per game
- Builds digit + position frequency, sum distribution, and recency ("due") stats
- Scores candidate combos with a clear formula
- Exposes a simple API that pick_engine_v3 can call:
    - build_cash_history(...)
    - score_cash_combo(...)
    - pick_top_cash_combos_for_day(...)
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Tuple, List, Optional, Iterable

from collections import defaultdict, Counter

# Type aliases
Digits = Tuple[int, ...]
GameName = str


@dataclass
class CashHistory:
    """
    Holds learned historical stats for a Cash game (Cash3 / Cash4).
    """
    game: GameName
    num_digits: int
    # Total draws considered
    draw_count: int

    # Digit frequency by position: pos_freq[pos][digit] -> count
    pos_freq: Dict[int, Counter]

    # Overall digit frequency (any position)
    digit_freq: Counter

    # Sum of digits frequency: sum_freq[sum_value] -> count
    sum_freq: Counter

    # Combo recency: last_seen[combo] -> last date seen
    last_seen: Dict[Digits, date]

    # Min and max dates in the historical window
    min_date: date
    max_date: date


def _ensure_date(d: date | datetime | str) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    # parse string
    s = str(d).strip()
    # try ISO first
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        # fallback to common US formats
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                continue
    # last resort: today (should almost never happen)
    return date.today()


def build_cash_history(
    game: GameName,
    results_by_date: Dict[str, Dict[str, Digits]],
    num_digits: int,
    lookback_days: int = 365
) -> CashHistory:
    """
    Build historical statistics for a cash game.

    results_by_date:
        { 'YYYY-MM-DD': { 'main': (d1, d2, d3 / d4) } }

    Only uses draws within the last `lookback_days` from the max date present.
    """
    # Normalize dates and sort
    parsed: List[Tuple[date, Digits]] = []
    for dstr, payload in results_by_date.items():
        main = payload.get("main")
        if not main:
            continue
        dd = _ensure_date(dstr)
        parsed.append((dd, tuple(int(x) for x in main)))

    if not parsed:
        # Empty history fallback
        return CashHistory(
            game=game,
            num_digits=num_digits,
            draw_count=0,
            pos_freq={i: Counter() for i in range(num_digits)},
            digit_freq=Counter(),
            sum_freq=Counter(),
            last_seen={},
            min_date=date.today(),
            max_date=date.today(),
        )

    parsed.sort(key=lambda x: x[0])
    min_d = parsed[0][0]
    max_d = parsed[-1][0]

    # Apply lookback window
    cutoff = max_d - timedelta(days=lookback_days)
    filtered = [(d, combo) for d, combo in parsed if d >= cutoff]

    if not filtered:
        filtered = parsed  # if nothing in window, use all

    pos_freq: Dict[int, Counter] = {i: Counter() for i in range(num_digits)}
    digit_freq: Counter = Counter()
    sum_freq: Counter = Counter()
    last_seen: Dict[Digits, date] = {}

    for d, combo in filtered:
        if len(combo) != num_digits:
            continue
        combo = tuple(int(x) for x in combo)
        # pos / digit frequency
        for idx, digit in enumerate(combo):
            pos_freq[idx][digit] += 1
            digit_freq[digit] += 1
        # sum freq
        s_val = sum(combo)
        sum_freq[s_val] += 1
        # last seen
        last_seen[combo] = max(last_seen.get(combo, d), d)

    draw_count = len(filtered)
    return CashHistory(
        game=game,
        num_digits=num_digits,
        draw_count=draw_count,
        pos_freq=pos_freq,
        digit_freq=digit_freq,
        sum_freq=sum_freq,
        last_seen=last_seen,
        min_date=filtered[0][0],
        max_date=filtered[-1][0],
    )


def _normalize_freq(counter: Counter) -> Dict[int, float]:
    """Convert counts to probabilities; handle empty."""
    total = sum(counter.values())
    if total <= 0:
        return {k: 0.0 for k in range(10)}
    return {d: counter.get(d, 0) / total for d in range(10)}


def _normalize_sum_freq(sum_freq: Counter) -> Dict[int, float]:
    total = sum(sum_freq.values())
    if total <= 0:
        return {}
    return {s: sum_freq[s] / total for s in sum_freq}


@dataclass
class CashComboScore:
    combo: Digits
    pos_score: float
    digit_score: float
    sum_score: float
    recency_score: float
    overlay_score: float
    total_score: float
    days_since_seen: Optional[int]


def score_cash_combo(
    combo: Digits,
    history: CashHistory,
    today: Optional[date] = None,
    overlay_boost: float = 0.0,
    w_pos: float = 0.35,
    w_digit: float = 0.25,
    w_sum: float = 0.20,
    w_recency: float = 0.20,
) -> CashComboScore:
    """
    Score a candidate combo using:
        - position frequency
        - overall digit frequency
        - sum-of-digits frequency
        - recency ("due" weight)
        - optional overlay_boost (Moorish/MMFSN/astro/etc)
    """
    if today is None:
        today = history.max_date

    combo = tuple(int(x) for x in combo)
    if len(combo) != history.num_digits:
        raise ValueError(f"Combo {combo} does not match num_digits={history.num_digits}")

    # ---------- position score ----------
    pos_probs: List[float] = []
    for idx, digit in enumerate(combo):
        pf = _normalize_freq(history.pos_freq.get(idx, Counter()))
        pos_probs.append(pf.get(digit, 0.0))
    pos_score = sum(pos_probs) / len(pos_probs) if pos_probs else 0.0

    # ---------- digit score ----------
    digit_probs = _normalize_freq(history.digit_freq)
    digit_score = sum(digit_probs.get(d, 0.0) for d in combo) / len(combo)

    # ---------- sum-of-digits score ----------
    s_val = sum(combo)
    sum_probs = _normalize_sum_freq(history.sum_freq)
    sum_score = sum_probs.get(s_val, 0.0)

    # ---------- recency score ----------
    last_seen_date = history.last_seen.get(combo)
    if last_seen_date:
        days_since = (today - last_seen_date).days
        # "Due" curve: saturating between 0 and 1
        # The longer it's been, the closer to 1.0
        recency_score = 1.0 - (1.0 / (1.0 + days_since / 30.0))
    else:
        # Never seen in this window → treat as somewhat "mysterious"
        days_since = None
        recency_score = 0.5

    # ---------- Overlay score ----------
    # overlay_boost is expected to be in range [-1, +1].
    overlay_score = overlay_boost

    # ---------- Final total ----------
    base_total = (
        w_pos * pos_score +
        w_digit * digit_score +
        w_sum * sum_score +
        w_recency * recency_score
    )
    total_score = base_total + overlay_score

    return CashComboScore(
        combo=combo,
        pos_score=pos_score,
        digit_score=digit_score,
        sum_score=sum_score,
        recency_score=recency_score,
        overlay_score=overlay_score,
        total_score=total_score,
        days_since_seen=days_since,
    )


def generate_all_cash_combos(num_digits: int) -> Iterable[Digits]:
    """
    Generate all possible combos for Cash3 / Cash4.

    num_digits=3 -> 000..999
    num_digits=4 -> 0000..9999
    """
    if num_digits == 3:
        for i in range(1000):
            s = f"{i:03d}"
            yield tuple(int(ch) for ch in s)
    elif num_digits == 4:
        for i in range(10000):
            s = f"{i:04d}"
            yield tuple(int(ch) for ch in s)
    else:
        raise ValueError("Only supports num_digits=3 or 4")


def pick_top_cash_combos_for_day(
    history: CashHistory,
    today: Optional[date] = None,
    k: int = 5,
    overlay_boost_fn = None,
) -> List[CashComboScore]:
    """
    Rank all combos and return top k.

    overlay_boost_fn:
        Optional callable: overlay_boost_fn(combo: Digits, game: str, day: date) -> float
        You can plug in Moorish / MMFSN / natal logic here later.
    """
    if today is None:
        today = history.max_date

    scores: List[CashComboScore] = []
    for combo in generate_all_cash_combos(history.num_digits):
        boost = 0.0
        if overlay_boost_fn is not None:
            try:
                boost = float(overlay_boost_fn(combo, history.game, today))
            except Exception:
                boost = 0.0
        sc = score_cash_combo(combo, history, today=today, overlay_boost=boost)
        scores.append(sc)

    # Sort by total_score descending
    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores[:k]
