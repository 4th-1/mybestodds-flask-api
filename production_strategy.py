"""Production strategy policy gates for live recommendations."""

from __future__ import annotations


ALLOWED_CASH3_SESSION   = "NIGHT"
ALLOWED_CASH3_TIER      = "PRIORITY WATCH"
ALLOWED_CASH3_TIER_RAW  = "MODERATE"
ALLOWED_CASH3_PLAY_TYPE = "STRAIGHT_BOX"   # condition-scoring confirmed profit engine
STRATEGY_VERSION = "cash3_moderate_night_straight_box_v2"

# Shadow-tracked play types — collected but NOT sent to subscribers
SHADOW_CASH3_PLAY_TYPES = {"BOX", "STRAIGHT+1OFF", "ONE_OFF", "STRAIGHT"}


def normalize_confidence_tier(tier: str | None) -> str:
    return (tier or "").strip().upper()


def is_live_recommendation_allowed(
    game: str | None,
    session: str | None,
    confidence_tier: str | None,
    play_type: str | None = None,
) -> bool:
    """Return True only for the currently validated production lane.

    Lane: Cash3 | PRIORITY WATCH (MODERATE) | NIGHT | STRAIGHT_BOX
    All other Cash3 play types and sessions are shadow-tracked research lanes.
    Cash4 is fully held pending its own EV rebuild.
    """
    game_norm    = (game or "").strip().upper()
    session_norm = (session or "").strip().upper()
    tier_norm    = normalize_confidence_tier(confidence_tier)
    play_norm    = (play_type or "").strip().upper()

    if game_norm == "CASH3":
        if session_norm != ALLOWED_CASH3_SESSION:
            return False
        if tier_norm != ALLOWED_CASH3_TIER:
            return False
        # play_type gate: only block when a value is explicitly supplied
        if play_norm and play_norm != ALLOWED_CASH3_PLAY_TYPE:
            return False
        return True

    if game_norm == "CASH4":
        return False

    return True


def strategy_reason(
    game: str | None,
    session: str | None,
    confidence_tier: str | None,
    play_type: str | None = None,
) -> str:
    """Explain why a recommendation is allowed or suppressed."""
    if is_live_recommendation_allowed(game, session, confidence_tier, play_type):
        return "validated_economic_lane"

    game_norm    = (game or "").strip().upper()
    session_norm = (session or "").strip().upper() or "UNKNOWN"
    tier_norm    = normalize_confidence_tier(confidence_tier) or "UNKNOWN"
    play_norm    = (play_type or "").strip().upper() or "UNKNOWN"

    if game_norm == "CASH4":
        return "cash4_disabled_pending_ev_rebuild"
    if game_norm == "CASH3" and session_norm != ALLOWED_CASH3_SESSION:
        return f"cash3_session_suppressed:{session_norm}"
    if game_norm == "CASH3" and tier_norm != ALLOWED_CASH3_TIER:
        return f"cash3_tier_suppressed:{tier_norm}"
    if game_norm == "CASH3" and play_norm not in (ALLOWED_CASH3_PLAY_TYPE, "UNKNOWN"):
        return f"cash3_play_type_shadow:{play_norm}"
    return "strategy_not_applicable"
