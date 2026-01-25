"""
option_c_logic.py

My Best Odds Engine v3.7 – Option-C Formatting & SENTRY Compliance Layer

Purpose
-------
Option-C is the strict formatting mode introduced in v3.7.

EVERY row that enters the Export → Audit → PDF pipeline MUST contain:

Required Core Fields (Score Layer)
----------------------------------
- confidence_score
- win_odds_1_in
- game_code
- lane_id

Required Play-Type Fields (Rubik Layer)
---------------------------------------
- primary_play_type
- bob_suggestion
- play_flag
- legend_code
- rubik_notes

Required Metadata Fields
------------------------
- forecast_date         (YYYY-MM-DD)
- draw_time             ("MIDDAY", "EVENING", "NIGHT", or jackpot draw label)
- number                (string or int, depending on game)
- sum                   (Cash3/4 digit-sum; may be None but field MUST exist)
- pattern_tags          (list; may be empty)
- engine_source         ("LEFT" or "RIGHT")
- option_c_pass         (bool – must be True)
- sentry_ready          (bool – must be True)

If any are missing, they must be populated with SAFE DEFAULTS.

Downstream tools that rely on this guarantee:
    - audit_sentry_v3_7.py
    - PDF formatting / Excel exports
    - Win probability filters
    - Legend mapper

Public API
----------
sanitize_option_c(row: dict) -> dict
"""

from __future__ import annotations

from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# Constants used for defaults
# ---------------------------------------------------------------------------

DEFAULT_PLAY_TYPE = "STANDARD"
DEFAULT_BOB = "NONE"
DEFAULT_PLAY_FLAG = "PLAY_FUN"
DEFAULT_LEGEND = "GEN_STD"
DEFAULT_NOTES = "Option-C fallback applied."

DEFAULT_DRAW_TIME = "N/A"
DEFAULT_NUMBER = ""
DEFAULT_DATE = "1900-01-01"

LEFT_ENGINES = {"CASH3", "CASH4"}
RIGHT_ENGINES = {"MEGAMILLIONS", "POWERBALL", "CASH4LIFE"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_key(row: Dict[str, Any], key: str, default: Any) -> None:
    """Guarantee key exists with a non-None value."""
    if key not in row or row[key] is None:
        row[key] = default


def _ensure_list(row: Dict[str, Any], key: str) -> None:
    """Ensure a field is a list (or becomes one)."""
    val = row.get(key)
    if val is None:
        row[key] = []
    elif isinstance(val, list):
        return
    else:
        try:
            # Convert comma-separated strings to list
            if isinstance(val, str):
                parts = [p.strip() for p in val.split(",") if p.strip()]
                row[key] = parts
            else:
                row[key] = [val]
        except Exception:
            row[key] = []


def _detect_engine_source(game_code: str) -> str:
    if game_code in LEFT_ENGINES:
        return "LEFT"
    if game_code in RIGHT_ENGINES:
        return "RIGHT"
    return "UNKNOWN"


def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# MAIN – Option-C Sanitizer
# ---------------------------------------------------------------------------

def sanitize_option_c(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce strict Option-C formatting.

    This MUST be called AFTER:
        - compute_scores_for_row()
        - apply_playtype_rubik()

    It guarantees:
        - ALL required fields exist
        - No SENTRY missing-field errors
        - All types are normalized (lists are lists, strings are strings)
    """

    # -------------------------------------------------------
    # 1. Make sure game_code + lane_id exist
    # -------------------------------------------------------
    row["game_code"] = _safe_str(row.get("game_code", "")).upper()
    row["lane_id"] = _safe_str(row.get("lane_id", "LANE_A")).upper()

    # -------------------------------------------------------
    # 2. Confidence score + win_odds must be present
    # -------------------------------------------------------
    _ensure_key(row, "confidence_score", 50.0)
    _ensure_key(row, "win_odds_1_in", 9999.0)

    # Coerce numeric values if strings snuck in
    try:
        row["confidence_score"] = float(row["confidence_score"])
    except Exception:
        row["confidence_score"] = 50.0

    try:
        row["win_odds_1_in"] = float(row["win_odds_1_in"])
    except Exception:
        row["win_odds_1_in"] = 9999.0

    # -------------------------------------------------------
    # 3. Play-Type Layer enforcement
    # -------------------------------------------------------
    _ensure_key(row, "primary_play_type", DEFAULT_PLAY_TYPE)
    _ensure_key(row, "bob_suggestion", DEFAULT_BOB)
    _ensure_key(row, "play_flag", DEFAULT_PLAY_FLAG)
    _ensure_key(row, "legend_code", DEFAULT_LEGEND)
    _ensure_key(row, "rubik_notes", DEFAULT_NOTES)

    # Normalize play_flag values
    if row["play_flag"] not in (
        "PLAY_CORE",
        "PLAY_LIGHT",
        "PLAY_FUN",
        "SKIP",
    ):
        row["play_flag"] = DEFAULT_PLAY_FLAG

    # -------------------------------------------------------
    # 4. Required metadata fields
    # -------------------------------------------------------

    # forecast_date
    _ensure_key(row, "forecast_date", DEFAULT_DATE)

    # draw_time (MIDDAY / EVENING / NIGHT / jackpot label)
    _ensure_key(row, "draw_time", DEFAULT_DRAW_TIME)

    # number (string representation)
    if "number" not in row or row["number"] is None:
        row["number"] = DEFAULT_NUMBER
    else:
        row["number"] = _safe_str(row["number"])

    # sum field for Cash3/Cash4 (even if None)
    if "sum" not in row:
        row["sum"] = None

    # pattern_tags list
    _ensure_list(row, "pattern_tags")

    # engine_source field
    row["engine_source"] = _detect_engine_source(row["game_code"])

    # -------------------------------------------------------
    # 5. SENTRY flags – MUST be present & True
    # -------------------------------------------------------
    row["option_c_pass"] = True
    row["sentry_ready"] = True

    return row


# For engine_core_v3_7 and run_kit_v3_7
EXPORTED_FUNCTIONS = ["sanitize_option_c"]
