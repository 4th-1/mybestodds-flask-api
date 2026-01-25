# core/score_fx_v3.py

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ScoreComponents:
    astro: float
    stats: float
    planetary_hours: float
    mmfsn: float
    numerology: float

@dataclass
class V3ScoreResult:
    total: float
    components: ScoreComponents
    debug: Dict[str, Any]

def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))

def compute_v3_score(
    astro_score: float,
    stats_score: float,
    planetary_hour_score: float,
    mmfsn_score: float,
    numerology_score: float,
    weights: Dict[str, float]
) -> V3ScoreResult:
    """
    Single scoring function for ALL kits.
    Inputs already normalized 0–100.
    Weights come from config_v3.json.
    """

    w_astro = weights.get("astro", 0.4)
    w_stats = weights.get("stats", 0.3)
    w_ph   = weights.get("planetary_hours", 0.1)
    w_mm   = weights.get("mmfsn", 0.1)
    w_num  = weights.get("numerology", 0.1)

    # Weighted sum
    raw_score = (
        astro_score * w_astro +
        stats_score * w_stats +
        planetary_hour_score * w_ph +
        mmfsn_score * w_mm +
        numerology_score * w_num
    )

    total_score = clamp(raw_score)

    components = ScoreComponents(
        astro=astro_score,
        stats=stats_score,
        planetary_hours=planetary_hour_score,
        mmfsn=mmfsn_score,
        numerology=numerology_score,
    )

    debug = {
        "weights": {
            "astro": w_astro,
            "stats": w_stats,
            "planetary_hours": w_ph,
            "mmfsn": w_mm,
            "numerology": w_num,
        },
        "raw_score": raw_score
    }

    return V3ScoreResult(total=total_score, components=components, debug=debug)
