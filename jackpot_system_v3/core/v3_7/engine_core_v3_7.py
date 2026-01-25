from __future__ import annotations

# ---------------------------------------------------------------------------
# STANDARD LIB IMPORTS
# ---------------------------------------------------------------------------

import os
import sys
import datetime
from typing import List, Dict, Any, Optional

# Sentinel (authoritative)
from core.v3_7.sentinel_engine_v3_7 import sentinel_filter_jackpot_rows

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ENGINES_ROOT = os.path.join(PROJECT_ROOT, "engines")
if ENGINES_ROOT not in sys.path:
    sys.path.insert(0, ENGINES_ROOT)

# ---------------------------------------------------------------------------
# IMPORTS — v3.7 CORE
# ---------------------------------------------------------------------------

from audit.sentinel_rules_v3_7 import is_valid_draw_day
from core.v3_7.mmfsn_resonance import apply_cash_mmfsn_resonance
from core.v3_7.phase_firewall import assert_no_personal_inputs, assert_mmfsn_sets_only

try:
    from core.v3_7.phase_firewall import enforce_phase_firewall
except Exception:
    enforce_phase_firewall = None

from core.v3_7.score_fx_v3_7 import compute_scores_for_row
from core.v3_7.playtype_rubik_v3_7 import apply_playtype_rubik
from core.v3_7.option_c_logic import sanitize_option_c
from core.v3_7.legend_mapper_v3_7 import map_legend_code
from core.v3_7.jackpot_confidence_v3_7 import compute_jackpot_confidence
import logging
logging.basicConfig(level=logging.WARNING)


