from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd

from core.overlay_loader_v3_7 import (
    load_all_overlays,
    ENGINE_LEFT,
)

# Load shared overlays once for the left engine
OVERLAY_CTX_LEFT = load_all_overlays(target=ENGINE_LEFT)

# We will allow overlays to move confidence by ±5% RELATIVE
MIN_MULT = 0.95
MAX_MULT = 1.05


@dataclass
class LeftScoreComponents:
    freq: float
    sum_score: float
    twin: float
    near_miss_pressure: float
    low_digit_boost: float = 0.0
    sequential_boost: float = 0.0


@dataclass
class LeftScoreResult:
    base_confidence: float          # stats-only confidence (0–1)
    confidence: float               # adjusted confidence (0–1, after overlays)
    best_odds: int                  # 1 in N odds, based on adjusted conf
    band: str                       # 🟩 🟨 🤎 🚫
    components: LeftScoreComponents
    debug: Dict[str, Any]


# -----------------------------------------------------------------
# 1. STATS-ONLY SCORING (YOUR EXISTING LOGIC, ADAPTED)
# -----------------------------------------------------------------

def band_from_odds(best_odds: int) -> str:
    """Return 🟩 🟨 🤎 🚫 based on 1-in-n odds."""
    if best_odds <= 50:
        return "🟩"
    if best_odds <= 150:
        return "🟨"
    if best_odds <= 300:
        return "🤎"
    return "🚫"


def compute_frequency_score(history_df: pd.DataFrame, candidate: str) -> float:
    """
    How often digits appear in history (normalized 0–1).
    history_df must have column 'numbers' as string (e.g., '724').
    """
    digits = list(candidate)
    total = 0
    for d in digits:
        total += history_df["numbers"].str.count(d).sum()
    # assuming 10 digits (0–9); normalize
    return total / (len(history_df) * 10)


def compute_sum_score(candidate: str, game: str) -> float:
    """Digit sum alignment probability."""
    s = sum(int(x) for x in candidate)
    if game == "Cash3":
        # Cash3 strong bands: 9–13 (recalibrated from 8-14, targets lower sums)
        return 1.0 if 9 <= s <= 13 else 0.65
    else:
        # Cash4 strong bands: 12–20
        return 1.0 if 12 <= s <= 20 else 0.55


def compute_low_digit_boost(candidate: str, game: str) -> float:
    """Boost for LOW digits (0-3) based on 2026 recalibration data."""
    if game != "Cash3":
        return 0.0
    
    low_count = sum(1 for d in candidate if int(d) <= 3)
    # 50% of digits in actual draws are LOW (0-3)
    # Boost based on LOW digit count
    if low_count == 3:
        return 0.20  # All LOW - massive boost
    elif low_count == 2:
        return 0.12  # 2 LOW digits - significant boost
    elif low_count == 1:
        return 0.05  # 1 LOW digit - small boost
    return 0.0


def compute_sequential_boost(candidate: str, game: str) -> float:
    """Boost for sequential patterns based on 2026 recalibration data."""
    if game != "Cash4":
        return 0.0
    
    digits = [int(d) for d in candidate]
    
    # Check for sequential patterns (ascending or descending)
    is_sequential = False
    
    # Perfect ascending (e.g., 1234, 5678)
    ascending = all(digits[i] + 1 == digits[i+1] for i in range(len(digits)-1))
    
    # Perfect descending (e.g., 9876, 4321)
    descending = all(digits[i] - 1 == digits[i+1] for i in range(len(digits)-1))
    
    # Near sequential (3 out of 4 consecutive, e.g., 7789, 4579)
    near_sequential = False
    for i in range(len(digits)-2):
        if digits[i] + 1 == digits[i+1] and digits[i+1] + 1 == digits[i+2]:
            near_sequential = True
            break
    
    if ascending or descending:
        return 0.25  # Perfect sequential - 25% boost
    elif near_sequential:
        return 0.15  # Near sequential - 15% boost
    
    return 0.0


