"""
convergence_alert.py
====================
Pre-draw convergence scanner.

Closes the gap that caused the 444 miss on 2026-05-15:
  - Due-Signal (app, reactive) and Soul Compass (email, no number named)
    both fired at threshold but neither knew the other existed.
  - No proactive named-number alert was sent before the Midday draw.

This module:
  1. Runs before each draw session (schedule: 11 AM / 5 PM / 10 PM local)
  2. Scans all Cash3 triples and Cash4 quads for structural pressure threshold
  3. Reads today's Soul Compass alignment strength
  4. When BOTH thresholds are met → emits a ConvergenceAlert dict
  5. Callers (Flask endpoint, email formatter, push handler) consume the alert

Design rules learned from the 444 miss
---------------------------------------
R1: max_gap_breached = True  → EXTREME label regardless of celestial match or stale data
R2: Stale data adds a caveat line, never suppresses a convergence alert
R3: session_affinity is surfaced as the primary "play window" in the alert headline
R4: preferred_window_days_away: if ≤ 14 → "window opening" message, not a mismatch penalty
R5: Two independent signals agreeing on the same day is the trigger — not one signal alone
"""

import json
import os
import sys
from datetime import datetime, date
from typing import Optional

# ── path setup ────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(_DIR, 'jackpot_system_v3', 'core')
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from triple_due_signal import compute_due_signal   # noqa: E402

# ── thresholds ────────────────────────────────────────────────────────────────
# A candidate crosses the structural pressure threshold when ANY of these is true:
THRESHOLD_MAX_GAP_BREACHED    = True    # historical max exceeded → always qualifies
THRESHOLD_OVERDUE_RATIO       = 1.25    # 25 % past average gap
THRESHOLD_GAP_PERCENTILE      = 85.0   # top 15 % of all historical gaps

# Soul Compass alignment strengths that count as "aligned for action"
ALIGNED_STRENGTHS = {'peak', 'strong', 'elevated'}

# Celestial fingerprint match tiers (score 0.0–1.0)
# Based on _score_condition_match() in triple_due_signal.py
CELESTIAL_MATCH_TIERS = [
    (0.85, 'Strong Historical Match'),
    (0.65, 'Elevated Match'),
    (0.40, 'Moderate Match'),
    (0.0,  'Weak Match'),
]

# Session draw times (local ET) — used in alert copy only
SESSION_DRAW_TIMES = {
    'Midday':  '12:29 PM',
    'Evening': '6:59 PM',
    'Night':   '11:34 PM',
}

# ── types ─────────────────────────────────────────────────────────────────────

class ConvergenceAlert:
    """
    Emitted when structural pressure + personal alignment both cross threshold.

    Attributes
    ----------
    game              : 'Cash3' or 'Cash4'
    number            : e.g. '444'
    signal_label      : 'EXTREME' | 'STRONG' | 'MODERATE'
    overdue_ratio     : float  e.g. 1.36
    current_gap       : int    e.g. 529
    avg_gap           : float  e.g. 389.0
    max_gap_breached  : bool
    session           : recommended draw session e.g. 'Midday'
    draw_time         : human time string e.g. '12:29 PM'
    alignment_strength          : string from Soul Compass e.g. 'Peak'
    timing_posture              : string from Soul Compass e.g. 'Lean In'
    stale_data                  : bool — data freshness caveat present
    days_since_hit              : int
    preferred_window_days_away  : int | None — days until celestial preferred window
    celestial_match_score       : float 0.0–1.0 — fingerprint similarity vs historical hits
    celestial_match_tier        : str  e.g. 'Strong Historical Match'
    headline                    : subscriber-facing one-liner
    body                        : subscriber-facing explanation paragraph
    play_instruction            : concise action line
    generated_at                : ISO timestamp
    """

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def __repr__(self):
        return (
            f"<ConvergenceAlert {self.game} {self.number} | "
            f"{self.signal_label} | {self.session} {self.draw_time} | "
            f"gap={self.current_gap} ({self.overdue_ratio}x) | "
            f"alignment={self.alignment_strength}>"
        )


# ── Soul Compass reader ───────────────────────────────────────────────────────

def _load_soul_compass(today: Optional[date] = None) -> dict:
    """
    Read today's Soul Compass output.

    Looks for:
      - data/soul_compass_today.json   (written by the daily email job)
      - data/soul_compass_cache.json   (rolling cache, last 7 days)
    Falls back to neutral defaults so the convergence scanner still runs.

    Expected schema:
      {
        "date": "2026-05-15",
        "alignment_strength": "Peak",      # Peak | Strong | Elevated | Moderate | Low
        "focus_area": "Purposeful Action",
        "timing_posture": "Lean In"        # Lean In | Engage | Steady | Hold | Wait
      }
    """
    today_str = (today or date.today()).strftime('%Y-%m-%d')

    search_paths = [
        os.path.join(_DIR, 'data', 'soul_compass_today.json'),
        os.path.join(_DIR, 'data', 'soul_compass_cache.json'),
    ]

    for path in search_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                raw = json.load(f)
            # cache may be a list of daily entries
            if isinstance(raw, list):
                for entry in reversed(raw):
                    if entry.get('date') == today_str:
                        return entry
                # not found for today — return most recent
                return raw[-1] if raw else {}
            if isinstance(raw, dict):
                # single-entry file
                return raw
        except Exception:
            continue

    # No file found — return neutral defaults (scanner will still run on
    # structural pressure alone, but won't require alignment confirmation)
    return {
        'date': today_str,
        'alignment_strength': 'Unknown',
        'focus_area': 'Unknown',
        'timing_posture': 'Unknown',
    }


