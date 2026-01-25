from datetime import datetime

# Optional logger (safe to keep)
try:
    from audit.sentinel_logger_v3_7 import write_sentinel_rejections
except Exception:
    write_sentinel_rejections = None


# =============================================================================
# DRAW SCHEDULE (AUTHORITATIVE)
# =============================================================================
DRAW_SCHEDULE = {
    "MEGAMILLIONS": {1, 4},        # Tuesday, Friday
    "POWERBALL": {0, 2, 5},        # Monday, Wednesday, Saturday
    "CASH3": set(range(7)),
    "CASH4": set(range(7)),
    "CASH4LIFE": set(range(7)),
}


# =============================================================================
# NORMALIZATION
# =============================================================================
def normalize_game_code(game: str) -> str:
    g = (game or "").upper().replace("_", "").replace(" ", "")
    if g in ("MEGAMILLIONS", "MM"):
        return "MEGAMILLIONS"
    if g in ("POWERBALL", "PB"):
        return "POWERBALL"
    if g in ("CASH4LIFE", "C4L"):
        return "CASH4LIFE"
    return g


# =============================================================================
# VALIDATION HELPERS
# =============================================================================
def is_executable_number(row: dict) -> bool:
    """
    Validates that a generated number is structurally executable
    for its game type.
    """
    num = str(row.get("number") or "").strip()
    game = normalize_game_code(row.get("game_code"))

    if not num or not game:
        return False

    if game == "CASH3":
        return num.isdigit() and len(num) == 3

    if game == "CASH4":
        return num.isdigit() and len(num) == 4

    if game in ("MEGAMILLIONS", "POWERBALL", "CASH4LIFE"):
        parts = num.split("|")
        if len(parts) != 2:
            return False
        balls = parts[0].strip().split("-")
        return all(b.isdigit() and len(b) == 2 for b in balls)

    return False


def is_valid_draw_day(row: dict) -> bool:
    """
    Authoritative draw-day gating.
    """
    game = normalize_game_code(row.get("game_code"))
    date_str = row.get("forecast_date")

    if not game or not date_str:
        return False

    if game not in DRAW_SCHEDULE:
        return False

    try:
        dow = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    except Exception:
        return False

    return dow in DRAW_SCHEDULE[game]