def compute_twin_pressure(candidate: str, game: str) -> float:
    """Looks at repeating digits and evaluates probability."""
    if len(candidate) == 3:
        # Cash3 logic
        if len(set(candidate)) == 1:
            return 0.85      # triple pressure
        if len(set(candidate)) == 2:
            return 0.92      # double pressure
        return 0.70          # all-unique
    else:
        # Cash4 logic
        if len(set(candidate)) == 1:
            return 0.85
        if len(set(candidate)) == 2:
            return 0.93
        if len(set(candidate)) == 3:
            return 0.78
        return 0.65


def compute_base_confidence(
    freq: float,
    sum_score: float,
    twin: float,
    near_miss_pressure: float = 0.35,
    low_digit_boost: float = 0.0,
    sequential_boost: float = 0.0,
) -> float:
    """
    Combine subscores into final 0–1 score.
    This is your original v3.6 stats blend + 2026 recalibration boosts.
    """
    base_conf = (
        0.38 * freq +
        0.32 * sum_score +
        0.18 * twin +
        0.12 * near_miss_pressure
    )
    
    # Apply 2026 recalibration boosts (additive)
    conf = base_conf + low_digit_boost + sequential_boost
    
    # Ensure we don't exceed 1.0
    return round(min(conf, 1.0), 4)


def convert_conf_to_odds(conf: float) -> int:
    """Convert confidence (0–1, typically 0–0.03) into 1-in-n odds."""
    if conf <= 0:
        return 9999
    return int(round(1 / conf))


def classify_pattern(candidate: str) -> str:
    """Basic pattern identifier."""
    if len(set(candidate)) == 1:
        return "TRIPLE" if len(candidate) == 3 else "QUAD"
    if len(set(candidate)) == 2:
        return "DOUBLE"
    return "ALL-UNIQUE"


def bob_sugg(candidate: str) -> str:
    """BOB Best Odds Bonus suggestion (stats-only)."""
    pattern = classify_pattern(candidate)
    if pattern == "TRIPLE":
        return "BOB: Add 3-Way BOX"
    if pattern == "DOUBLE":
        return "BOB: Add 3-Way BOX"
    if pattern == "ALL-UNIQUE":
        return "BOB: Add 6-Way BOX (Safety)"
    return "BOB: None"


# -----------------------------------------------------------------
# 2. OVERLAY (ALIGNMENT) – LIGHT INFLUENCE (OPTION A)
# -----------------------------------------------------------------

def _get_multiplier(table: dict, key: str, default_key: str = "DEFAULT") -> float:
    """
    Safely look up a multiplier from an overlay table.

    Example JSON:
    {
        "FULL":    {"multiplier": 1.03},
        "NEW":     {"multiplier": 1.02},
        "DEFAULT": {"multiplier": 1.00}
    }
    """
    if not isinstance(table, dict):
        return 1.0

    entry = table.get(key) or table.get(default_key) or {}
    try:
        return float(entry.get("multiplier", 1.0))
    except (TypeError, ValueError):
        return 1.0


def apply_left_overlays_light(base_conf: float, meta: Dict[str, Any]) -> float:
    """
    Apply LIGHT overlay influence (Option A) for the left engine.

    base_conf: raw confidence from stats only (0–1, typically 0–0.03)
    meta:      metadata about this candidate:
               - moon_phase
               - day_of_week
               - weather_code
               - bias_pattern
               - planetary_hour

    Overlays:
      - nudge confidence using small multipliers
      - clamp combined multiplier to [0.95, 1.05] → ±5% RELATIVE
      - keep final score in [0.0, 1.0]
    """
    if base_conf <= 0:
        return base_conf

    shared = OVERLAY_CTX_LEFT.shared

    moon_table = shared.get("moon_phases", {})
    dow_table = shared.get("day_of_week", {})
    weather_table = shared.get("weather_rules", {})
    bias_table = shared.get("bias_patterns", {})
    planet_table = shared.get("planetary_hours", {})

    moon_key = meta.get("moon_phase")
    dow_key = meta.get("day_of_week")
    weather_key = meta.get("weather_code")
    bias_key = meta.get("bias_pattern")
    planet_key = meta.get("planetary_hour")

    moon_mult = _get_multiplier(moon_table, moon_key) if moon_key else 1.0
    dow_mult = _get_multiplier(dow_table, dow_key) if dow_key else 1.0
    weather_mult = _get_multiplier(weather_table, weather_key) if weather_key else 1.0
    bias_mult = _get_multiplier(bias_table, bias_key) if bias_key else 1.0
    planet_mult = _get_multiplier(planet_table, planet_key) if planet_key else 1.0

    combined_mult = (
        moon_mult *
        dow_mult *
        weather_mult *
        bias_mult *
        planet_mult
    )

    # Clamp combined multiplier to ±5% effect
    if combined_mult < MIN_MULT:
        combined_mult = MIN_MULT
    elif combined_mult > MAX_MULT:
        combined_mult = MAX_MULT

    adjusted = base_conf * combined_mult
    return max(0.0, min(1.0, adjusted))


