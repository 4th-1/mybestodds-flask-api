from __future__ import annotations

# ---------------------------------------------------------------------------
# STANDARD LIB IMPORTS (MUST COME FIRST)
# ---------------------------------------------------------------------------

import os
import sys
import datetime
from typing import List, Dict, Any, Optional

# Sentinel (authoritative)
from core.v3_7.sentinel_engine_v3_7 import sentinel_filter_jackpot_rows

# ---------------------------------------------------------------------------
# PATH SETUP (ORDER IS CRITICAL — DO NOT MOVE)
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ENGINES_ROOT = os.path.join(PROJECT_ROOT, "engines")
if ENGINES_ROOT not in sys.path:
    sys.path.insert(0, ENGINES_ROOT)

V37_RIGHTSIDE_ROOT = os.path.join(ENGINES_ROOT, "rightside_v3_7")
if V37_RIGHTSIDE_ROOT not in sys.path:
    sys.path.insert(0, V37_RIGHTSIDE_ROOT)

# ---------------------------------------------------------------------------
# IMPORTS — v3.7 CORE
# ---------------------------------------------------------------------------

from audit.sentinel_rules_v3_7 import is_valid_draw_day

from core.v3_7.mmfsn_resonance import apply_cash_mmfsn_resonance
from core.v3_7.phase_firewall import (
    assert_no_personal_inputs,
    assert_mmfsn_sets_only,
)

try:
    from core.v3_7.phase_firewall import enforce_phase_firewall
except Exception:
    enforce_phase_firewall = None

from core.v3_7.score_fx_v3_7 import compute_scores_for_row
from core.v3_7.playtype_rubik_v3_7 import apply_playtype_rubik
from core.v3_7.option_c_logic import sanitize_option_c
from core.v3_7.legend_mapper_v3_7 import map_legend_code

# ---------------------------------------------------------------------------
# IMPORT — RIGHT ENGINE (ROBUST)
# ---------------------------------------------------------------------------

build_engine_for_game = None
_errors: List[str] = []

try:
    from rightside_engine_v3_6 import build_engine_for_game as _be
    build_engine_for_game = _be
except Exception as e:
    _errors.append(str(e))

if build_engine_for_game is None:
    try:
        from core.v3_7.rightside_engine_v3_6 import build_engine_for_game as _be
        build_engine_for_game = _be
    except Exception as e:
        _errors.append(str(e))

if build_engine_for_game is None:
    raise ImportError("\n".join(_errors))

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

CASH3_SESSIONS = ["MIDDAY", "EVENING", "NIGHT"]
CASH4_SESSIONS = ["MIDDAY", "EVENING", "NIGHT"]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _to_iso_date(date_str: str) -> str:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return datetime.datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")


def _safe_upper_session(s: str) -> str:
    return (s or "").strip().upper()


def _display_game_name(game_key: str) -> str:
    return {
        "megamillions": "MegaMillions",
        "powerball": "Powerball",
        "cash4life": "Cash4Life",
    }.get(game_key.lower(), game_key)


# =============================================================================
# ENGINE
# =============================================================================

class MyBestOddsEngineV37:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.subscriber: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # SAFE MMFSN WRAPPER
    # ------------------------------------------------------------------
    def _apply_mmfsn_resonance_safe(self, picks, subscriber, game, session, draw_date):
        try:
            return apply_cash_mmfsn_resonance(picks, subscriber)
        except TypeError:
            return apply_cash_mmfsn_resonance(
                picks=picks,
                subscriber=subscriber,
                game=game,
                session=session,
                draw_date=draw_date,
            )

    # ------------------------------------------------------------------
    # PUBLIC API (AUTHORITATIVE)
    # ------------------------------------------------------------------
    def generate_forecast(
        self,
        start_date: str,
        end_date: str,
        subscriber: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        self.subscriber = subscriber

        cur = datetime.datetime.strptime(_to_iso_date(start_date), "%Y-%m-%d").date()
        end = datetime.datetime.strptime(_to_iso_date(end_date), "%Y-%m-%d").date()

        rows: List[Dict[str, Any]] = []

        while cur <= end:
            d = cur.strftime("%Y-%m-%d")

            cash = self._run_cash("Cash3", d) + self._run_cash("Cash4", d)
            cash = self._apply_mmfsn_resonance_safe(cash, subscriber, "CASH", None, d)
            cash = self._transform(cash)

            try:
                assert_mmfsn_sets_only(cash, subscriber)
            except Exception:
                pass

            jackpots = []
            for g in ("megamillions", "powerball", "cash4life"):
                jackpots.extend(self._run_jackpot(g, d, subscriber))

            jackpots = self._transform(jackpots)

            rows.extend(cash + jackpots)
            cur += datetime.timedelta(days=1)

        rows.sort(key=lambda r: float(r.get("confidence_score", 0)), reverse=True)
        rows = self._resolve_ties_with_seed(rows, subscriber)

        if enforce_phase_firewall:
            rows = enforce_phase_firewall(rows)

        return rows

    # ------------------------------------------------------------------