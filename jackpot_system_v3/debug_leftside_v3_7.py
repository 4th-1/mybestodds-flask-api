"""
debug_leftside_v3_7.py
---------------------------------------------------------
Purpose:
Run Cash3 or Cash4 predictions using the NEW v3.7 Left Engine
(stats-only base confidence + overlay-light timing alignment).

Usage:
python debug_leftside_v3_7.py --game Cash3 --session NIGHT --date 2025-12-01

Outputs:
- Base confidence (stats only)
- Adjusted confidence (stats + overlays, ±5%)
- Best odds (1 in n)
- Confidence band (🟩 🟨 🤎 🚫)
- Pattern type, sum range, twin-pressure, frequency score
- BOB (Best Odds Bonus) recommendations
"""

import argparse
import pandas as pd
from datetime import datetime

from core.score_left_v3_7 import (
    score_pool_left,
    classify_pattern,
    bob_sugg,
)

from core.overlay_loader_v3_7 import (
    load_all_overlays,
    ENGINE_LEFT
)


# --------------------------------------------------------
# Utility
# --------------------------------------------------------

def load_history(game: str):
    """Load standardized Cash3 or Cash4 CSV history."""
    csv_path = "history_cash3_2025.csv" if game == "Cash3" else "history_cash4_2025.csv"
    df = pd.read_csv(csv_path, dtype=str)
    return df


def get_meta_for_date(game: str, draw_date: str, session: str):
    """
    Build metadata for overlay-light scoring:
      - moon_phase
      - day_of_week
      - planetary_hour
      - weather_code (future expansion)
    """
    overlay_ctx = load_all_overlays(target=ENGINE_LEFT)

    # Derive day-of-week
    dow = datetime.strptime(draw_date, "%Y-%m-%d").strftime("%a")  # Mon, Tue, etc.

    # 🌌 SWISS EPHEMERIS INTEGRATION - Real astronomical calculations!
    try:
        from core.swiss_ephemeris_v3_7 import get_astronomical_context
        astro_data = get_astronomical_context(draw_date, session)
        
        return {
            "moon_phase": astro_data.get("moon_phase", "FULL"),
            "moon_illumination": astro_data.get("moon_illumination", 0.5),
            "day_of_week": astro_data.get("day_of_week", dow),
            "planetary_hour": astro_data.get("planetary_hour", session),
            "sun_sign": astro_data.get("sun_sign", "Unknown"),
            "moon_sign": astro_data.get("moon_sign", "Unknown"),
            "north_node_sign": astro_data.get("north_node_sign", "Unknown"),
            "calculation_source": astro_data.get("calculation_source", "Unknown"),
            "weather_code": None,
            "bias_pattern": None,
        }
    except ImportError:
        # Fallback to old fake system
        planet_key = session  # NIGHT/MIDDAY mapping (customize later)
        moon_phase = "FULL"  # Replace later once moon phase JSON mapping is added
        
        return {
            "moon_phase": moon_phase,
            "day_of_week": dow,
            "planetary_hour": planet_key,
            "calculation_source": "Debug_Fallback",
            "weather_code": None,
            "bias_pattern": None,
        }


# --------------------------------------------------------
# Main Runner
# --------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", required=True, choices=["Cash3", "Cash4"])
    parser.add_argument("--session", required=True, choices=["MIDDAY", "EVENING", "NIGHT"])
    parser.add_argument("--date", required=False)
    parser.add_argument("--pool", required=False)

    args = parser.parse_args()

    draw_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"\n=== v3.7 LEFT-SIDE DEBUG RUN ===")
    print(f"Game: {args.game}")
    print(f"Draw date: {draw_date}")
    print(f"Session: {args.session}")
    print("-------------------------------------")

    # Load history
    history = load_history(args.game)

    # Determine base pool
    if args.pool:
        base_pool = args.pool.split(",")
    else:
        # A small default test group for Cash3/Cash4
        base_pool = ["047", "187", "724", "305", "361"] if args.game == "Cash3" else ["0106", "1248", "5560", "6789"]

    # Build meta (alignment) for this date/session
    meta = get_meta_for_date(args.game, draw_date, args.session)

    # Map to each candidate
    meta_map = {cand: meta for cand in base_pool}

    # Run scoring
    results_df = score_pool_left(
        history_df=history,
        game=args.game,
        base_pool=base_pool,
        near_miss_pressure=0.35,
        meta_map=meta_map,
    )

    # Show results
    print("\nResults:")
    print(results_df.to_string(index=False))
