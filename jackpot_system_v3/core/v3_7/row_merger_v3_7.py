# -*- coding: utf-8 -*-
"""
row_merger_v3_7.py  
Merges all lane outputs into a unified, Option-C clean format.

Responsibility:
    • Combine lane outputs (Lane A, B, C, D, Planetary, Numerology…)
    • De-duplicate rows
    • Highest confidence pick wins for duplicates
    • Pass each row through left_builder_v3_7 to enforce Option-C schema
"""

from typing import List, Dict, Any
from .left_builder_v3_7 import build_row_v3_7


def _row_key(lane_row: Dict[str, Any]) -> str:
    """
    Unique identifier for a pick:
       game + date + session + pick digits
    This ensures duplicates collapse correctly.
    """
    game = str(lane_row.get("game", "")).lower()
    date = str(lane_row.get("draw_date", ""))
    session = str(lane_row.get("session", "")).lower()
    pick = str(lane_row.get("value") or lane_row.get("pick") or "")
    return f"{game}|{date}|{session}|{pick}"


def merge_lane_outputs_v3_7(
    all_lane_rows: List[Dict[str, Any]],
    subscriber_id: str,
    kit_type: str
) -> List[Dict[str, Any]]:
    """
    Input:
        all_lane_rows → raw lane outputs from pick_engine_v3
        subscriber_id → "JDS_BOOK3"
        kit_type      → "BOOK3"
    Output:
        List of Option-C formatted rows
    """

    # STEP 1 — collapse duplicates using “best pick wins”
    collapsed: Dict[str, Dict[str, Any]] = {}

    for lane_row in all_lane_rows:
        key = _row_key(lane_row)

        # First time seeing this combination → store as-is
        if key not in collapsed:
            collapsed[key] = lane_row
            continue

        # If duplicate, pick the one with higher confidence
        try:
            new_conf = float(lane_row.get("confidence", 0))
            old_conf = float(collapsed[key].get("confidence", 0))
        except:
            new_conf = 0
            old_conf = 0

        if new_conf > old_conf:
            collapsed[key] = lane_row

    # STEP 2 — convert all clean merged rows into Option-C rows
    final_rows: List[Dict[str, Any]] = []

    for merged_lane_row in collapsed.values():
        option_c_row = build_row_v3_7(
            merged_lane_row,
            subscriber_id=subscriber_id,
            kit_type=kit_type
        )
        final_rows.append(option_c_row)

    # STEP 3 — sort output for presentation stability
    final_rows.sort(key=lambda r: (r["draw_date"], r["draw_time"], r["game"]))

    return final_rows
