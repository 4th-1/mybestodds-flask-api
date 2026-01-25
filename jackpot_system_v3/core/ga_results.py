# core/ga_results.py

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import Counter
from datetime import datetime, date

Draw = Dict[str, Any]

def _load_json(path: Path) -> List[Draw]:
    if not path.exists():
        print(f"[GA_RESULTS WARNING] File not found: {path}")
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"[GA_RESULTS WARNING] Expected list in {path}, got {type(data)}")
            return []
        return data
    except Exception as e:
        print(f"[GA_RESULTS ERROR] Could not read {path}: {e}")
        return []

def load_all_ga_results(config: Dict[str, Any], root: Path) -> Dict[str, List[Draw]]:
    """
    Loads GA results for:
      - cash3_midday
      - cash3_evening
      - cash4_night
    Returns dict keyed by alias.
    """
    results_cfg = config.get("ga_results", {})

    out: Dict[str, List[Draw]] = {}
    for key in ["cash3_midday", "cash3_evening", "cash4_night"]:
        rel_path = results_cfg.get(key)
        if not rel_path:
            print(f"[GA_RESULTS WARNING] No path configured for {key}")
            out[key] = []
            continue
        full_path = root / rel_path
        out[key] = _load_json(full_path)
        print(f"[GA_RESULTS] Loaded {len(out[key])} draws from {full_path}")
    return out

def _filter_last_n_days(draws: List[Draw], as_of: date, n_days: int) -> List[Draw]:
    filtered: List[Draw] = []
    for d in draws:
        try:
            d_date = datetime.fromisoformat(d["date"]).date()
        except Exception:
            continue
        if 0 <= (as_of - d_date).days <= n_days:
            filtered.append(d)
    return filtered

def build_digit_frequencies(draws: List[Draw], as_of: date, window_days: int = 60) -> Counter:
    """
    Build digit frequency table (0-9) over the last N days from 'as_of'.
    """
    window = _filter_last_n_days(draws, as_of, window_days)
    freq = Counter()
    for d in window:
        digits_str = str(d.get("digits", ""))
        for ch in digits_str:
            if ch.isdigit():
                freq[ch] += 1
    return freq

def build_weekday_win_counts(draws: List[Draw], as_of: date, window_days: int = 180) -> Counter:
    """
    Count wins by weekday (0=Mon,...6=Sun) over last N days.
    """
    window = _filter_last_n_days(draws, as_of, window_days)
    counts = Counter()
    for d in window:
        try:
            d_date = datetime.fromisoformat(d["date"]).date()
        except Exception:
            continue
        wd = d_date.weekday()
        counts[wd] += 1
    return counts

def normalized_weekday_score(target_weekday: int, counts: Counter) -> float:
    """
    Returns a 0-100 score indicating how 'hot' this weekday is
    relative to others in the data.
    """
    if not counts:
        return 50.0

    # Average frequency
    total = sum(counts.values())
    avg = total / len(counts)

    target_count = counts.get(target_weekday, 0)
    if avg == 0:
        return 50.0

    ratio = target_count / avg  # >1 = hotter than average

    # Map ratio into 0-100 band: 0.5x->30, 1.0x->50, 1.5x->70, 2.0x->85, 3.0x->100 cap
    if ratio <= 0.5:
        return 30.0
    if ratio >= 3.0:
        return 100.0

    # Simple piecewise linear:
    # between 0.5 and 1.0 -> 30 to 50
    # between 1.0 and 1.5 -> 50 to 70
    # between 1.5 and 2.0 -> 70 to 85
    # between 2.0 and 3.0 -> 85 to 100
    if ratio <= 1.0:
        # 0.5→30, 1.0→50
        return 30.0 + (ratio - 0.5) * (20.0 / 0.5)
    if ratio <= 1.5:
        # 1.0→50, 1.5→70
        return 50.0 + (ratio - 1.0) * (20.0 / 0.5)
    if ratio <= 2.0:
        # 1.5→70, 2.0→85
        return 70.0 + (ratio - 1.5) * (15.0 / 0.5)
    # 2.0–3.0
    return 85.0 + (ratio - 2.0) * (15.0 / 1.0)
