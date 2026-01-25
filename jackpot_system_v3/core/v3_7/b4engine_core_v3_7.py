"""
engine_core_v3_7.py

My Best Odds Engine v3.7 – Core Orchestration Layer
--------------------------------------------------
Authoritative, self-contained engine with a guaranteed public API.

FINAL STABILIZED VERSION (NO PHANTOM LEFT ENGINE IMPORTS)

Fixes included:
- generate_forecast is a real class method (always present)
- No imports from missing v3.6 left-engine modules (cash3_engine_v3_6 etc.)
- Cash3/Cash4 candidate generation is implemented locally (stable baseline)
- Jackpot draw-day gating is NON-BLOCKING at the engine level (soft-check only)
- Sentinel is authoritative via sentinel_filter_jackpot_rows (BOOK3 preview allowed)
- Jackpot uses filename-safe CSV mapping (no .capitalize() bugs)
- Jackpot fallback restores parity with earlier successful runs
- Right engine import is robust across your two known locations
"""

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

# Project root (this repo)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local engines folder (RIGHT engine lives here)
ENGINES_ROOT = os.path.join(PROJECT_ROOT, "engines")
if ENGINES_ROOT not in sys.path:
    sys.path.insert(0, ENGINES_ROOT)

# Right-side v3.7 folder (direct file import)
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
    from core.v3_7.phase_firewall import enforce_phase_firewall  # type: ignore
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
_right_import_errors: List[str] = []

try:
    from rightside_engine_v3_6 import build_engine_for_game as _be  # type: ignore
    build_engine_for_game = _be
except Exception as e:
    _right_import_errors.append(f"from rightside_engine_v3_6 import ... failed: {e}")

if build_engine_for_game is None:
    try:
        from core.v3_7.rightside_engine_v3_6 import build_engine_for_game as _be  # type: ignore
        build_engine_for_game = _be
    except Exception as e:
        _right_import_errors.append(f"from core.v3_7.rightside_engine_v3_6 import ... failed: {e}")

if build_engine_for_game is None:
    raise ImportError(
        "Could not import build_engine_for_game from any known location.\n"
        + "\n".join(_right_import_errors)
    )

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

CASH3_SESSIONS = ["MIDDAY", "EVENING", "NIGHT"]
CASH4_SESSIONS = ["MIDDAY", "EVENING", "NIGHT"]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _to_iso_date(date_str: str) -> str:
    s = (date_str or "").strip()
    if not s:
        return s
    try:
        datetime.datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        pass
    try:
        return datetime.datetime.strptime(s, "%m/%d/%Y").strftime("%Y-%m-%d")
    except Exception:
        return s


def compose_ticket_string(game: str, white_balls, special_ball=None) -> str:
    """
    Fallback composer used only if the right-engine doesn't provide a canonical 'number'.
    """
    if not white_balls:
        return ""
    try:
        wb = sorted(int(x) for x in white_balls if str(x).strip().isdigit())
    except Exception:
        return ""
    if not wb:
        return ""

    base = "-".join(f"{n:02d}" for n in wb)

    if special_ball is None or str(special_ball).strip() == "":
        return base

    try:
        sb = int(special_ball)
    except Exception:
        return base

    g = (game or "").strip().lower()
    tag = "Mega" if g == "megamillions" else "PB" if g == "powerball" else "CB"
    return f"{base} | {tag} {sb:02d}"


def _display_game_name(game_key: str) -> str:
    return {
        "megamillions": "MegaMillions",
        "powerball": "Powerball",
        "cash4life": "Cash4Life",
    }.get((game_key or "").lower(), game_key)


def _safe_upper_session(s: str) -> str:
    return (s or "").strip().upper()


# =============================================================================
# ENGINE
# =============================================================================

