# play_type_resolver_v3_7.py

from typing import Dict

CASH3_PLAY_TYPES = ["STRAIGHT", "STRAIGHT/BOX", "BOX", "COMBO", "1-OFF", "PAIR"]
CASH4_PLAY_TYPES = ["STRAIGHT", "STRAIGHT/BOX", "BOX", "COMBO", "1-OFF"]

def _base_default_for_game(game: str) -> str:
    g = (game or "").strip().lower()
    if "cash 3" in g or "cash3" in g:
        return "STRAIGHT"
    if "cash 4" in g or "cash4" in g:
        return "STRAIGHT"
    # Jackpots: standard ticket, no play-type nuance at retailer
    return "STANDARD"
    

def resolve_play_type(game: str, ctx: Dict) -> str:
    """
    Decide BEST play type for this row, based on:
      - Game (Cash 3 / Cash 4 / Jackpot)
      - Context flags from the engine (ctx dict)

    Expected ctx flags (True/False where relevant):
      - pair_focus:      built around front/back pairs
      - one_off_focus:   1-off safety is recommended
      - combo_focus:     full combo coverage recommended
      - box_safety:      Box is recommended as a safety overlay
      - high_confidence: strong A/B + recency + pattern
      - straight_core:   number is primarily a straight hit target
    """
    game_lower = (game or "").strip().lower()
    base = _base_default_for_game(game)

    # Jackpots: keep it simple
    if "mega" in game_lower or "powerball" in game_lower or "cash4life" in game_lower:
        return "STANDARD"

    pair_focus      = bool(ctx.get("pair_focus"))
    one_off_focus   = bool(ctx.get("one_off_focus"))
    combo_focus     = bool(ctx.get("combo_focus"))
    box_safety      = bool(ctx.get("box_safety"))
    high_confidence = bool(ctx.get("high_confidence"))
    straight_core   = bool(ctx.get("straight_core", True))  # assume true unless told otherwise

    # 1) Pair-specific plays (Cash 3 only right now)
    if ("cash 3" in game_lower or "cash3" in game_lower) and pair_focus:
        return "PAIR"

    # 2) 1-Off calls
    if one_off_focus:
        return "1-OFF"

    # 3) Full combo coverage
    if combo_focus:
        return "COMBO"

    # 4) Straight/Box blend when:
    #    - core is straight, but we want Box safety AND confidence is decent
    if box_safety and straight_core:
        # Only upgrade to STRAIGHT/BOX if game supports it
        if "cash 3" in game_lower or "cash3" in game_lower or "cash 4" in game_lower or "cash4" in game_lower:
            return "STRAIGHT/BOX"

    # 5) Simple Box safety when pattern is noisy / mixed
    if box_safety and not straight_core:
        return "BOX"

    # 6) Default = Straight (your exact requested base)
    return base