# -----------------------------------------------------------------
# 3. PUBLIC API: SCORE A SINGLE CANDIDATE
# -----------------------------------------------------------------

def score_candidate_left(
    candidate: str,
    history_df: pd.DataFrame,
    game: str,
    near_miss_pressure: float = 0.35,
    meta: Dict[str, Any] = None,
) -> LeftScoreResult:
    """
    Core v3.7 left-engine scorer.

    - Computes stats-only base_confidence
    - Applies light overlays for alignment
    - Returns confidence, odds, and band for kit builders & debug tools
    """
    if meta is None:
        meta = {}

    freq = compute_frequency_score(history_df, candidate)
    sum_score = compute_sum_score(candidate, game)
    twin = compute_twin_pressure(candidate, game)
    low_boost = compute_low_digit_boost(candidate, game)
    seq_boost = compute_sequential_boost(candidate, game)

    base_conf = compute_base_confidence(
        freq=freq,
        sum_score=sum_score,
        twin=twin,
        near_miss_pressure=near_miss_pressure,
        low_digit_boost=low_boost,
        sequential_boost=seq_boost,
    )

    adj_conf = apply_left_overlays_light(base_conf, meta)

    odds = convert_conf_to_odds(adj_conf)
    band = band_from_odds(odds)

    components = LeftScoreComponents(
        freq=round(freq, 4),
        sum_score=sum_score,
        twin=twin,
        near_miss_pressure=near_miss_pressure,
        low_digit_boost=low_boost,
        sequential_boost=seq_boost,
    )

    debug = {
        "candidate": candidate,
        "game": game,
        "meta": meta,
        "base_confidence": base_conf,
        "adjusted_confidence": adj_conf,
        "odds": odds,
        "band": band,
    }

    return LeftScoreResult(
        base_confidence=base_conf,
        confidence=adj_conf,
        best_odds=odds,
        band=band,
        components=components,
        debug=debug,
    )


# -----------------------------------------------------------------
# 4. BULK SCORING HELPER (e.g., for pools)
# -----------------------------------------------------------------

def score_pool_left(
    history_df: pd.DataFrame,
    game: str,
    base_pool: List[str],
    near_miss_pressure: float = 0.35,
    meta_map: Dict[str, Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Score a whole pool of candidates and return a DataFrame
    sorted by adjusted confidence (highest first).

    meta_map (optional):
      dict of candidate -> meta, so each candidate can
      have specific moon_phase, DOW, planetary_hour, etc.
    """
    if meta_map is None:
        meta_map = {}

    rows = []
    for cand in base_pool:
        meta = meta_map.get(cand, {})
        res = score_candidate_left(
            candidate=cand,
            history_df=history_df,
            game=game,
            near_miss_pressure=near_miss_pressure,
            meta=meta,
        )

        rows.append({
            "candidate": cand,
            "base_confidence_score": res.base_confidence,
            "confidence_score": res.confidence,
            "best_odds": f"1 in {res.best_odds}",
            "band": res.band,
            "freq_score": res.components.freq,
            "sum_score": res.components.sum_score,
            "twin": res.components.twin,
            "near_miss_pressure": res.components.near_miss_pressure,
            "low_digit_boost": res.components.low_digit_boost,
            "sequential_boost": res.components.sequential_boost,
            "pattern": classify_pattern(cand),
            "bob": bob_sugg(cand),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by="confidence_score", ascending=False).reset_index(drop=True)
    return df
