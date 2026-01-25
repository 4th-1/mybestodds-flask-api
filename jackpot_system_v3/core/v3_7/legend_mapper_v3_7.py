"""
legend_mapper_v3_7.py

My Best Odds Engine v3.7
Legend Mapper for Option-C and Subscriber-Facing Output

Purpose
-------
This module converts INTERNAL legend codes (used throughout v3.7)
into HUMAN-FRIENDLY explanations that appear in:

    - PDF Kits
    - Excel exports
    - Forecast rows
    - Pattern legends
    - Subscriber communication (“learn while you earn”)

Legend codes are produced by playtype_rubik_v3_7.py.
Option-C requires these fields ALWAYS exist:
    legend_code
    rubik_notes

This module guarantees:
    1. All legend codes map cleanly to a subscriber-facing message
    2. Unknown codes DO NOT break the system (fallback provided)
    3. SENTRY NEVER flags missing legend messages
"""

from __future__ import annotations
from typing import Dict, Any


# ---------------------------------------------------------------------------
# MASTER LEGEND DICTIONARY
# ---------------------------------------------------------------------------

LEGEND_TEXT_MAP: Dict[str, str] = {

    # ---------------------------------------------------------
    # CASH 3 LEGENDS
    # ---------------------------------------------------------
    "C3_ST": "Cash 3 • Straight play (highest payout; direct hit).",
    "C3_BX": "Cash 3 • Box play – flexible hit if digits land in any order.",
    "C3_STBX": "Cash 3 • Straight + Box – best of both worlds for tighter patterns.",
    "C3_ST_1OFF": "Cash 3 • Straight + 1-Off – includes backup protection for near-misses.",
    "C3_ST_BX_BOB": "Cash 3 • Straight + Box + BOB Bonus – boosts coverage for strong signals.",
    "C3_PAIR_BACK": "Cash 3 • Back Pair emphasis – repeats or trailing patterns active.",

    # ---------------------------------------------------------
    # CASH 4 LEGENDS
    # ---------------------------------------------------------
    "C4_ST": "Cash 4 • Straight only – highest precision hit required.",
    "C4_BX": "Cash 4 • Box play – pays when the digits appear in any order.",
    "C4_STBX": "Cash 4 • Straight + Box – broader coverage for reliable patterns.",
    "C4_ST_1OFF": "Cash 4 • Straight + 1-Off – protection from near-miss outcomes.",
    "C4_ST_BX_BOB": "Cash 4 • Straight + Box + BOB Bonus for very strong indicators.",
    "C4_PAIR_BACK": "Cash 4 • Back Pair strategy – repeating or weighted back-end patterns.",

    # ---------------------------------------------------------
    # MEGA MILLIONS LEGENDS
    # ---------------------------------------------------------
    "MM_STD": "Mega Millions • Standard play – best for balanced pattern days.",
    "MM_STD_MB": "Mega Millions • Standard + MB-Focus – targets strong Mega Ball alignment.",

    # ---------------------------------------------------------
    # POWERBALL LEGENDS
    # ---------------------------------------------------------
    "PB_STD": "Powerball • Standard play – use when the general pattern aligns.",
    "PB_STD_PB": "Powerball • Standard + PB-Focus – highlights strong Power Ball probability.",

    # ---------------------------------------------------------
    # CASH4LIFE LEGENDS
    # ---------------------------------------------------------
    "C4L_STD": "Cash 4 Life • Standard play – balanced number alignment.",
    "C4L_STD_MB": "Cash 4 Life • Standard + Cash Ball focus – enhanced end-digit alignment.",

    # ---------------------------------------------------------
    # GENERIC / SAFETY FALLBACK
    # ---------------------------------------------------------
    "GEN_STD": "Standard recommended play – stable but not a high-confidence pattern.",
}


# ---------------------------------------------------------------------------
# FALLBACK MESSAGE
# ---------------------------------------------------------------------------

DEFAULT_LEGEND_TEXT = (
    "Standard recommended play – system fallback used. "
    "Confidence stable but not strong enough for enhanced play types."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def map_legend_code(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures every row has a clean subscriber-facing message
    mapped from its internal legend_code.

    Adds / overwrites the field:
        row["legend_text"]

    This is SAFE for:
        - Option-C
        - SENTRY v3.7
        - left or right engine rows
    """

    code = str(row.get("legend_code", "")).upper().strip()

    if code in LEGEND_TEXT_MAP:
        row["legend_text"] = LEGEND_TEXT_MAP[code]
    else:
        row["legend_text"] = DEFAULT_LEGEND_TEXT

    return row


# Exported functions for engine_core_v3_7 / run_kit_v3_7
EXPORTED_FUNCTIONS = ["map_legend_code"]
