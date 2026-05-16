"""
soul_compass_writer.py
======================
Derives and persists Soul Compass alignment values for use by
convergence_alert.py (and any other downstream consumer).

Two modes of operation
----------------------
1. Lovable-push  (preferred)
   Lovable's edge function POSTs its already-computed values to
   POST /api/soul-compass/write after each daily email send.
   This file just persists what Lovable calculated.

2. Overlay-derived fallback
   If Lovable hasn't posted today, generate_soul_compass(date_str)
   derives values from overlay_engine_v3_7 so the cache is never empty.

Files written
-------------
  data/soul_compass_today.json   – single-day object, overwritten daily
  data/soul_compass_cache.json   – rolling 7-day list, deduplicated by date

Schema
------
{
    "date": "YYYY-MM-DD",
    "alignment_strength": "Peak|Strong|Elevated|Moderate|Low",
    "timing_posture":     "Lean In|Engage|Steady|Hold|Wait",
    "focus_area":         "<string>",
    "source":             "lovable|overlay_engine"
}

CLI
---
    python soul_compass_writer.py              # generate for today
    python soul_compass_writer.py 2026-05-15   # generate for a specific date
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_DIR, "data")
_TODAY_FILE = os.path.join(_DATA_DIR, "soul_compass_today.json")
_CACHE_FILE = os.path.join(_DATA_DIR, "soul_compass_cache.json")

# ---------------------------------------------------------------------------
# Label-mapping tables (overlay engine → Soul Compass labels)
# ---------------------------------------------------------------------------

# Overlay score is the average of four component weights (0.0–1.0 each).
# See combined_overlay_score() in overlay_engine_v3_7.py.
_ALIGNMENT_THRESHOLDS = [
    (0.80, "Peak"),
    (0.65, "Strong"),
    (0.50, "Elevated"),
    (0.35, "Moderate"),
]

# Moon phase → timing posture (primary driver)
# Logic: waxing phases = action energy; near-new = fresh start / lean in;
#        waning phases = reflection / hold except waning gibbous = steady.
_MOON_POSTURE: dict[str, str] = {
    "New Moon":        "Lean In",   # fresh cycle, new-moon energy
    "Waxing Crescent": "Lean In",   # momentum building
    "First Quarter":   "Lean In",   # decisive action quarter
    "Waxing Gibbous":  "Engage",    # approaching peak
    "Full Moon":       "Engage",    # peak expression
    "Waning Gibbous":  "Steady",    # sustain momentum
    "Last Quarter":    "Hold",      # reflection phase
    "Waning Crescent": "Hold",      # closing / rest
}

# Zodiac sign → focus area (flavour text for the email)
_ZODIAC_FOCUS: dict[str, str] = {
    "Aries":       "Bold Moves",
    "Taurus":      "Patient Accumulation",
    "Gemini":      "Adaptive Strategy",
    "Cancer":      "Intuition & Instinct",
    "Leo":         "Confidence & Courage",
    "Virgo":       "Precision & Detail",
    "Libra":       "Balanced Risk",
    "Scorpio":     "Deep Investigation",
    "Sagittarius": "Expansive Play",
    "Capricorn":   "Disciplined Structure",
    "Aquarius":    "Pattern Recognition",
    "Pisces":      "Flow & Intuition",
}


# ---------------------------------------------------------------------------
# Core derivation
# ---------------------------------------------------------------------------

def _overlay_to_alignment(overlay_score: float) -> str:
    """Map a 0.0–1.0 overlay score to an alignment_strength label."""
    for threshold, label in _ALIGNMENT_THRESHOLDS:
        if overlay_score >= threshold:
            return label
    return "Low"


def generate_soul_compass(date_str: Optional[str] = None) -> dict:
    """
    Derive Soul Compass values for *date_str* (YYYY-MM-DD) using the
    overlay engine.  Defaults to today if date_str is None.

    Returns a soul_compass dict ready for write_soul_compass_files().
    """
    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")

    # Import here so this module doesn't hard-fail if the overlay engine
    # isn't installed (e.g. during unit-testing / plain import).
    try:
        sys.path.insert(0, os.path.join(_DIR, "jackpot_system_v3", "core"))
        from overlay_engine_v3_7 import compute_overlays  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "overlay_engine_v3_7 not found — cannot derive soul compass. "
            "Use write_soul_compass_files() to persist Lovable-provided values instead."
        ) from exc

    # Use Midday session as the anchor draw for each day's overlay score.
    raw = compute_overlays(date_str, "Midday")

    overlay_score = float(raw["overlay_score"])
    moon_phase    = raw["moon_phase"]
    zodiac_sign   = raw["zodiac_sign"]

    alignment_strength = _overlay_to_alignment(overlay_score)
    timing_posture     = _MOON_POSTURE.get(moon_phase, "Steady")
    focus_area         = _ZODIAC_FOCUS.get(zodiac_sign, "Purposeful Action")

    # Boost posture: if overlay is Peak but posture would be Hold,
    # upgrade to Engage so high-pressure alerts aren't suppressed.
    if alignment_strength == "Peak" and timing_posture == "Hold":
        timing_posture = "Engage"

    return {
        "date":               date_str,
        "alignment_strength": alignment_strength,
        "timing_posture":     timing_posture,
        "focus_area":         focus_area,
        "moon_phase":         moon_phase,
        "zodiac_sign":        zodiac_sign,
        "numerology_code":    raw["numerology_code"],
        "overlay_score":      overlay_score,
        "source":             "overlay_engine",
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_soul_compass_files(entry: dict) -> None:
    """
    Write *entry* to:
      - data/soul_compass_today.json  (overwrite)
      - data/soul_compass_cache.json  (append, dedup by date, keep 7 days)
    """
    os.makedirs(_DATA_DIR, exist_ok=True)

    # 1. Overwrite today file
    with open(_TODAY_FILE, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)

    # 2. Append to rolling 7-day cache
    cache: list[dict] = []
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                cache = json.load(f)
            if not isinstance(cache, list):
                cache = []
        except (json.JSONDecodeError, OSError):
            cache = []

    # Deduplicate: remove any existing entry for the same date
    cache = [e for e in cache if e.get("date") != entry.get("date")]
    cache.append(entry)
    cache = cache[-7:]  # keep most-recent 7 days

    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def generate_and_write(date_str: Optional[str] = None) -> dict:
    """Convenience: generate + write in one call. Returns the entry written."""
    entry = generate_soul_compass(date_str)
    write_soul_compass_files(entry)
    return entry


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_main() -> None:
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    entry = generate_and_write(date_str)
    print(json.dumps(entry, indent=2))
    print(f"\nWrote → {_TODAY_FILE}")
    print(f"Cache → {_CACHE_FILE}")


if __name__ == "__main__":
    _cli_main()
