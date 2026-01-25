"""
playtype_rubik_v3_7.py

My Best Odds Engine v3.7 – Play-Type Rubik Logic

Purpose
-------
This module centralizes ALL play-type decision logic for:

- Cash3
- Cash4
- MegaMillions
- Powerball
- Cash4Life

It converts:
    game + lane + confidence + odds + pattern tags (triples, quads, etc.)

into a standardized, Option-C–ready block:

    {
        "primary_play_type": <str>,   # e.g. "STRAIGHT", "BOX", "STRAIGHT+BOX", "STANDARD", "MB_ONLY"
        "bob_suggestion":    <str>,   # e.g. "ADD_BOX_FOR_SAFETY", "ADD_1_OFF", "NONE"
        "play_flag":         <str>,   # e.g. "PLAY_CORE", "PLAY_LIGHT", "SKIP"
        "legend_code":       <str>,   # compact code for legend_mapper_v3_7
        "rubik_notes":       <str>,   # short human-readable rationale
    }

This module does NOT:
- compute confidence_score
- compute win_odds_1_in
- perform SENTRY checks

Those are handled by:
- score_fx_v3_7.py     (confidence / odds)
- option_c_logic.py    (field enforcement, Option-C spec)
- legend_mapper_v3_7.py (code → human text)

But SENTRY v3.7 EXPECTS this module to ALWAYS provide:
    primary_play_type, bob_suggestion, play_flag, legend_code

even if the input row is incomplete. When in doubt, safe defaults are used.

Public API
----------
- apply_playtype_rubik(row: dict) -> dict

Row Requirements (inputs)
-------------------------
At minimum, the row dict passed in SHOULD contain:

    row["game_code"]           # "CASH3" | "CASH4" | "MEGAMILLIONS" | "POWERBALL" | "CASH4LIFE"
    row["lane_id"]             # e.g. "LANE_A", "LANE_B", "LANE_C", "LANE_D"
    row["confidence_score"]    # 0–100 float or int
    row["win_odds_1_in"]       # positive float (1-in-X odds; lower is better)

Optional helpers (used if present, but NOT required):
    row["is_triple"]           # bool (Cash3 only)
    row["is_quad"]             # bool (Cash4 only)
    row["pattern_tags"]        # list[str] or comma-separated string; e.g. ["HIGH_SUM", "REPEATER"]
    row["sum"]                 # integer digit sum (Cash3/Cash4)
    row["is_jackpot_only"]     # bool flag for special jackpot handling

If missing, the logic gracefully falls back to safe defaults.

Integration Notes
-----------------
- engine_core_v3_7.py should call apply_playtype_rubik(row) AFTER
  confidence_score and win_odds_1_in are attached to the row.

- option_c_logic.py may re-validate the outputs from this module
  but should NOT override them except for emergency compliance.

- legend_mapper_v3_7.py must know how to interpret legend_code values
  defined in LEGEND_CODES below.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Supported Games & Play Types
# ---------------------------------------------------------------------------

GAME_CASH3 = "CASH3"
GAME_CASH4 = "CASH4"
GAME_MEGAMILLIONS = "MEGAMILLIONS"
GAME_POWERBALL = "POWERBALL"
GAME_CASH4LIFE = "CASH4LIFE"

SUPPORTED_GAMES = {
    GAME_CASH3,
    GAME_CASH4,
    GAME_MEGAMILLIONS,
    GAME_POWERBALL,
    GAME_CASH4LIFE,
}

# Core play type labels – kept simple & stable for Option-C and legend mapping
PLAY_STRAIGHT = "STRAIGHT"
PLAY_BOX = "BOX"
PLAY_STRAIGHT_BOX = "STRAIGHT+BOX"
PLAY_COMBO = "COMBO"
PLAY_FRONT_PAIR = "FRONT_PAIR"
PLAY_BACK_PAIR = "BACK_PAIR"
PLAY_ONE_OFF = "ONE_OFF"

PLAY_STANDARD = "STANDARD"          # jackpot base play
PLAY_MB_ONLY = "MB_ONLY"            # Mega Ball / Power Ball / Cash4Life special focus
PLAY_QP_STANDARD = "QP_STANDARD"    # quick-pick friendly standard

# BOB (Best Odds Bonus) suggestion labels (internal, mapped in legend)
BOB_NONE = "NONE"
BOB_ADD_BOX = "ADD_BOX_FOR_SAFETY"
BOB_ADD_BACK_PAIR = "ADD_BACK_PAIR_ONLY"
BOB_ADD_ONE_OFF = "ADD_1_OFF"
BOB_STRONG_COMBO = "BOB_STRONG_ADD_COMBO"
BOB_STRAIGHT_ONLY = "STRAIGHT_ONLY_NO_BOB"

# Play-flag values used by Confidence → Play logic
PLAY_FLAG_CORE = "PLAY_CORE"        # Must-play (strong signal)
PLAY_FLAG_LIGHT = "PLAY_LIGHT"      # Light stake / optional
PLAY_FLAG_FUN = "PLAY_FUN"          # Micro stake only
PLAY_FLAG_SKIP = "SKIP"             # Do not play


# ---------------------------------------------------------------------------
# Legend code templates
# ---------------------------------------------------------------------------

# These are compact codes that legend_mapper_v3_7.py will expand
# into subscriber-facing explanations.

LEGEND_CODES = {
    # Cash3 / Cash4
    "C3_ST": "Cash3 Straight only",
    "C3_BX": "Cash3 Box only",
    "C3_STBX": "Cash3 Straight + Box",
    "C3_ST_1OFF": "Cash3 Straight + 1-Off safety",
    "C3_ST_BX_BOB": "Cash3 Straight + Box + BOB safety",
    "C3_PAIR_BACK": "Cash3 Back Pair focus",
    "C4_ST": "Cash4 Straight only",
    "C4_BX": "Cash4 Box only",
    "C4_STBX": "Cash4 Straight + Box",
    "C4_ST_1OFF": "Cash4 Straight + 1-Off safety",
    "C4_ST_BX_BOB": "Cash4 Straight + Box + BOB safety",
    "C4_PAIR_BACK": "Cash4 Back Pair focus",

    # Jackpot games
    "MM_STD": "MegaMillions standard ticket",
    "MM_STD_MB": "MegaMillions standard + MB-only safety",
    "PB_STD": "Powerball standard ticket",
    "PB_STD_PB": "Powerball standard + PB-only safety",
    "C4L_STD": "Cash4Life standard ticket",
    "C4L_STD_MB": "Cash4Life standard + Cash Ball focus",

    # Fallback
    "GEN_STD": "Generic standard play",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RubikContext:
    """Normalized context taken from a forecast row."""

    game_code: str
    lane_id: str
    confidence_score: float
    win_odds_1_in: float
    is_triple: bool = False
    is_quad: bool = False
    pattern_tags: List[str] = None
    digit_sum: Optional[int] = None
    is_jackpot_only: bool = False

    def has_tag(self, tag: str) -> bool:
        if not self.pattern_tags:
            return False
        tnorm = tag.upper()
        return any(t.upper() == tnorm for t in self.pattern_tags)


@dataclass
class PlayTypeDecision:
    """Final Rubik decision used by Option-C layer."""
    primary_play_type: str
    bob_suggestion: str
    play_flag: str
    legend_code: str
    rubik_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_play_type": self.primary_play_type,
            "bob_suggestion": self.bob_suggestion,
            "play_flag": self.play_flag,
            "legend_code": self.legend_code,
            "rubik_notes": self.rubik_notes,
        }


# ---------------------------------------------------------------------------
# Helpers – context extraction & confidence → play flag mapping
# ---------------------------------------------------------------------------

def _normalize_pattern_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return [str(value).strip()]


def _build_context(row: Dict[str, Any]) -> RubikContext:
    game_code = str(row.get("game_code", "")).upper().strip()
    lane_id = str(row.get("lane_id", "LANE_A")).upper().strip()

    # Confidence default to 50 if missing so logic still works
    try:
        confidence_score = float(row.get("confidence_score", 50.0))
    except (TypeError, ValueError):
        confidence_score = 50.0

    try:
        win_odds_1_in = float(row.get("win_odds_1_in", 9999.0))
    except (TypeError, ValueError):
        win_odds_1_in = 9999.0

    is_triple = bool(row.get("is_triple", False))
    is_quad = bool(row.get("is_quad", False))
    digit_sum = row.get("sum")
    try:
        digit_sum = int(digit_sum) if digit_sum is not None else None
    except (TypeError, ValueError):
        digit_sum = None

    pattern_tags = _normalize_pattern_tags(row.get("pattern_tags"))
    is_jackpot_only = bool(row.get("is_jackpot_only", False))

    return RubikContext(
        game_code=game_code,
        lane_id=lane_id,
        confidence_score=confidence_score,
        win_odds_1_in=win_odds_1_in,
        is_triple=is_triple,
        is_quad=is_quad,
        pattern_tags=pattern_tags,
        digit_sum=digit_sum,
        is_jackpot_only=is_jackpot_only,
    )


def _choose_play_flag(ctx: RubikContext) -> str:
    """
    Map confidence_score + win_odds into a coarse play_flag.

    These bands are intentionally simple & can be tuned later.
    The key is that play_flag is ALWAYS present for Option-C / SENTRY.
    """
    c = ctx.confidence_score
    o = ctx.win_odds_1_in

    # Strong alignment: high confidence and favorable odds
    if c >= 80 or o <= 120:
        return PLAY_FLAG_CORE

    # Solid edge: decent confidence and moderate odds
    if c >= 65 or o <= 250:
        return PLAY_FLAG_LIGHT

    # Weak but interesting: show as fun-only unless lane forces skip
    if c >= 50 or o <= 500:
        return PLAY_FLAG_FUN

    # Everything else: skip
    return PLAY_FLAG_SKIP


# ---------------------------------------------------------------------------
# Game-specific Rubik logic
# ---------------------------------------------------------------------------

def _decide_cash3(ctx: RubikContext) -> PlayTypeDecision:
    """
    Cash3-specific play-type Rubik.

    Key notes:
    - Triples tend to favor Box/Combo + small Straight.
    - High confidence → Straight+Box with BOB safety.
    - Medium confidence → Box with BOB 1-Off or Back Pair on repeaters.
    - Low confidence → Box/Fun or Skip, depending on play_flag.
    """
    play_flag = _choose_play_flag(ctx)

    # If play_flag says SKIP, we still output a valid structure but note skip.
    if play_flag == PLAY_FLAG_SKIP:
        return PlayTypeDecision(
            primary_play_type=PLAY_BOX,
            bob_suggestion=BOB_NONE,
            play_flag=PLAY_FLAG_SKIP,
            legend_code="C3_BX",
            rubik_notes="Cash3 – Low confidence; Box-only recommended as SKIP/FUN reference.",
        )

    # Triples: box is essential; often add Straight or Combo when confidence is high
    if ctx.is_triple:
        if ctx.confidence_score >= 75:
            return PlayTypeDecision(
                primary_play_type=PLAY_STRAIGHT_BOX,
                bob_suggestion=BOB_STRONG_COMBO,
                play_flag=play_flag,
                legend_code="C3_ST_BX_BOB",
                rubik_notes="Cash3 triple – Straight+Box with BOB Combo for maximum capture.",
            )
        else:
            return PlayTypeDecision(
                primary_play_type=PLAY_BOX,
                bob_suggestion=BOB_ADD_BOX,
                play_flag=play_flag,
                legend_code="C3_BX",
                rubik_notes="Cash3 triple – Box-first approach on moderate confidence.",
            )

    # Repeater or strong pattern tag – consider Back Pair add-on
    if ctx.has_tag("REPEATER") or ctx.has_tag("BACKPAIR"):
        return PlayTypeDecision(
            primary_play_type=PLAY_STRAIGHT,
            bob_suggestion=BOB_ADD_BACK_PAIR,
            play_flag=play_flag,
            legend_code="C3_PAIR_BACK",
            rubik_notes="Cash3 repeater/back-bias – Straight + Back Pair BOB.",
        )

    # High confidence classic case
    if ctx.confidence_score >= 80:
        return PlayTypeDecision(
            primary_play_type=PLAY_STRAIGHT_BOX,
            bob_suggestion=BOB_ADD_ONE_OFF,
            play_flag=play_flag,
            legend_code="C3_ST_1OFF",
            rubik_notes="Cash3 high confidence – Straight+Box + 1-Off safety.",
        )

    # Moderate confidence – favor Box, plus small Straight if lane B/C
    if ctx.confidence_score >= 65:
        if ctx.lane_id in ("LANE_B", "LANE_C"):
            return PlayTypeDecision(
                primary_play_type=PLAY_STRAIGHT_BOX,
                bob_suggestion=BOB_ADD_BOX,
                play_flag=play_flag,
                legend_code="C3_STBX",
                rubik_notes="Cash3 medium confidence – Straight+Box stacked for lane B/C.",
            )
        return PlayTypeDecision(
            primary_play_type=PLAY_BOX,
            bob_suggestion=BOB_ADD_ONE_OFF,
            play_flag=play_flag,
            legend_code="C3_BX",
            rubik_notes="Cash3 medium confidence – Box-first with 1-Off BOB.",
        )

    # Low confidence but not skip – fun Box only
    return PlayTypeDecision(
        primary_play_type=PLAY_BOX,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="C3_BX",
        rubik_notes="Cash3 low confidence – Box-only as FUN-level play.",
    )


def _decide_cash4(ctx: RubikContext) -> PlayTypeDecision:
    """
    Cash4-specific play-type Rubik.

    Similar to Cash3 but with quads and more volatility.
    """
    play_flag = _choose_play_flag(ctx)

    if play_flag == PLAY_FLAG_SKIP:
        return PlayTypeDecision(
            primary_play_type=PLAY_BOX,
            bob_suggestion=BOB_NONE,
            play_flag=PLAY_FLAG_SKIP,
            legend_code="C4_BX",
            rubik_notes="Cash4 – Low confidence; Box-only recommended as SKIP/FUN reference.",
        )

    # Quads: very rare; strong Box/Combo emphasis when flagged
    if ctx.is_quad:
        if ctx.confidence_score >= 75:
            return PlayTypeDecision(
                primary_play_type=PLAY_STRAIGHT_BOX,
                bob_suggestion=BOB_STRONG_COMBO,
                play_flag=play_flag,
                legend_code="C4_ST_BX_BOB",
                rubik_notes="Cash4 quad – Straight+Box + BOB Combo on high confidence.",
            )
        return PlayTypeDecision(
            primary_play_type=PLAY_BOX,
            bob_suggestion=BOB_ADD_BOX,
            play_flag=play_flag,
            legend_code="C4_BX",
            rubik_notes="Cash4 quad – Box-first on moderate confidence.",
        )

    # Back pair emphasis or repeater pattern
    if ctx.has_tag("REPEATER") or ctx.has_tag("BACKPAIR"):
        return PlayTypeDecision(
            primary_play_type=PLAY_STRAIGHT,
            bob_suggestion=BOB_ADD_BACK_PAIR,
            play_flag=play_flag,
            legend_code="C4_PAIR_BACK",
            rubik_notes="Cash4 repeater/back-bias – Straight + Back Pair BOB.",
        )

    # High confidence general case
    if ctx.confidence_score >= 80:
        return PlayTypeDecision(
            primary_play_type=PLAY_STRAIGHT_BOX,
            bob_suggestion=BOB_ADD_ONE_OFF,
            play_flag=play_flag,
            legend_code="C4_ST_1OFF",
            rubik_notes="Cash4 high confidence – Straight+Box + 1-Off safety.",
        )

    # Moderate confidence general case
    if ctx.confidence_score >= 65:
        if ctx.lane_id in ("LANE_B", "LANE_C"):
            return PlayTypeDecision(
                primary_play_type=PLAY_STRAIGHT_BOX,
                bob_suggestion=BOB_ADD_BOX,
                play_flag=play_flag,
                legend_code="C4_STBX",
                rubik_notes="Cash4 medium confidence – Straight+Box for structured lanes.",
            )
        return PlayTypeDecision(
            primary_play_type=PLAY_BOX,
            bob_suggestion=BOB_ADD_ONE_OFF,
            play_flag=play_flag,
            legend_code="C4_BX",
            rubik_notes="Cash4 medium confidence – Box-first with 1-Off BOB.",
        )

    # Low confidence but not skip – fun Box only
    return PlayTypeDecision(
        primary_play_type=PLAY_BOX,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="C4_BX",
        rubik_notes="Cash4 low confidence – Box-only as FUN-level play.",
    )


def _decide_megamillions(ctx: RubikContext) -> PlayTypeDecision:
    """
    MegaMillions play-type Rubik.

    We keep structure very simple:
    - STANDARD ticket is the base.
    - When confidence is high or lane is jackpot-focused, add MB-only BOB.
    """
    play_flag = _choose_play_flag(ctx)

    if play_flag == PLAY_FLAG_SKIP:
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_NONE,
            play_flag=PLAY_FLAG_SKIP,
            legend_code="MM_STD",
            rubik_notes="MegaMillions – Low signal; standard line shown as reference only.",
        )

    if ctx.confidence_score >= 80 or ctx.lane_id in ("LANE_B", "LANE_C"):
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_ADD_BACK_PAIR,  # repurposed internally for MB-only focus
            play_flag=play_flag,
            legend_code="MM_STD_MB",
            rubik_notes="MegaMillions high confidence – Standard + MB-focused BOB lane.",
        )

    return PlayTypeDecision(
        primary_play_type=PLAY_STANDARD,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="MM_STD",
        rubik_notes="MegaMillions normal confidence – Standard ticket only.",
    )


def _decide_powerball(ctx: RubikContext) -> PlayTypeDecision:
    """
    Powerball play-type Rubik.

    Mirrors MegaMillions structure but uses PB-focused legend codes.
    """
    play_flag = _choose_play_flag(ctx)

    if play_flag == PLAY_FLAG_SKIP:
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_NONE,
            play_flag=PLAY_FLAG_SKIP,
            legend_code="PB_STD",
            rubik_notes="Powerball – Low signal; standard line shown as reference only.",
        )

    if ctx.confidence_score >= 80 or ctx.lane_id in ("LANE_B", "LANE_C"):
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_ADD_BACK_PAIR,  # internal shorthand for PB-only focus
            play_flag=play_flag,
            legend_code="PB_STD_PB",
            rubik_notes="Powerball high confidence – Standard + PB-focused BOB lane.",
        )

    return PlayTypeDecision(
        primary_play_type=PLAY_STANDARD,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="PB_STD",
        rubik_notes="Powerball normal confidence – Standard ticket only.",
    )


def _decide_cash4life(ctx: RubikContext) -> PlayTypeDecision:
    """
    Cash4Life play-type Rubik.

    Very similar to MegaMillions: base STANDARD ticket with optional ball-focus BOB.
    """
    play_flag = _choose_play_flag(ctx)

    if play_flag == PLAY_FLAG_SKIP:
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_NONE,
            play_flag=PLAY_FLAG_SKIP,
            legend_code="C4L_STD",
            rubik_notes="Cash4Life – Low signal; standard line shown as reference only.",
        )

    if ctx.confidence_score >= 80 or ctx.lane_id in ("LANE_B", "LANE_C"):
        return PlayTypeDecision(
            primary_play_type=PLAY_STANDARD,
            bob_suggestion=BOB_ADD_BACK_PAIR,  # internal shorthand for Cash Ball focus
            play_flag=play_flag,
            legend_code="C4L_STD_MB",
            rubik_notes="Cash4Life high confidence – Standard + Cash Ball–focused BOB lane.",
        )

    return PlayTypeDecision(
        primary_play_type=PLAY_STANDARD,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="C4L_STD",
        rubik_notes="Cash4Life normal confidence – Standard ticket only.",
    )


def _decide_fallback(ctx: RubikContext) -> PlayTypeDecision:
    """
    Fallback logic for unknown/unsupported games.

    Still returns a COMPLETE decision block for Option-C & SENTRY.
    """
    play_flag = _choose_play_flag(ctx)

    return PlayTypeDecision(
        primary_play_type=PLAY_STANDARD,
        bob_suggestion=BOB_NONE,
        play_flag=play_flag,
        legend_code="GEN_STD",
        rubik_notes=f"Fallback Rubik – Generic STANDARD play for game={ctx.game_code or 'UNKNOWN'}.",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_playtype_rubik(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the Play-Type Rubik.

    Parameters
    ----------
    row : dict
        A forecast row, already enriched with:
            - game_code
            - lane_id
            - confidence_score
            - win_odds_1_in
        plus any of:
            - is_triple / is_quad / pattern_tags / sum / is_jackpot_only

    Returns
    -------
    dict
        The original row, updated with the following Option-C critical fields:
            - primary_play_type
            - bob_suggestion
            - play_flag
            - legend_code
            - rubik_notes
    """
    ctx = _build_context(row)

    if ctx.game_code == GAME_CASH3:
        decision = _decide_cash3(ctx)
    elif ctx.game_code == GAME_CASH4:
        decision = _decide_cash4(ctx)
    elif ctx.game_code == GAME_MEGAMILLIONS:
        decision = _decide_megamillions(ctx)
    elif ctx.game_code == GAME_POWERBALL:
        decision = _decide_powerball(ctx)
    elif ctx.game_code == GAME_CASH4LIFE:
        decision = _decide_cash4life(ctx)
    else:
        decision = _decide_fallback(ctx)

    row.update(decision.to_dict())
    return row


# For introspection by engine_core_v3_7 / run_kit_v3_7
EXPORTED_FUNCTIONS = ["apply_playtype_rubik"]