# ── structural pressure check ─────────────────────────────────────────────────

def _crosses_pressure_threshold(candidate: dict) -> bool:
    """Return True if this candidate meets structural pressure threshold."""
    if candidate.get('max_gap_breached'):
        return True
    if candidate.get('overdue_ratio', 0) >= THRESHOLD_OVERDUE_RATIO:
        return True
    if candidate.get('gap_percentile', 0) >= THRESHOLD_GAP_PERCENTILE:
        return True
    return False


def _alignment_is_active(soul_compass: dict) -> bool:
    """Return True if Soul Compass says today is an action day."""
    strength = (soul_compass.get('alignment_strength') or '').lower()
    posture  = (soul_compass.get('timing_posture') or '').lower()
    if strength in ALIGNED_STRENGTHS:
        return True
    if 'lean in' in posture or 'engage' in posture:
        return True
    return False


# ── alert builder ─────────────────────────────────────────────────────────────

def _celestial_tier(score: float) -> str:
    """Map a 0.0–1.0 fingerprint similarity score to a subscriber-facing tier label."""
    for threshold, label in CELESTIAL_MATCH_TIERS:
        if score >= threshold:
            return label
    return 'Weak Match'


def _build_alert(candidate: dict, game: str, soul_compass: dict,
                 stale: bool, today: date) -> ConvergenceAlert:
    """Build a ConvergenceAlert from a qualified candidate + Soul Compass data."""

    number          = candidate['number']
    signal_label    = candidate['signal']
    overdue_ratio   = candidate['overdue_ratio']
    current_gap     = candidate['current_gap_draws']
    avg_gap         = candidate['avg_gap_draws']
    max_breached    = candidate.get('max_gap_breached', False)
    session         = (candidate.get('session_affinity') or 'Midday')
    days_since      = candidate.get('days_since_last_hit') or 0
    draw_time       = SESSION_DRAW_TIMES.get(session, '')
    alignment       = soul_compass.get('alignment_strength', 'Unknown')
    posture         = soul_compass.get('timing_posture', '')

    # Celestial fingerprint match — already computed by triple_due_signal
    cm              = candidate.get('condition_match') or {}
    cm_score        = float(cm.get('score', 0.5))
    cm_tier         = _celestial_tier(cm_score)
    cm_verdict      = cm.get('verdict', '')
    cm_matching     = cm.get('matching_factors', [])

    # Preferred window proximity (days until peak celestial window)
    preferred_window_days_away = candidate.get('preferred_window_days_away')

    # ── headline ──────────────────────────────────────────────────────────────
    if max_breached:
        headline = (
            f"⚡ {number} | {game} | {session} — RECORD GAP ALERT\n"
            f"Structural pressure is at an all-time high. "
            f"The conditions are active. {cm_tier}."
        )
    else:
        headline = (
            f"🎯 {number} | {game} | {session} — Active Window\n"
            f"{current_gap} draws since last hit ({overdue_ratio:.1f}× average). "
            f"{cm_tier}."
        )

    # ── body ──────────────────────────────────────────────────────────────────
    body_parts = []

    body_parts.append(
        f"{number} is currently {current_gap} draws since its last appearance "
        f"(average gap: {int(avg_gap)} draws, overdue ratio: {overdue_ratio:.2f}×)."
    )

    if max_breached:
        body_parts.append(
            f"This is the longest recorded absence for {number} in our entire history. "
            f"Structural pressure at this level is the strongest signal the system can produce. "
            f"When a number reaches this threshold, the conditions are set regardless of "
            f"any other variable."
        )
    else:
        body_parts.append(
            f"The gap percentile places this in the top "
            f"{100 - int(candidate.get('gap_percentile', 85))}% of all historical absences."
        )

    # Celestial fingerprint match — measurable, not philosophical
    if cm_matching:
        body_parts.append(
            f"Celestial conditions: {cm_tier}. "
            + cm_matching[0]  # lead with the strongest matching factor
        )
    elif cm_verdict:
        body_parts.append(
            f"Celestial conditions: {cm_tier}. {cm_verdict}."
        )

    if stale:
        body_parts.append(
            f"Note: draw data has a freshness lag. "
            f"The gap and pressure readings are based on available history. "
            f"{'Even with stale data, a record gap cannot be reduced.' if max_breached else 'Interpret the timing layer with mild caution.'}"
        )

    if preferred_window_days_away is not None and 0 < preferred_window_days_away <= 14:
        body_parts.append(
            f"The peak celestial window for {number} opens in approximately "
            f"{preferred_window_days_away} day(s). Structural pressure is sufficient to act now; "
            f"the next {preferred_window_days_away} days represent the combined peak."
        )

    if session and draw_time:
        body_parts.append(
            f"Historical session: {number} shows its highest affinity for the "
            f"{session} draw ({draw_time})."
        )

    body = ' '.join(body_parts)

    # ── play instruction ──────────────────────────────────────────────────────
    play_instruction = (
        f"Play {number} | {game} | {session} ({draw_time}) | "
        f"Straight recommended. If your compass is pointing here, this is your window."
    )

    return ConvergenceAlert(
        game=game,
        number=number,
        signal_label=signal_label,
        overdue_ratio=overdue_ratio,
        current_gap=current_gap,
        avg_gap=avg_gap,
        max_gap_breached=max_breached,
        session=session,
        draw_time=draw_time,
        alignment_strength=alignment,
        timing_posture=posture,
        stale_data=stale,
        days_since_hit=days_since,
        preferred_window_days_away=preferred_window_days_away,
        celestial_match_score=round(cm_score, 2),
        celestial_match_tier=cm_tier,
        headline=headline,
        body=body,
        play_instruction=play_instruction,
        generated_at=datetime.now().isoformat(),
    )


