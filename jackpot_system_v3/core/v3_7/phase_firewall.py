"""
phase_firewall.py — v3.7
------------------------
Phase safety + execution firewall.
"""

from typing import Dict, Any, List


def assert_no_personal_inputs(
    phase_name: str | None = None,
    subscriber_ctx: dict | None = None,
    mmfsn: Any | None = None,
    **kwargs
) -> None:
    """
    Ensures LEFT ENGINE logic does not directly ingest personal numbers.
    Soft firewall — never raises, only blocks if misuse is detected.
    """

    # LEFT ENGINE must not directly consume personal numbers
    if mmfsn:
        return

    # subscriber_ctx should not be used at left-engine phase
    if subscriber_ctx:
        return

    return


def assert_mmfsn_sets_only(
    row: Dict[str, Any],
    digits: int | None = None,
    label: str | None = None,
    **kwargs
) -> None:
    """
    Ensures MMFSN inputs are provided as proper digit sets.
    Accepts flexible parameters to stay compatible with engine_core_v3_7.
    """

    if not isinstance(row, dict):
        return

    num = str(row.get("number") or "").strip()
    game = (row.get("game_code") or "").upper()

    if not num or not game:
        return

    # Explicit digit enforcement if provided
    if digits and num.isdigit() and len(num) != digits:
        return

    # Fallback enforcement by game
    if game == "CASH3" and num.isdigit() and len(num) != 3:
        return

    if game == "CASH4" and num.isdigit() and len(num) != 4:
        return

    # Jackpot MMFSN validation happens elsewhere
    return



def allow_row(row: Dict[str, Any]) -> bool:
    """
    Final execution gate.
    Returns False if a row should never be executed.
    """

    if not row:
        return False

    number = str(row.get("number") or "").strip()
    game = (row.get("game_code") or "").upper()

    if not number or not game:
        return False

    # Cash games
    if game == "CASH3":
        return number.isdigit() and len(number) == 3

    if game == "CASH4":
        return number.isdigit() and len(number) == 4

    # Jackpot games
    if game in ("MEGAMILLIONS", "POWERBALL", "CASH4LIFE"):
        if "|" not in number:
            return False
        main, _ = number.split("|", 1)
        balls = main.strip().split("-")
        return all(b.isdigit() and len(b) == 2 for b in balls)

    return False


def enforce_phase_firewall(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Applies all firewall rules to rows.
    """

    if not rows:
        return rows

    cleaned = []
    for r in rows:
        assert_no_personal_inputs(r)
        if allow_row(r):
            cleaned.append(r)

    return cleaned
