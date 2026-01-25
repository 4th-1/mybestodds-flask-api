# core/best_odds_engine.py

from pathlib import Path
import json
from typing import Dict, Any


# ------------------------------------------------------
# OFFICIAL ODDS LOADER (Flexible: base_odds / official_odds / odds)
# ------------------------------------------------------

def load_official_odds(root: Path) -> Dict[str, int]:
    """
    Load official odds from lottery_odds.json.

    Accepts ANY of the following keys per game entry:
      - base_odds
      - official_odds
      - odds

    This makes V3 fully flexible with uploaded user files.
    """

    odds_path = root / "data" / "lottery_odds.json"

    # --- Load the JSON file safely ---
    try:
        with odds_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"[BEST ODDS ERROR] lottery_odds.json not found at: {odds_path}"
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"[BEST ODDS ERROR] lottery_odds.json is not valid JSON! {e}"
        )

    parsed: Dict[str, int] = {}

    # --- Parse each game's odds, accepting flexible formats ---
    for game, fields in raw.items():

        # Accept *any* of the common keys
        val = (
            fields.get("base_odds")
            or fields.get("official_odds")
            or fields.get("odds")
        )

        if val is None:
            raise KeyError(
                f"[BEST ODDS ERROR] Game '{game}' is missing an odds value.\n"
                f"Must include one of: base_odds, official_odds, odds.\n"
                f"Entry was: {fields}"
            )

        try:
            parsed[game] = int(val)
        except Exception:
            raise ValueError(
                f"[BEST ODDS ERROR] Odds for game '{game}' must be numeric. "
                f"Got: {val}"
            )

    return parsed


# ------------------------------------------------------
# BEST ODDS CALCULATOR FOR A SINGLE DAY
# (Your V3 system calls this after rounding confidence)
# ------------------------------------------------------

def compute_best_odds_for_day(
    confidence: int,
    picks: Dict[str, Any],
    official_odds: Dict[str, int]
) -> Dict[str, Any]:
    """
    Given a rounded Best Odds Confidence Score (0–100),
    compute the adjusted '1 in N' Best Odds AFTER our Smart Logic.

    Formula:
      effective = max(official / (1 + confidence/50), floor_limit)

    Hard limits:
      Cash3        never better than 1 in 10
      Cash4        never better than 1 in 30
      MegaMillions never better than 1 in 250_000
      Powerball    never better than 1 in 250_000
      Cash4Life    never better than 1 in 50_000
    """

    # Hard safety caps
    limits = {
        "Cash3": 10,
        "Cash4": 30,
        "MegaMillions": 250_000,
        "Powerball": 250_000,
        "Cash4Life": 50_000,
    }

    result = {}

    for game, base in official_odds.items():
        # Improvement factor grows with confidence
        improvement = 1 + (confidence / 50)

        eff = int(max(base / improvement, limits.get(game, base)))

        result[game] = {
            "official_odds": base,
            "effective_odds": eff,
            "improvement_factor": base / eff,
        }

    return result