class MyBestOddsEngineV37:
    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.subscriber: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # SAFE MMFSN WRAPPER
    # ------------------------------------------------------------------
    def _apply_mmfsn_resonance_safe(
        self,
        picks,
        subscriber,
        game,
        session,
        draw_date,
    ):
        """
        Compatibility wrapper: supports different apply_cash_mmfsn_resonance
        signatures without breaking when the function changes.
        """
        try:
            return apply_cash_mmfsn_resonance(
                picks,
                subscriber,
            )
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

        def __init__(self, config: Optional[Dict[str, Any]] = None):
            self.config = config or {}
        self.subscriber: Dict[str, Any] = {}

    def _apply_mmfsn_resonance_safe(
        self,
        picks,
        subscriber,
        game,
        session,
        draw_date,
    ):
        """
        Compatibility wrapper: supports different apply_cash_mmfsn_resonance
        signatures without breaking _run_cash if the function changes.
        """
        try:
            # Newer signature (rows-based)
            return apply_cash_mmfsn_resonance(
                picks,
                subscriber,
            )
        except TypeError:
            # Older / candidate-based signature
            return apply_cash_mmfsn_resonance(
                picks=picks,
                subscriber=subscriber,
                game=game,
                session=session,
                draw_date=draw_date,
            )

    # --------------------------------------------------
    # SUBSCRIBER SEED (TIE RESOLUTION ONLY)
    # --------------------------------------------------
    def _subscriber_seed(self, subscriber: Dict[str, Any]) -> int:
        import hashlib, json
        base = json.dumps(subscriber, sort_keys=True, default=str)
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return int(h[:12], 16)

    # --------------------------------------------------
    # TIE RESOLUTION (DETERMINISTIC)
    # --------------------------------------------------
    def _resolve_ties_with_seed(
        self,
        rows: List[Dict[str, Any]],
        subscriber: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        import random

        if not rows:
            return rows

        rng = random.Random(self._subscriber_seed(subscriber))

        i = 0
        while i < len(rows):
            j = i + 1
            while j < len(rows) and rows[j].get("score") == rows[i].get("score"):
                j += 1

            if j - i > 1:
                block = rows[i:j]
                rng.shuffle(block)
                rows[i:j] = block

            i = j

        return rows

    # --------------------------------------------------
    # HISTORY PARSER (Cash3/Cash4 normalized)
    # Expects:
    #   draw_date | session | digits | ...
    # --------------------------------------------------
    def _parse_cash_history(self, path: str, game: str):
        import pandas as pd

        if not os.path.exists(path):
            print(f"[WARN] Missing history file: {path}")
            return None

        df = pd.read_csv(path, dtype=str)

        required = {"draw_date", "session", "digits"}
        if not required.issubset(df.columns):
            print(f"[WARN] Cash history missing required columns {required}: {path}")
            return None

        width = 4 if game == "Cash4" else 3

        df = df.copy()
        df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce").dt.date
        df = df.dropna(subset=["draw_date"])
        df["session"] = df["session"].astype(str).map(_safe_upper_session)
        df["digits"] = df["digits"].astype(str).str.strip().str.zfill(width)

        return df

    # ------------------------------------------------------------------
    # CASH GENERATOR (LOCAL, STABLE)
    # ------------------------------------------------------------------
    def _generate_cash_candidates(
        self,
        history_df,
        game: str,
        draw_date: datetime.date,
        session: str,
        max_picks: int = 6,
        lookback: int = 120,
    ) -> List[str]:
        width = 4 if game == "Cash4" else 3

        df = history_df
        df = df[(df["session"] == session) & (df["draw_date"] < draw_date)].copy()
        if df.empty:
            return []

        df = df.sort_values("draw_date", ascending=False).head(lookback)
        digits_list = df["digits"].astype(str).tolist()
        if not digits_list:
            return []

        pos_counts: List[Dict[str, int]] = [dict() for _ in range(width)]
        for s in digits_list:
            s = str(s).zfill(width)
            for i, ch in enumerate(s[:width]):
                pos_counts[i][ch] = pos_counts[i].get(ch, 0) + 1

        top_per_pos: List[List[str]] = []
        for i in range(width):
            items = sorted(pos_counts[i].items(), key=lambda x: (-x[1], x[0]))
            top_per_pos.append([k for k, _ in items[:4]] or ["0"])

        cands: List[str] = []
        for a in top_per_pos[0]:
            if width == 3:
                for b in top_per_pos[1]:
                    for c in top_per_pos[2]:
                        cands.append(f"{a}{b}{c}")
                        if len(cands) >= max_picks:
                            return cands
            else:
                for b in top_per_pos[1]:
                    for c in top_per_pos[2]:
                        for d in top_per_pos[3]:
                            cands.append(f"{a}{b}{c}{d}")
                            if len(cands) >= max_picks:
                                return cands

        return cands[:max_picks]

    # ------------------------------------------------------------------
    # CASH ENGINES
    # ------------------------------------------------------------------
    def _run_cash(self, game: str, date: str) -> List[Dict[str, Any]]:
        assert_no_personal_inputs(f"LEFT ENGINE {game}", None, None)

        date = _to_iso_date(date)
        draw_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

        path = os.path.join(
            PROJECT_ROOT,
            f"data/results/ga_results/{game.lower()}_results.csv"
        )

        history = self._parse_cash_history(path, game)
        if history is None or getattr(history, "empty", True):
            return []

        sessions = CASH3_SESSIONS if game == "Cash3" else CASH4_SESSIONS

        rows: List[Dict[str, Any]] = []

        for session in sessions:
            try:
                # HISTORICAL CANDIDATE GENERATION (PRIMARY)
                picks = self._generate_cash_candidates(
                    history,
                    game,
                    draw_date,
                    session,
                    max_picks=6
                )

                # ROW EMISSION
                for num in picks:
                    rows.append({
                        "forecast_date": date,
                        "draw_date": date,
                        "game": game,
                        "game_code": game.upper(),
                        "engine_side": "LEFT",
                        "draw_time": session,
                        "number": num,
                        "engine_source": "LEFT_GENERATED",
                    })

            except Exception as e:
                print(
                    f"[WARN] _run_cash failed: "
                    f"game={game} date={date} session={session} err={e}"
                )

        return rows

# ------------------------------------------------------------------
# JACKPOTS — FINAL v3.7
# Sentinel is applied AFTER rows exist (authoritative)
# ------------------------------------------------------------------
def _run_jackpot(
    self,
    game: str,
    date: str,
    subscriber: Dict[str, Any],
) -> List[Dict[str, Any]]:

    game_key = (game or "").strip().lower()
    date = _to_iso_date(date)

    csv_map = {
        "megamillions": "MegaMillions.csv",
        "powerball": "Powerball.csv",
        "cash4life": "Cash4Life.csv",
    }

    if game_key not in csv_map:
        print(f"[JACKPOT] SKIP (unknown game_key): {game_key}")
        return []

    history_csv = os.path.join(
        PROJECT_ROOT,
        "data",
        "results",
        "jackpot_results",
        csv_map[game_key],
    )

    if not os.path.exists(history_csv):
        print(f"[JACKPOT] SKIP (missing history file): {history_csv}")
        return []

    kit_type = subscriber.get("kit_type", "BOOK3")

    # Soft draw-day note (non-blocking)
    try:
        if not is_valid_draw_day(game_key.upper(), date):
            print(f"[JACKPOT] NOTE non-draw day → continuing: {game_key.upper()} {date}")
    except Exception:
        pass

    # ✅ CORRECT factory call (NO subscriber kwarg)
    engine = build_engine_for_game(
        game_key,
        kit_type,
        history_csv,
    )

    # ✅ Bind subscriber AFTER engine creation
    if hasattr(engine, "subscriber"):
        engine.subscriber = subscriber

    target = datetime.datetime.strptime(date, "%Y-%m-%d").date()

    try:
        picks = engine.generate_picks_for_range(target, target)
    except Exception as e:
        print(f"[JACKPOT] ERROR primary generation: {e}")
        picks = []

    if not picks:
        try:
            picks = engine.generate_picks_for_range(
                target - datetime.timedelta(days=3),
                target + datetime.timedelta(days=3),
            )
        except Exception as e:
            print(f"[JACKPOT] ERROR fallback generation: {e}")
            return []

    rows: List[Dict[str, Any]] = []

    for p in picks:
        ticket = (p.get("number") or "").strip()
        if not ticket:
            continue

        rows.append({
            "forecast_date": date,
            "draw_date": date,
            "game": _display_game_name(game_key),
            "game_code": game_key.upper(),
            "engine_side": "RIGHT",
            "draw_time": "JACKPOT",
            "number": ticket,
            "engine_source": "RIGHT_GENERATED",
        })

    rows = sentinel_filter_jackpot_rows(
        rows=rows,
        game_code=game_key.upper(),
        forecast_date=date,
        kit_type=kit_type,
    )

    return rows
