from __future__ import annotations

import json
from typing import List, Dict, Any

# -----------------------------
# CONFIG
# -----------------------------
MAX_CONFIDENCE = 15.0

# -----------------------------
# CONFIDENCE BANDING (OPTIONAL)
# -----------------------------
def confidence_band(pct: int) -> str:
    if pct >= 80:
        return "STRONG"
    elif pct >= 65:
        return "MODERATE"
    elif pct >= 50:
        return "WATCH"
    else:
        return "SKIP"

# -----------------------------
# FORMATTER
# -----------------------------
def format_weekly_kit(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted: List[Dict[str, Any]] = []

    for r in rows:
        out = dict(r)

        # -------------------------
        # CASH + ALL GAMES
        # -------------------------
        confidence_score = float(r.get("confidence_score", 0))
        out["confidence_pct"] = round(
            (confidence_score / MAX_CONFIDENCE) * 100
        )
        out["confidence_band"] = confidence_band(out["confidence_pct"])

        # -------------------------
        # JACKPOT (SEPARATE SIGNAL)
        # -------------------------
        if r.get("is_jackpot"):
            jackpot_score = float(r.get("jackpot_confidence_score", 0))
            out["jackpot_confidence_pct"] = round(
                (jackpot_score / MAX_CONFIDENCE) * 100
            )

        formatted.append(out)

    return formatted

# -----------------------------
# CLI / FILE DRIVER
# -----------------------------
def run_formatter(
    input_path: str,
    output_path: str,
):
    with open(input_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    formatted = format_weekly_kit(rows)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=2)

    print(f"[FORMATTER] Weekly kit written to {output_path}")