# Right engine loader
from core.v3_7.rightside_engine_v3_6 import build_engine_for_game

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
    # PUBLIC API
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

            jackpots: List[Dict[str, Any]] = []
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
    # JACKPOT ENGINE (AUDITED & FIXED)
    # ------------------------------------------------------------------
    def _run_jackpot(
        self,
        game_key: str,
        date_str: str,
        subscriber: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        # is_valid_draw_day EXPECTS A DICT WITH game_code AND forecast_date
        if not is_valid_draw_day({"game_code": game_key.upper(), "forecast_date": date_str}):
            return []

        # Map game to specific jackpot history CSV file
        game_csv_map = {
            "megamillions": "megamillions_2025.csv",
            "powerball": "powerball_2025.csv",
            "cash4life": "cash4life_2025.csv"
        }
        
        csv_filename = game_csv_map.get(game_key.lower())
        if not csv_filename:
            return []  # Unknown game
        
        # Path to separated-ball jackpot CSV (one level above jackpot_system_v3)
        history_csv_path = os.path.join(PROJECT_ROOT, "..", "results", "jackpot_history", csv_filename)
        history_csv_path = os.path.abspath(history_csv_path)
        
        # Check if file exists
        if not os.path.exists(history_csv_path):
            logging.warning(f"[JACKPOT] History CSV not found: {history_csv_path}")
            return []  # No history, no predictions
        
        engine = build_engine_for_game(
            game_key,
            subscriber.get("kit_type", "BOOK3"),
            history_csv_path,
        )
        if not engine:
            return []

        target = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        raw = engine.generate_picks_for_range(target, target) or []
        logging.error(
            f"[DEBUG JACKPOT] {game_key} {date_str} raw_candidates = {len(raw)}"
)


        # --------------------------------------------------
        # Build pre-sentinel jackpot rows
        # --------------------------------------------------
        rows: List[Dict[str, Any]] = []
        for r in raw:
            number = r.get("number")
            if not number:
                continue

            rows.append({
                "forecast_date": date_str,
                "draw_date": date_str,
                "game": _display_game_name(game_key),
                "game_code": game_key.upper(),
                "engine_side": "RIGHT",
                "draw_time": "JACKPOT",
                "number": number,
                "engine_source": "RIGHT_GENERATED",

                # 🔍 VISIBILITY TAGS
                "is_jackpot": True,
                "row_type": "JACKPOT",
            })

        if not rows:
            return []
        # --------------------------------------------------
        # Sentinel filter (authoritative)
        # --------------------------------------------------
        filtered = sentinel_filter_jackpot_rows(
            rows=rows,
            game_code=game_key.upper(),
            forecast_date=date_str,
            kit_type=subscriber.get("kit_type", "BOOK3"),
        )

        # --------------------------------------------------
        # JACKPOT AUDIT TRACE
        # --------------------------------------------------
        if not filtered:
            # Sentinel rejected all jackpot rows
            for r in rows:
                r["jackpot_status"] = "FILTERED"
                r["jackpot_filter_reason"] = "SENTINEL_REJECT"
            return []

        # Sentinel passed at least one row
        for r in filtered:
            r["jackpot_status"] = "PASSED"
            r["jackpot_filter_reason"] = None

        return filtered

    # ------------------------------------------------------------------
    # TIE RESOLUTION
    # ------------------------------------------------------------------
    def _subscriber_seed(self, subscriber: Dict[str, Any]) -> int:
        import hashlib, json
        base = json.dumps(subscriber, sort_keys=True, default=str)
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return int(h[:12], 16)

    def _resolve_ties_with_seed(
        self,
        rows: List[Dict[str, Any]],
        subscriber: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        import random
        if not rows:
            return rows

        rng = random.Random(self._subscriber_seed(subscriber))
        i = 0

        while i < len(rows):
            j = i + 1
            while j < len(rows) and rows[j].get("confidence_score") == rows[i].get("confidence_score"):
                j += 1

            if j - i > 1:
                block = rows[i:j]
                rng.shuffle(block)
                rows[i:j] = block

            i = j

        return rows

    # ------------------------------------------------------------------
    # TRANSFORM
    # ------------------------------------------------------------------
    def _transform(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        for r in rows:
            r = compute_scores_for_row(r, self.config)
            r = self._apply_confidence_deltas(r)
            r = compute_jackpot_confidence(r)   # jackpot-only logic
            r = apply_playtype_rubik(r)
            r = sanitize_option_c(r)
            r = map_legend_code(r)
            out.append(r)

        return out

    # ------------------------------------------------------------------
    # CONFIDENCE DELTAS
    # ------------------------------------------------------------------
    def _apply_confidence_deltas(self, row: Dict[str, Any]) -> Dict[str, Any]:
        delta = 0.0

        # -------------------------
        # MMFSN DELTA
        # -------------------------
        mmfsn = set(self.subscriber.get("mmfsn", []))
        number = str(row.get("number", ""))

        if number in mmfsn and row.get("mmfsn_due", False):
            delta += 1.5

        # -------------------------
        # DAY-OF-WEEK DELTA
        # -------------------------
        DAY_BIAS = {
            "Mon": 0.2, "Tue": 0.4, "Wed": 0.6,
            "Thu": 0.8, "Fri": 1.0,
            "Sat": 0.5, "Sun": 0.3
        }

        try:
            d = datetime.datetime.strptime(row["draw_date"], "%Y-%m-%d")
            delta += DAY_BIAS.get(d.strftime("%a"), 0.0)
        except Exception:
            pass

        # -------------------------
        # SESSION DELTA (CASH ONLY)
        # -------------------------
        if row.get("game_code") in {"CASH3", "CASH4"}:
            SESSION_BIAS = {
                "MIDDAY": 0.75,
                "EVENING": 0.5,
                "NIGHT": 0.25
            }
            delta += SESSION_BIAS.get(row.get("draw_time"), 0.0)

        # -------------------------
        # HARD CAP
        # -------------------------
        delta = min(delta, 3.0)

        row["confidence_score"] = round(
            float(row.get("confidence_score", 0)) + delta, 1
        )

        return row

        mmfsn = set(self.subscriber.get("mmfsn", []))
        number = str(row.get("number", ""))

        if number in mmfsn and row.get("mmfsn_due", False):
            delta += 1.5

        # -------------------------
        # DAY-OF-WEEK DELTA
        # -------------------------
        DAY_BIAS = {
            "Mon": 0.2, "Tue": 0.4, "Wed": 0.6,
            "Thu": 0.8, "Fri": 1.0,
            "Sat": 0.5, "Sun": 0.3
        }

        try:
            d = datetime.datetime.strptime(row["draw_date"], "%Y-%m-%d")
            delta += DAY_BIAS.get(d.strftime("%a"), 0.0)
        except Exception:
            pass

        # -------------------------
        # SESSION DELTA (CASH ONLY)
        # -------------------------
        if row.get("game_code") in {"CASH3", "CASH4"}:
            SESSION_BIAS = {
                "MIDDAY": 0.75,
                "EVENING": 0.5,
                "NIGHT": 0.25
            }
            delta += SESSION_BIAS.get(row.get("draw_time"), 0.0)

        # -------------------------
        # HARD CAP
        # -------------------------
        delta = min(delta, 3.0)

        row["confidence_score"] = round(
            float(row.get("confidence_score", 0)) + delta, 1
        )

        return row

    # ------------------------------------------------------------------
    # CASH ENGINE
    # ------------------------------------------------------------------
    def _run_cash(self, game: str, date: str) -> List[Dict[str, Any]]:
        assert_no_personal_inputs(f"LEFT ENGINE {game}", None, None)

        date = _to_iso_date(date)
        draw_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

        path = os.path.join(
            PROJECT_ROOT,
            f"data/results/ga_results/{game.lower()}_results.csv"
        )

        if not os.path.exists(path):
            return []

        import pandas as pd
        df = pd.read_csv(path, dtype=str)

        required = {"draw_date", "session", "digits"}
        if not required.issubset(df.columns):
            return []

        width = 4 if game == "Cash4" else 3

        df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce").dt.date
        df = df.dropna(subset=["draw_date"])
        df["session"] = df["session"].astype(str).map(_safe_upper_session)
        df["digits"] = df["digits"].astype(str).str.zfill(width)

        sessions = CASH3_SESSIONS if game == "Cash3" else CASH4_SESSIONS
        rows: List[Dict[str, Any]] = []

        for session in sessions:
            hist = df[(df["session"] == session) & (df["draw_date"] < draw_date)]
            if hist.empty:
                continue

            recent = hist.sort_values("draw_date", ascending=False).head(120)
            for n in recent["digits"].tolist()[:6]:
                rows.append({
                    "forecast_date": date,
                    "draw_date": date,
                    "game": game,
                    "game_code": game.upper(),
                    "engine_side": "LEFT",
                    "draw_time": session,
                    "number": n,
                    "engine_source": "LEFT_GENERATED",
                })

        return rows
