# core/mmfsn_v3.py

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional


@dataclass
class MMFSNDebug:
    has_profile: bool
    cash3_count: int
    cash4_count: int
    base_strength: float
    day_factor: float
    final_score: float
    notes: str


def _get_root() -> Path:
    """Resolve project root (jackpot_system_v3)."""
    return Path(__file__).resolve().parents[1]


def load_mmfsn_profile(initials: str, root: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load MMFSN profile for a given subscriber initials.
    Looks for: data/mmfsn_profiles/<INITIALS>_mmfsn.json
    """
    if root is None:
        root = _get_root()

    mmfsn_dir = root / "data" / "mmfsn_profiles"
    profile_path = mmfsn_dir / f"{initials.upper()}_mmfsn.json"

    if not profile_path.exists():
        return None

    with profile_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compute_mmfsn_score_for_day(
    subscriber: Dict[str, Any],
    current_dt: datetime,
    config: Dict[str, Any],
    root: Optional[Path] = None
) -> Tuple[float, MMFSNDebug]:
    """
    Compute the MMFSN contribution for a given subscriber and day.

    V3 DESIGN (first-pass implementation):
      - Uses how many MMFSN numbers exist (Cash3 + Cash4)
      - Applies your global MMFSN cap: max 5 per game (already enforced by cleaner)
      - Scales a base strength by a simple day-of-month factor so score is not static

    Later, this function can be upgraded to:
      - Cross-check MMFSN against GA stats
      - Cross-check against generated picks
      - Use hit-history & streak logic
    """

    if root is None:
        root = _get_root()

    initials = subscriber.get("initials", "").upper()
    profile = load_mmfsn_profile(initials, root=root)

    if not profile:
        debug = MMFSNDebug(
            has_profile=False,
            cash3_count=0,
            cash4_count=0,
            base_strength=0.0,
            day_factor=0.0,
            final_score=0.0,
            notes="No MMFSN profile found for subscriber."
        )
        return 0.0, debug

    mmfsn_numbers = profile.get("mmfsn_numbers", {})
    cash3_list = mmfsn_numbers.get("Cash3", []) or []
    cash4_list = mmfsn_numbers.get("Cash4", []) or []

    cash3_count = len(cash3_list)
    cash4_count = len(cash4_list)

    # ---- Base strength from how many personal numbers exist ----
    #
    # Max 10 total (5+5). We map 0..10 → 0..40 points.
    #
    total_count = cash3_count + cash4_count
    base_strength = min(total_count, 10) * 4.0  # 0 → 0, 10 → 40

    # ---- Day factor: simple modulation so score is not identical every day ----
    #
    # Use day-of-month (1..31) to produce 0.6–1.0 factor.
    #
    day = current_dt.day
    day_factor = 0.6 + 0.4 * ((day - 1) / 30.0)  # roughly 0.6–1.0

    raw_score = base_strength * day_factor  # rough range 0–40

    # Optional global weight from config (if present)
    mmfsn_weight_cfg = (
        config.get("score_weights", {})
        .get("mmfsn", 1.0)
    )

    final_score = raw_score * float(mmfsn_weight_cfg)

    debug = MMFSNDebug(
        has_profile=True,
        cash3_count=cash3_count,
        cash4_count=cash4_count,
        base_strength=base_strength,
        day_factor=day_factor,
        final_score=final_score,
        notes="First-pass MMFSN V3 score: count-based strength * day-of-month modulation."
    )

    return final_score, debug