# ── main public API ───────────────────────────────────────────────────────────

def scan_for_convergence(
    games: Optional[list] = None,
    today: Optional[date] = None,
    require_alignment: bool = True,
    extra_draws_cash3: Optional[list] = None,
    extra_draws_cash4: Optional[list] = None,
) -> list:
    """
    Main entry point. Call before each draw session.

    Parameters
    ----------
    games            : list of game strings to scan, default ['Cash3', 'Cash4']
    today            : override today's date (used in back-tests)
    require_alignment: if True, both structural + Soul Compass must qualify.
                       if False, structural pressure alone is sufficient.
    extra_draws_*    : in-memory draws to merge (Railway live-ingest path)

    Returns
    -------
    List of ConvergenceAlert objects, sorted by structural pressure (highest first).
    Empty list = no alerts today.
    """
    games  = games or ['Cash3', 'Cash4']
    today  = today or date.today()

    soul_compass  = _load_soul_compass(today)
    alignment_ok  = _alignment_is_active(soul_compass) if require_alignment else True

    alerts = []

    for game in games:
        extra = extra_draws_cash3 if game == 'Cash3' else extra_draws_cash4
        try:
            result = compute_due_signal(game, extra_draws=extra)
        except Exception as e:
            print(f"[convergence_alert] compute_due_signal({game}) error: {e}")
            continue

        stale = result.get('data_freshness', {}).get('is_stale', False)
        candidates = result.get('ranked', [])

        for candidate in candidates:
            if not _crosses_pressure_threshold(candidate):
                continue
            if require_alignment and not alignment_ok:
                continue

            alert = _build_alert(
                candidate=candidate,
                game=game,
                soul_compass=soul_compass,
                stale=stale,
                today=today,
            )
            alerts.append(alert)

    # Sort: record-gap breaches first, then by overdue ratio descending
    alerts.sort(
        key=lambda a: (int(a.max_gap_breached), a.overdue_ratio),
        reverse=True,
    )

    return alerts


def scan_and_print(games=None, require_alignment=True):
    """
    CLI helper — run directly to see today's convergence alerts.

    Usage:
        python convergence_alert.py
        python convergence_alert.py --no-alignment   (structural only)
    """
    import argparse
    import sys as _sys
    # Ensure UTF-8 output on Windows terminals that default to cp1252
    if hasattr(_sys.stdout, 'reconfigure'):
        try:
            _sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    parser = argparse.ArgumentParser(description='MyBestOdds Convergence Alert Scanner')
    parser.add_argument('--no-alignment', action='store_true',
                        help='Skip Soul Compass alignment requirement')
    parser.add_argument('--game', default=None,
                        help='Scan one game only: Cash3 or Cash4')
    args = parser.parse_args()

    _require = not args.no_alignment
    _games   = [args.game] if args.game else None

    alerts = scan_for_convergence(games=_games, require_alignment=_require)

    if not alerts:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] No convergence alerts today.")
        return

    print(f"\n{'='*60}")
    print(f"  CONVERGENCE ALERTS  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    for i, alert in enumerate(alerts, 1):
        print(f"ALERT {i}")
        print(f"  {alert.headline}")
        print()
        print(f"  {alert.body}")
        print()
        print(f"  Celestial match: {alert.celestial_match_tier} ({alert.celestial_match_score:.2f})")
        print(f"  ▶  {alert.play_instruction}")
        print(f"{'─'*60}\n")


if __name__ == '__main__':
    scan_and_print()
