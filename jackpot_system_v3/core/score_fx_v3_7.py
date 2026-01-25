"""
score_fx_v3_7.py

v3.7 SCORE LAYER

This module replaces the old blended v3.0–3.6 scoring logic.

For LEFT engine rows (Cash3, Cash4):
  - Uses the new v3.7 left scorer (stats-only base + light overlays)
  - Produces:
      base_confidence_score (0–1, stats only)
      confidence_score      (0–1, stats + overlays within ±5%)
      win_odds_1_in         (int)
      confidence_band       (🟩 🟨 🤎 🚫)

For RIGHT engine rows (jackpots):
  - Preserves any existing confidence if present
  - Normalizes and derives win_odds_1_in
  - Keeps behavior safe until a dedicated jackpot v3.7 scorer is added.
"""

from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import os

from core.score_left_v3_7 import (
    score_candidate_left,
    classify_pattern,
    bob_sugg,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _load_history_for_game(game_code: str) -> pd.DataFrame:
    """
    Load Cash3/Cash4 history. Adjust paths if your history files live
    elsewhere. For now, we mirror the debug_leftside_v3_7 convention.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if game_code.upper() == "CASH3":
        csv_path = os.path.join(base_dir, "history_cash3_2025.csv")
    else:
        csv_path = os.path.join(base_dir, "history_cash4_2025.csv")

    if not os.path.exists(csv_path):
        # Fails safe: empty frame if file not found
        return pd.DataFrame({"numbers": []})

    return pd.read_csv(csv_path, dtype=str)


def _build_meta_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build timing/alignment meta for overlay-light logic, based on row fields.

    Expected fields:
      - forecast_date (YYYY-MM-DD)
      - draw_time (MIDDAY / EVENING / NIGHT)
    """
    forecast_date = row.get("forecast_date")
    draw_time = row.get("draw_time")

    # Day-of-week
    dow = None
    if forecast_date:
        try:
            dow = datetime.strptime(forecast_date, "%Y-%m-%d").strftime("%a")
        except Exception:
            dow = None

    # 🌌 SWISS EPHEMERIS INTEGRATION - Real astronomical calculations!
    try:
        from .swiss_ephemeris_v3_7 import get_astronomical_context
        astro_data = get_astronomical_context(forecast_date, draw_time)
        
        return {
            "moon_phase": astro_data.get("moon_phase", "DEFAULT"),
            "moon_illumination": astro_data.get("moon_illumination", 0.5),
            "day_of_week": astro_data.get("day_of_week", dow),
            "planetary_hour": astro_data.get("planetary_hour", draw_time),
            "sun_sign": astro_data.get("sun_sign", "Unknown"),
            "moon_sign": astro_data.get("moon_sign", "Unknown"),
            "north_node_sign": astro_data.get("north_node_sign", "Unknown"),
            "planetary_positions": astro_data.get("planetary_positions", {}),
            "calculation_source": astro_data.get("calculation_source", "Unknown"),
            "weather_code": row.get("weather_code"),
            "bias_pattern": row.get("bias_pattern"),
        }
    except ImportError:
        # Fallback to old system if Swiss Ephemeris not available
        planet_key = draw_time  # e.g. "NIGHT", "MIDDAY", etc.
        moon_phase = row.get("moon_phase") or "DEFAULT"
        
        return {
            "moon_phase": moon_phase,
            "day_of_week": dow,
            "planetary_hour": planet_key,
            "weather_code": row.get("weather_code"),
            "bias_pattern": row.get("bias_pattern"),
            "calculation_source": "Legacy_Fallback"
        }


def _compute_odds_from_conf(conf: float) -> int:
    """
    Convert confidence (0–1, typically small like 0.01–0.03) into 1-in-n odds.
    """
    if conf <= 0:
        return 9999
    return int(round(1.0 / conf))


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ----------------------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------------------

def compute_scores_for_row(row: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central v3.7 scoring router.

    Called by engine_core_v3_7.MyBestOddsEngineV37._transform_row(...)
    for EVERY row (all games).

    Behavior:
      - LEFT engine (Cash3/Cash4): use new v3.7 left scoring.
      - RIGHT engine (jackpot): normalize any existing confidence, fill odds.
    """

    engine_side = row.get("engine_side")
    game_code = row.get("game_code", "").upper()

    # ------------------------------------------------------------------
    # LEFT ENGINE (Cash3 / Cash4) – full v3.7 scoring
    # ------------------------------------------------------------------
    if engine_side == "LEFT" and game_code in ("CASH3", "CASH4"):
        candidate = str(row.get("number", "")).strip()
        if not candidate:
            # If no number present, return row unchanged; SENTRY can flag later.
            return row

        # Map game_code to game name used by left scorer
        game_name = "Cash3" if game_code == "CASH3" else "Cash4"

        history_df = _load_history_for_game(game_code)
        meta = _build_meta_from_row(row)

        res = score_candidate_left(
            candidate=candidate,
            history_df=history_df,
            game=game_name,
            near_miss_pressure=row.get("near_miss_pressure", 0.35),
            meta=meta,
        )

        # Attach scores
        row["base_confidence_score"] = res.base_confidence
        row["confidence_score"] = res.confidence

        # Derive odds & band from adjusted confidence
        odds = res.best_odds
        row["win_odds_1_in"] = odds
        row["confidence_band"] = res.band

        # For convenience (if you still like the string form)
        row["win_odds_str"] = f"1 in {odds}"

        # Attach pattern + BOB if not present
        row.setdefault("pattern", classify_pattern(candidate))
        row.setdefault("bob_suggestion", bob_sugg(candidate))

        return row

    # ------------------------------------------------------------------
    # RIGHT ENGINE (Jackpot games) – safe normalization for now
    # ------------------------------------------------------------------
    # You can later plug a dedicated jackpot v3.7 scorer here. For now,
    # we normalize any existing confidence or assign a small default.
    if engine_side == "RIGHT":
        # Try to use existing confidence_score if present
        raw_conf = row.get("confidence_score")

        if raw_conf is None:
            # Fallback: derive something from existing fields if available
            # e.g. row.get("score") or some base metric. For now, we default.
            raw_conf = 0.0002  # ~1 in 5000 odds – conservative

        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            conf = 0.0002

        conf = _clamp(conf, 0.000001, 0.5)  # keep in a sensible range

        row["confidence_score"] = conf
        row["base_confidence_score"] = row.get("base_confidence_score", conf)

        odds = _compute_odds_from_conf(conf)
        row["win_odds_1_in"] = odds
        row["confidence_band"] = row.get("confidence_band") or "🤎"

        row["win_odds_str"] = f"1 in {odds}"

        return row

    # ------------------------------------------------------------------
    # Fallback: rows without engine_side (should be rare)
    # ------------------------------------------------------------------
    # We don't want to break anything; just ensure fields exist.
    existing_conf = row.get("confidence_score", 0.0)
    try:
        conf = float(existing_conf)
    except (TypeError, ValueError):
        conf = 0.0

    conf = _clamp(conf, 0.0, 1.0)
    row["confidence_score"] = conf
    row.setdefault("base_confidence_score", conf)

    odds = _compute_odds_from_conf(conf)
    row["win_odds_1_in"] = odds
    row["win_odds_str"] = f"1 in {odds}"
    row.setdefault("confidence_band", "🤎")

    return row
