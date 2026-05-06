"""
triple_due_signal.py
====================
Predicts WHEN a triple (Cash3) or quad (Cash4) is likely to fall next.

Five-factor model:
  1. Overdue Ratio      — current gap / historical average gap (primary driver, 45%)
  2. Gap Percentile     — where current gap sits in all historical gaps (30%)
  3. Digit Heat         — how frequently this digit appeared in recent 100 draws (15%)
  4. Frequency Trend    — hit rate accelerating or decelerating in recent half of history (10%)
  5. Max Gap Breach     — binary bonus when current gap exceeds historical maximum

Signal labels: EXTREME | STRONG | MODERATE | WATCH | COLD
"""

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'ga_results')

# Overlay engine is in the same core package
_CORE_DIR = os.path.dirname(__file__)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

try:
    from overlay_engine_v3_7 import compute_overlays as _compute_overlays
    _OVERLAYS_AVAILABLE = True
except ImportError:
    _OVERLAYS_AVAILABLE = False

# GA Lottery payout tables (straight only — triples/quads have one arrangement)
_PAYOUT = {
    'Cash3': {'label': 'Cash3 Triple', 'straight_per_dollar': 500},
    'Cash4': {'label': 'Cash4 Quad',   'straight_per_dollar': 5000},
}

_WAGER_LEVELS = [
    {'bet': '$1',  'label': 'Entry play'},
    {'bet': '$2',  'label': 'Moderate conviction'},
    {'bet': '$5',  'label': 'Strong conviction'},
    {'bet': '$10', 'label': 'High conviction'},
]

# ─────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────

def _parse_date(s: str):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _build_data_freshness(draws: list, today_dt: datetime = None) -> dict:
    """Compute draw-data freshness metadata for subscriber-facing transparency."""
    if today_dt is None:
        today_dt = datetime.now()

    if not draws:
        return {
            'as_of_date': None,
            'days_since_latest_draw': None,
            'is_stale': True,
            'stale_after_days': 2,
            'status': 'STALE',
            'message': 'No historical draw data available for freshness validation.',
        }

    as_of_dt = draws[-1]['date']
    as_of_str = draws[-1]['date_str']
    days_old = (today_dt.date() - as_of_dt.date()).days
    stale_after_days = 2
    is_stale = days_old > stale_after_days

    return {
        'as_of_date': as_of_str,
        'days_since_latest_draw': days_old,
        'is_stale': is_stale,
        'stale_after_days': stale_after_days,
        'status': 'STALE' if is_stale else 'FRESH',
        'message': (
            f"Draw history is {days_old} day(s) behind live calendar; interpret Triples & Quads Signal output with caution."
            if is_stale else
            'Draw history is within freshness window.'
        ),
    }


def _load_draws(game: str, extra_draws: list = None) -> list:
    """Load all sessions for a game, dedup by date+session, sort chronologically.

    extra_draws: optional list of dicts with keys draw_date, winning_numbers, session
    (same shape as _ga_extra_entries values) to merge with disk data.
    Used on Railway where disk JSON files are reset on each redeploy.
    """
    if game == 'Cash3':
        files = ['cash3_midday.json', 'cash3_evening.json', 'cash3_night.json']
        n_digits = 3
    else:
        files = ['cash4_midday.json', 'cash4_evening.json', 'cash4_night.json']
        n_digits = 4

    SESSION_ORDER = {'midday': 0, 'mid': 0, 'cash3_midday': 0, 'cash4_midday': 0,
                     'evening': 1, 'eve': 1, 'cash3_evening': 1, 'cash4_evening': 1,
                     'night': 2, 'cash3_night': 2, 'cash4_night': 2}

    seen = set()
    all_draws = []
    for fname in files:
        session_key = fname.replace('.json', '').split('_', 1)[1]  # midday / evening / night
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        draws = data.get('draws', data) if isinstance(data, dict) else data
        for d in draws:
            raw_num = d.get('winning_number', '')
            num = raw_num[:n_digits]
            if len(num) < n_digits:
                continue
            raw_date = d.get('draw_date') or d.get('date', '')
            parsed = _parse_date(raw_date)
            if parsed is None:
                continue
            key = (parsed.strftime('%Y-%m-%d'), session_key)
            if key in seen:
                continue
            seen.add(key)
            all_draws.append({
                'date_str': parsed.strftime('%Y-%m-%d'),
                'date': parsed,
                'number': num,
                'session': session_key,
                'session_order': SESSION_ORDER.get(session_key, 9),
            })

    # Merge in-memory entries (e.g. Railway runtime ingests not yet on disk)
    for d in (extra_draws or []):
        raw_num = str(d.get('winning_numbers') or d.get('winning_number') or '')
        num = raw_num[:n_digits]
        if len(num) < n_digits:
            continue
        raw_date = d.get('draw_date') or d.get('date', '')
        parsed = _parse_date(raw_date)
        if parsed is None:
            continue
        sess_raw = str(d.get('session') or 'night').lower()
        session_key = {'mid': 'midday', 'midday': 'midday',
                       'eve': 'evening', 'evening': 'evening',
                       'night': 'night'}.get(sess_raw, sess_raw)
        key = (parsed.strftime('%Y-%m-%d'), session_key)
        if key in seen:
            continue
        seen.add(key)
        all_draws.append({
            'date_str': parsed.strftime('%Y-%m-%d'),
            'date': parsed,
            'number': num,
            'session': session_key,
            'session_order': SESSION_ORDER.get(session_key, 9),
        })

    all_draws.sort(key=lambda x: (x['date'], x['session_order']))
    return all_draws


# ─────────────────────────────────────────────
# Core analysis
# ─────────────────────────────────────────────

def _gap_percentile(current_gap: int, gaps: list) -> float:
    """Return fraction of historical gaps that current_gap exceeds (0.0 – 1.0)."""
    if not gaps:
        return 0.5
    return sum(1 for g in gaps if current_gap > g) / len(gaps)


def _digit_heat(digit: str, recent_draws: list) -> float:
    """Fraction of recent draws that contain this digit in any position."""
    if not recent_draws:
        return 0.0
    return sum(1 for d in recent_draws if digit in d['number']) / len(recent_draws)


def _frequency_trend(hits: list, total: int) -> float:
    """
    Compare hit rate in the first half vs second half of history.
    Returns > 1.0 if accelerating (more hits recently), < 1.0 if decelerating.
    """
    if len(hits) < 2:
        return 1.0
    midpoint = total // 2
    first_half = sum(1 for h in hits if h < midpoint)
    second_half = len(hits) - first_half
    # Normalize per draw count
    first_rate = first_half / midpoint if midpoint > 0 else 0
    second_rate = second_half / (total - midpoint) if (total - midpoint) > 0 else 0
    if first_rate == 0:
        return 2.0 if second_rate > 0 else 1.0
    return second_rate / first_rate


def _build_narrative(num: str, game: str, current_gap: int, avg_gap: float,
                     overdue_ratio: float, gap_pct: float, last_hit_date: str,
                     days_since: int, signal: str, session_affinity: str) -> str:
    """Human-readable explanation optimized for subscriber display."""
    lines = []

    if last_hit_date:
        lines.append(
            f"{num} last hit {last_hit_date} ({days_since} day{'s' if days_since != 1 else ''} ago)."
        )
    else:
        lines.append(f"{num} has never been recorded in this window.")

    if avg_gap > 0:
        lines.append(
            f"It is currently {current_gap} draws into a cycle that averages {int(avg_gap)} draws between hits "
            f"({overdue_ratio:.1f}x its normal interval)."
        )
    if gap_pct >= 0.5:
        pct_label = int(gap_pct * 100)
        lines.append(
            f"Historically, only {100 - pct_label}% of {game} gaps have been this long."
        )
    
    if session_affinity:
        lines.append(f"When it does fall, it favors the {session_affinity} draw.")

    if signal == 'EXTREME':
        lines.append("EXTREME: This combination has exceeded its longest-ever recorded gap — it is statistically overdue at the highest level.")
    elif signal == 'STRONG':
        lines.append("STRONG signal: Gap analysis and digit frequency both indicate elevated likelihood.")
    elif signal == 'MODERATE':
        lines.append("MODERATE signal: Worth tracking — probability rising above baseline.")
    elif signal == 'WATCH':
        lines.append("On the watch list — not yet at peak due level.")
    else:
        lines.append("Below threshold — gap is within the normal recent-hit window.")

    return ' '.join(lines)


def compute_due_signal(game: str, extra_draws: list = None) -> dict:
    """
    Full Triples & Quads Signal analysis for Cash3 (triples) or Cash4 (quads).

    Returns
    -------
    dict with keys:
      game, total_draws_analyzed, as_of_date,
      ranked (all 10 candidates sorted by likelihood desc),
      top_pick (highest likelihood),
      strong_signals, extreme_signals
    """
    draws = _load_draws(game, extra_draws=extra_draws)
    if not draws:
        return {'game': game, 'error': 'No draw data found', 'ranked': []}

    data_freshness = _build_data_freshness(draws)

    n_digits = 3 if game == 'Cash3' else 4
    total = len(draws)
    today_dt = datetime.now()

    # Build hit index per candidate
    hit_indices: dict = defaultdict(list)
    for idx, d in enumerate(draws):
        num = d['number']
        if len(num) == n_digits and len(set(num)) == 1:
            hit_indices[num].append(idx)

    recent_window = draws[-100:] if total >= 100 else draws

    results = []
    for digit in map(str, range(10)):
        candidate = digit * n_digits

        hits = hit_indices.get(candidate, [])
        n_hits = len(hits)

        # Current gap
        if hits:
            current_gap = (total - 1) - hits[-1]
            last_hit_date_str = draws[hits[-1]]['date_str']
            last_hit_dt = draws[hits[-1]]['date']
            days_since = (today_dt - last_hit_dt).days
        else:
            current_gap = total
            last_hit_date_str = None
            last_hit_dt = None
            days_since = None

        # Historical inter-hit gaps
        gaps = [hits[i] - hits[i - 1] for i in range(1, len(hits))]

        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            max_gap = max(gaps)
            std_gap = math.sqrt(sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)) if len(gaps) > 1 else 0
        else:
            # Theoretical: 1 specific triple per 10^n_digits draws, 10 candidates
            theoretical_rate = 1.0 / (10 ** n_digits) * 10
            avg_gap = 1.0 / theoretical_rate if theoretical_rate > 0 else total
            max_gap = avg_gap
            std_gap = 0

        # Factor 1: Overdue ratio (capped at 3.0 for scoring)
        overdue_ratio = current_gap / avg_gap if avg_gap > 0 else 0.0
        f1 = min(overdue_ratio, 3.0) / 3.0  # normalize to 0–1

        # Factor 2: Gap percentile
        gap_pct = _gap_percentile(current_gap, gaps)
        f2 = gap_pct  # already 0–1

        # Factor 3: Digit heat
        heat = _digit_heat(digit, recent_window)
        f3 = min(heat / 0.35, 1.0)  # 35% appearance = saturate (expected ~30%)

        # Factor 4: Frequency trend
        trend = _frequency_trend(hits, total)
        f4 = min(trend / 2.0, 1.0)  # normalize: trend=2 means recent hits doubled → saturate

        # Factor 5: Max gap breach (binary bonus)
        f5 = 1.0 if (gaps and current_gap > max_gap) else 0.0

        # Combined likelihood score (weighted)
        # Weights: overdue 45%, percentile 30%, heat 15%, trend 10%
        # Bonus for max breach: +0.5 additive
        likelihood = (f1 * 0.45) + (f2 * 0.30) + (f3 * 0.15) + (f4 * 0.10) + (f5 * 0.50)

        # Session affinity: which session did this triple most recently hit in, 
        # and historically which session accounts for most hits?
        session_counts: dict = defaultdict(int)
        for h_idx in hits:
            session_counts[draws[h_idx]['session']] += 1
        session_affinity = max(session_counts, key=session_counts.get).capitalize() if session_counts else ''

        # Statistical hit probability in next 10 draws
        base_p = n_hits / total if n_hits > 0 else 1.0 / (10 ** n_digits)
        p_next_10 = (1.0 - (1.0 - base_p) ** 10) * 100  # percent

        # Signal label
        if f5 == 1.0 or overdue_ratio >= 2.5:
            signal = 'EXTREME'
        elif likelihood >= 0.65 or overdue_ratio >= 1.5:
            signal = 'STRONG'
        elif likelihood >= 0.45:
            signal = 'MODERATE'
        elif likelihood >= 0.25:
            signal = 'WATCH'
        else:
            signal = 'COLD'

        narrative = _build_narrative(
            num=candidate, game=game,
            current_gap=current_gap, avg_gap=avg_gap,
            overdue_ratio=overdue_ratio, gap_pct=gap_pct,
            last_hit_date=last_hit_date_str,
            days_since=days_since if days_since is not None else 0,
            signal=signal, session_affinity=session_affinity,
        )

        results.append({
            'number': candidate,
            'digit': digit,
            'hits_in_window': n_hits,
            'current_gap_draws': current_gap,
            'avg_gap_draws': round(avg_gap, 1),
            'max_gap_draws': int(max_gap),
            'overdue_ratio': round(overdue_ratio, 2),
            'gap_percentile': round(gap_pct * 100, 1),
            'digit_heat': round(heat, 3),
            'frequency_trend': round(trend, 2),
            'max_gap_breached': bool(f5),
            'likelihood_score': round(likelihood, 3),
            'p_hit_next_10_draws_pct': round(p_next_10, 2),
            'signal': signal,
            'session_affinity': session_affinity,
            'last_hit_date': last_hit_date_str,
            'days_since_last_hit': days_since,
            'narrative': narrative,
        })

    results.sort(key=lambda x: x['likelihood_score'], reverse=True)

    return {
        'game': game,
        'total_draws_analyzed': total,
        'as_of_date': draws[-1]['date_str'] if draws else None,
        'data_freshness': data_freshness,
        'ranked': results,
        'top_pick': results[0] if results else None,
        'extreme_signals': [r for r in results if r['signal'] == 'EXTREME'],
        'strong_signals': [r for r in results if r['signal'] == 'STRONG'],
        'moderate_signals': [r for r in results if r['signal'] == 'MODERATE'],
        'active_signals': [r for r in results if r['signal'] in ('EXTREME', 'STRONG', 'MODERATE')],
    }


# ─────────────────────────────────────────────────────────────────────
# Subscriber Query: check_number()
# ─────────────────────────────────────────────────────────────────────

def _mode(values: list):
    """Return the most common value in a list, or None if empty."""
    if not values:
        return None
    counts = defaultdict(int)
    for v in values:
        counts[v] += 1
    return max(counts, key=counts.get)


def _pct(count: int, total: int) -> str:
    if total == 0:
        return '0%'
    return f"{round(count / total * 100)}%"


def _session_label(raw: str) -> str:
    return {'midday': 'Midday', 'evening': 'Evening', 'night': 'Night'}.get(raw.lower(), raw.capitalize())


def _build_condition_fingerprint(draws: list, hit_indices: list) -> dict:
    """
    For each historical hit of a candidate number, compute the overlay conditions
    (moon phase, zodiac, numerology, planetary hour, day-of-week, month) and
    return their frequency distributions.

    Returns dict with top condition for each factor + full counts.
    """
    moon_counts: dict = defaultdict(int)
    zodiac_counts: dict = defaultdict(int)
    numerology_counts: dict = defaultdict(int)
    session_counts: dict = defaultdict(int)
    dow_counts: dict = defaultdict(int)
    month_counts: dict = defaultdict(int)

    for idx in hit_indices:
        d = draws[idx]
        date_str = d['date_str']
        session_raw = d['session']
        session_ui = {'midday': 'Midday', 'evening': 'Evening', 'night': 'Night'}.get(session_raw, 'Midday')

        session_counts[session_raw] += 1
        month_counts[d['date'].strftime('%B')] += 1
        dow_counts[d['date'].strftime('%A')] += 1

        if _OVERLAYS_AVAILABLE:
            try:
                ov = _compute_overlays(date_str, session_ui)
                moon_counts[ov['moon_phase']] += 1
                zodiac_counts[ov['zodiac_sign']] += 1
                numerology_counts[ov['numerology_code']] += 1
            except Exception:
                pass

    n = len(hit_indices)
    return {
        'hit_count': n,
        'moon_phases': dict(moon_counts),
        'top_moon_phase': _mode(list(moon_counts.keys())) if moon_counts else None,
        'zodiac_seasons': dict(zodiac_counts),
        'top_zodiac': _mode(list(zodiac_counts.keys())) if zodiac_counts else None,
        'numerology_codes': dict(numerology_counts),
        'top_numerology': _mode(list(numerology_counts.keys())) if numerology_counts else None,
        'sessions': dict(session_counts),
        'top_session': _mode(list(session_counts.keys())) if session_counts else None,
        'days_of_week': dict(dow_counts),
        'top_day_of_week': _mode(list(dow_counts.keys())) if dow_counts else None,
        'months': dict(month_counts),
        'top_month': _mode(list(month_counts.keys())) if month_counts else None,
        'overlays_available': _OVERLAYS_AVAILABLE,
        'note': None if (_OVERLAYS_AVAILABLE and n > 0) else (
            'Overlay engine unavailable — moon/zodiac/numerology conditions not computed.' if not _OVERLAYS_AVAILABLE
            else 'No historical hits in data window — conditions cannot be fingerprinted.'
        ),
    }


def _score_condition_match(fingerprint: dict, today_date: datetime, number: str = '') -> dict:
    """
    Compare today's overlay conditions to the historical hit fingerprint.

    Scoring weights:
      Moon phase match      25%
      Zodiac season match   25%
      Numerology match      20%
      Day of week match     15%
      Month match           15%

    Returns score (0-1), match detail, and best session recommendation.
    """
    num = number or 'this number'
    if not _OVERLAYS_AVAILABLE or fingerprint['hit_count'] == 0:
        return {
            'score': 0.5,
            'pct': 50,
            'verdict': 'UNKNOWN',
            'matching_factors': [],
            'mismatching_factors': [],
            'note': 'Insufficient historical data or overlay engine unavailable for condition matching.',
            'today_conditions': {},
            'best_session': None,
        }

    today_str = today_date.strftime('%Y-%m-%d')
    today_dow = today_date.strftime('%A')
    today_month = today_date.strftime('%B')

    # Compute today's overlays for each session
    sessions = ['Midday', 'Evening', 'Night']
    best_session = None
    best_session_score = -1.0
    today_ov_by_session = {}

    for sess in sessions:
        try:
            ov = _compute_overlays(today_str, sess)
            today_ov_by_session[sess] = ov
            # Quick alignment check for this session
            s = 0.0
            if fingerprint['top_moon_phase'] and ov.get('moon_phase') == fingerprint['top_moon_phase']:
                s += 0.3
            if fingerprint['top_zodiac'] and ov.get('zodiac_sign') == fingerprint['top_zodiac']:
                s += 0.3
            if s > best_session_score:
                best_session_score = s
                best_session = sess
        except Exception:
            pass

    # Use affinity session (top_session) if overlay session is indeterminate
    if best_session is None:
        best_session = _session_label(fingerprint['top_session'] or 'midday')

    today_ov = today_ov_by_session.get(best_session, {})

    # Factor scores
    score = 0.0
    matching = []
    mismatching = []
    total_hits = fingerprint['hit_count']

    # Moon phase (25%)
    top_moon = fingerprint['top_moon_phase']
    today_moon = today_ov.get('moon_phase')
    moon_hit_count = fingerprint['moon_phases'].get(top_moon, 0) if top_moon else 0
    if top_moon and today_moon == top_moon:
        score += 0.25
        matching.append(
            f"{today_moon} — when {num} has hit in the past, the moon was in this phase {_pct(moon_hit_count, total_hits)} of the time. That matches today."
        )
    elif today_moon and top_moon:
        mismatching.append(
            f"Moon: historically {num} tends to fall during a {top_moon}, not a {today_moon}."
        )

    # Zodiac season (25%)
    top_zodiac = fingerprint['top_zodiac']
    today_zodiac = today_ov.get('zodiac_sign')
    zodiac_hit_count = fingerprint['zodiac_seasons'].get(top_zodiac, 0) if top_zodiac else 0
    if top_zodiac and today_zodiac == top_zodiac:
        score += 0.25
        matching.append(
            f"{today_zodiac} season — this is the zodiac period when {num} hit {_pct(zodiac_hit_count, total_hits)} of the time historically. We're in that window now."
        )
    elif today_zodiac and top_zodiac:
        mismatching.append(
            f"Season: {num} has typically fallen during {top_zodiac}, not {today_zodiac} where we are now."
        )

    # Numerology (20%)
    top_num = fingerprint['top_numerology']
    today_num_code = today_ov.get('numerology_code')
    num_hit_count = fingerprint['numerology_codes'].get(top_num, 0) if top_num else 0
    if top_num and today_num_code == top_num:
        score += 0.20
        matching.append(
            f"Today's date energy ({today_num_code}) lines up — {num} hit on days carrying this same energy {_pct(num_hit_count, total_hits)} of the time."
        )
    elif today_num_code and top_num:
        mismatching.append(
            f"Date energy: today carries a {today_num_code} energy; {num} has most often fallen on {top_num} days."
        )

    # Day of week (15%)
    top_dow = fingerprint['top_day_of_week']
    dow_hit_count = fingerprint['days_of_week'].get(top_dow, 0) if top_dow else 0
    if top_dow and today_dow == top_dow:
        score += 0.15
        matching.append(
            f"{today_dow}s have been good to {num} — {_pct(dow_hit_count, total_hits)} of past hits landed on this day of the week."
        )
    elif top_dow:
        mismatching.append(
            f"Day of week: {num} has shown up most on {top_dow}s, not {today_dow}s."
        )

    # Month (15%)
    top_month = fingerprint['top_month']
    month_hit_count = fingerprint['months'].get(top_month, 0) if top_month else 0
    if top_month and today_month == top_month:
        score += 0.15
        matching.append(
            f"{today_month} is a historically favorable month for {num} — {_pct(month_hit_count, total_hits)} of past hits came in this month."
        )
    elif top_month:
        mismatching.append(
            f"Month: {num} has hit most in {top_month}; we're currently in {today_month}."
        )

    pct = round(score * 100)
    if pct >= 75:
        verdict = 'CONDITIONS LINING UP'
    elif pct >= 50:
        verdict = 'SOME CONDITIONS MATCH'
    elif pct >= 25:
        verdict = 'A FEW THINGS LINE UP'
    else:
        verdict = 'CONDITIONS NOT THERE YET'

    # Low-hit-count caveat
    low_sample_note = None
    if total_hits < 3:
        low_sample_note = (
            f"Heads up: {num} has only hit {total_hits} time(s) in our records, "
            "so the pattern comparison is a guide, not a guarantee."
        )

    return {
        'score': round(score, 2),
        'pct': pct,
        'verdict': verdict,
        'matching_factors': matching,
        'mismatching_factors': mismatching,
        'best_session': best_session,
        'today_conditions': {
            'date': today_str,
            'day_of_week': today_dow,
            'month': today_month,
            'moon_phase': today_ov.get('moon_phase'),
            'zodiac_sign': today_ov.get('zodiac_sign'),
            'numerology_code': today_ov.get('numerology_code'),
            'planetary_hour': today_ov.get('planetary_hour'),
        },
        'note': low_sample_note,
        'weather_note': (
            'Weather data is not yet integrated into the condition fingerprint. '
            'This is a planned enhancement for a future release.'
        ),
    }


def _build_wager_guide(game: str, bet_amounts: list = None) -> list:
    payout_per_dollar = _PAYOUT.get(game, {}).get('straight_per_dollar', 500)
    levels = bet_amounts or ['$1', '$2', '$5', '$10']
    guide = []
    for lv in _WAGER_LEVELS:
        if lv['bet'] in levels:
            amt = int(lv['bet'].replace('$', ''))
            guide.append({
                'bet': lv['bet'],
                'payout': f"${amt * payout_per_dollar:,}",
                'label': lv['label'],
            })
    return guide


def _build_check_narrative(number: str, game: str, gap_data: dict,
                            condition_match: dict, verdict: str,
                            play_advice: dict,
                            fingerprint: dict = None,
                            confidence_label: str = '') -> str:
    """
    Self-contained narrative structured in four steps:
      1. Track record — what we know about this number historically
      2. The gap — how overdue it is and what that means
      3. The celestial picture — what lunar/seasonal conditions say
      4. Bottom line — confidence label + clear action
    """
    fp = fingerprint or {}
    parts = []
    n_hits = gap_data.get('hits_in_window', 0)
    last_hit = gap_data.get('last_hit_date')
    days_ago = gap_data.get('days_since_last_hit')
    total = gap_data.get('total_draws_analyzed', 0)
    game_label = 'Cash 3' if game == 'Cash3' else 'Cash 4'

    # ── STEP 1: Track record ──────────────────────────────────────────
    if n_hits == 0:
        parts.append(
            f"{number} has not appeared in our {game_label} history — which in itself is significant. "
            f"Across {total:,} draws, it has never hit. That kind of absence puts it in rare territory."
        )
    else:
        hit_word = 'once' if n_hits == 1 else f'{n_hits} times'
        if last_hit:
            parts.append(
                f"{number} has hit {hit_word} across our {game_label} records spanning {total:,} draws. "
                f"The most recent hit was {last_hit}, {days_ago} day{'s' if days_ago != 1 else ''} ago."
            )
        else:
            parts.append(
                f"{number} has hit {hit_word} in our {game_label} records across {total:,} draws."
            )

    # ── STEP 2: The gap ───────────────────────────────────────────────
    or_val = gap_data.get('overdue_ratio', 0)
    avg_gap = gap_data.get('avg_gap_draws', 0)
    cur_gap = gap_data.get('current_gap_draws', 0)
    gp = gap_data.get('gap_percentile', 0)
    max_breached = gap_data.get('max_gap_breached', False)

    if avg_gap > 0 and n_hits > 0:
        if or_val >= 2.5:
            parts.append(
                f"Historically it comes around every {int(avg_gap)} draws on average. "
                f"Right now it has been silent for {cur_gap:,} draws — that's {or_val:.1f}x its normal interval. "
                f"Very few numbers reach this level of absence."
            )
        elif or_val >= 1.0:
            parts.append(
                f"On average, {number} cycles through about every {int(avg_gap)} draws. "
                f"We're currently at {cur_gap:,} draws since the last hit — past its average window and building pressure."
            )
        else:
            parts.append(
                f"On average, {number} comes around every {int(avg_gap)} draws. "
                f"At {cur_gap:,} draws out, it's still inside its normal range."
            )

    if max_breached:
        parts.append(
            f"This is the longest stretch without {number} we have on record — it has surpassed its own historical maximum."
        )
    elif gp > 75 and n_hits > 0:
        parts.append(
            f"Looking at every recorded gap for {number}, only {100 - int(gp)}% have lasted this long. "
            "The probability of a hit rises the further it extends past this point."
        )

    # ── STEP 3: The celestial picture ────────────────────────────────
    matching = condition_match.get('matching_factors', [])
    mismatching = condition_match.get('mismatching_factors', [])
    top_moon = fp.get('top_moon_phase')
    top_zodiac = fp.get('top_zodiac')
    today_cond = condition_match.get('today_conditions', {})
    today_moon = today_cond.get('moon_phase', '')
    today_zodiac = today_cond.get('zodiac_sign', '')

    if matching:
        astro_lines = []
        for m in matching[:2]:
            astro_lines.append(m)
        parts.append(
            f"On the celestial side, the conditions today are working in {number}'s favor. "
            + ' '.join(astro_lines)
        )
        if mismatching:
            parts.append(
                f"One factor that doesn't align: {mismatching[0]} "
                "— but with more conditions matching than not, the overall picture is favorable."
            )
    elif top_moon and top_zodiac:
        parts.append(
            f"Looking at the celestial conditions when {number} has hit in the past, "
            f"it has favored a {top_moon} during {top_zodiac} season. "
            f"Today we're sitting in a {today_moon} under {today_zodiac} — "
            + (
                "the sky hasn't quite turned to its preferred window yet, but that window will come."
                if or_val >= 1.0 else
                "the timing isn't aligned yet."
            )
        )
    elif not matching and not mismatching:
        parts.append(
            f"We don't yet have enough historical hits for {number} to map a reliable celestial pattern. "
            "The gap data carries more weight here."
        )

    # ── Session insight ───────────────────────────────────────────────
    sess_reason = play_advice.get('session_reason', '')
    if sess_reason:
        parts.append(sess_reason)

    # ── STEP 4: Bottom line ───────────────────────────────────────────
    conf_phrase = f"Our system rates this {confidence_label}" if confidence_label else 'Our system'

    if verdict == 'PLAY — STRONG CONDITIONS':
        parts.append(
            f"{conf_phrase}. The historical gap and the celestial conditions are both pointing the same way — "
            "that combination doesn't come together often. This is a well-supported play."
        )
    elif verdict == 'PLAY — GAP DRIVEN':
        parts.append(
            f"{conf_phrase}. The gap has grown to a level where the data makes a compelling case on its own. "
            "The celestial window isn't perfectly aligned today, but the length of this absence is the stronger signal."
        )
    elif verdict == 'WATCH — CONDITIONS ALIGN':
        parts.append(
            f"{conf_phrase}. The moon and seasonal conditions mirror past {number} hits, which is encouraging. "
            "However, the gap hasn't built to the level that makes this a high-conviction play yet. "
            "Track it — if it stays out another few weeks, the case strengthens."
        )
    elif verdict == 'HOLD — NOT YET DUE':
        parts.append(
            f"{conf_phrase}. {number} hasn't been out long enough for the data to support the play right now. "
            "Your instinct may be correct — just early. Revisit in a couple of weeks."
        )
    else:
        parts.append(
            f"{conf_phrase}. Multiple factors are developing but haven't fully converged yet. "
            "Give it a little more time and check back after the next few draws."
        )

    return ' '.join(parts)


def check_number(number_str: str, today: datetime = None, extra_draws: list = None) -> dict:
    """
    Subscriber-query entry point.

    Parameters
    ----------
    number_str : str
        The triple or quad the subscriber wants to check (e.g. '555', '3333').
        Must be all identical digits and 3 or 4 characters long.
    today : datetime, optional
        Override "today" — defaults to datetime.now().

    Returns
    -------
    dict with keys:
        number, game, type, valid,
        gap_analysis, historical_conditions, condition_match,
        verdict, verdict_label, confidence_score,
        play_advice, narrative
    """
    if today is None:
        today = datetime.now()

    # ── Validate input ────────────────────────────────────────────────
    num = number_str.strip()
    if not num.isdigit():
        return {
            'valid': False,
            'error': f"'{number_str}' is not a valid number. Please enter digits only (e.g. 555 or 3333).",
        }
    if len(num) == 3:
        game = 'Cash3'
        n_type = 'triple'
    elif len(num) == 4:
        game = 'Cash4'
        n_type = 'quad'
    else:
        return {
            'valid': False,
            'error': f"'{number_str}' must be 3 digits (Cash3 triple) or 4 digits (Cash4 quad).",
        }

    if len(set(num)) != 1:
        suggested = num[0] * len(num)
        return {
            'valid': False,
            'number_submitted': num,
            'error': (
                f"'{num}' is not a triple/quad — all digits must be the same. "
                f"Did you mean {suggested}? "
                f"Or check our regular Cash{len(num)} predictions for mixed numbers."
            ),
        }

    digit = num[0]

    # ── Load draws + locate hits ──────────────────────────────────────
    draws = _load_draws(game, extra_draws=extra_draws)
    if not draws:
        return {'valid': False, 'error': f'No draw data available for {game}.'}

    data_freshness = _build_data_freshness(draws, today_dt=today)

    total = len(draws)
    hit_indices_map: dict = defaultdict(list)
    for idx, d in enumerate(draws):
        raw = d['number']
        if len(raw) == len(num) and len(set(raw)) == 1:
            hit_indices_map[raw].append(idx)

    hits = hit_indices_map.get(num, [])
    n_hits = len(hits)

    # ── Gap analysis (single number) ─────────────────────────────────
    if hits:
        current_gap = (total - 1) - hits[-1]
        last_hit_date_str = draws[hits[-1]]['date_str']
        last_hit_dt = draws[hits[-1]]['date']
        days_since = (today - last_hit_dt).days
    else:
        current_gap = total
        last_hit_date_str = None
        last_hit_dt = None
        days_since = None

    gaps = [hits[i] - hits[i - 1] for i in range(1, len(hits))]
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
    else:
        theoretical_rate = 1.0 / (10 ** len(num)) * 10
        avg_gap = 1.0 / theoretical_rate if theoretical_rate > 0 else total
        max_gap = avg_gap

    overdue_ratio = current_gap / avg_gap if avg_gap > 0 else 0.0
    gap_pct = _gap_percentile(current_gap, gaps)
    max_gap_breached = bool(gaps and current_gap > max_gap)

    recent_window = draws[-100:] if total >= 100 else draws
    heat = _digit_heat(digit, recent_window)
    trend = _frequency_trend(hits, total)

    f1 = min(overdue_ratio, 3.0) / 3.0
    f2 = gap_pct
    f3 = min(heat / 0.35, 1.0)
    f4 = min(trend / 2.0, 1.0)
    f5 = 1.0 if max_gap_breached else 0.0
    gap_likelihood = (f1 * 0.45) + (f2 * 0.30) + (f3 * 0.15) + (f4 * 0.10) + (f5 * 0.50)

    # Session affinity
    session_counts: dict = defaultdict(int)
    for h_idx in hits:
        session_counts[draws[h_idx]['session']] += 1
    session_affinity_raw = max(session_counts, key=session_counts.get) if session_counts else 'midday'
    session_affinity = _session_label(session_affinity_raw)

    gap_analysis = {
        'hits_in_window': n_hits,
        'total_draws_analyzed': total,
        'current_gap_draws': current_gap,
        'avg_gap_draws': round(avg_gap, 1),
        'max_gap_draws': int(max_gap),
        'overdue_ratio': round(overdue_ratio, 2),
        'gap_percentile': round(gap_pct * 100, 1),
        'max_gap_breached': max_gap_breached,
        'digit_heat': round(heat, 3),
        'frequency_trend': round(trend, 2),
        'gap_likelihood_score': round(gap_likelihood, 3),
        'last_hit_date': last_hit_date_str,
        'days_since_last_hit': days_since,
        'session_affinity': session_affinity,
    }

    # ── Condition fingerprint ─────────────────────────────────────────
    fingerprint = _build_condition_fingerprint(draws, hits)
    condition_match = _score_condition_match(fingerprint, today, number=num)

    # Override best session: prefer fingerprint affinity if condition match is low
    best_session = condition_match.get('best_session') or session_affinity

    # ── Blended confidence score ──────────────────────────────────────
    # Gap is primary (70%), condition alignment secondary (30%)
    cm_score = condition_match['score']
    blended = (gap_likelihood * 0.70) + (cm_score * 0.30)

    # If the underlying draw history is stale, reduce confidence so output remains honest.
    if data_freshness.get('is_stale'):
        blended *= 0.75

    confidence_score = round(min(blended, 1.0), 3)

    # Confidence label
    if confidence_score >= 0.75:
        conf_label = 'OVERDUE ALERT'
        conf_color = 'red'
    elif confidence_score >= 0.55:
        conf_label = 'TRIPLES & QUADS SIGNAL'
        conf_color = 'orange'
    elif confidence_score >= 0.35:
        conf_label = 'BUILDING'
        conf_color = 'yellow'
    elif confidence_score >= 0.20:
        conf_label = 'WATCH'
        conf_color = 'blue-gray'
    else:
        conf_label = 'COLD'
        conf_color = 'gray'

    if data_freshness.get('is_stale'):
        conf_label = f"{conf_label} (STALE DATA)"

    # ── Play verdict ──────────────────────────────────────────────────
    if gap_likelihood >= 0.55 and cm_score >= 0.50:
        verdict = 'PLAY — STRONG CONDITIONS'
        verdict_label = 'The data and the patterns are both pointing the same way. This is a well-supported play.'
    elif gap_likelihood >= 0.55 and cm_score < 0.50:
        verdict = 'PLAY — GAP DRIVEN'
        verdict_label = "It's been a long time. The gap alone makes this worth playing even though today's patterns aren't a perfect match."
    elif gap_likelihood < 0.40 and cm_score >= 0.60:
        verdict = 'WATCH — CONDITIONS ALIGN'
        verdict_label = "The patterns are lining up with past hits, but it hasn't been long enough since the last one. Keep it on your list."
    elif gap_likelihood < 0.30 and cm_score < 0.35:
        verdict = 'HOLD — NOT YET DUE'
        verdict_label = f"{num} came around recently enough that the timing isn't there yet. Give it more time."
    else:
        verdict = 'MONITOR'
        verdict_label = 'Something is building here. Not quite ready — check back in a week or two.'

    # ── Play advice ───────────────────────────────────────────────────
    payout_per_dollar = _PAYOUT.get(game, {}).get('straight_per_dollar', 500)
    draws_remaining = max(0, int(avg_gap) - current_gap)
    weeks_remaining = round(draws_remaining / (3 * 7), 1) if draws_remaining > 0 else 0  # 3 draws/day

    play_advice = {
        'play_type': 'STRAIGHT',
        'play_note': f"Every $1 pays ${payout_per_dollar:,}.",
        'session': best_session,
        'session_reason': (
            f"{num} has shown up in the {session_affinity} draw {_pct(session_counts.get(session_affinity_raw, 0), n_hits)} of the time."
            if n_hits > 0 else "We don't have enough session history to make a recommendation yet."
        ),
        'wager_guide': _build_wager_guide(game, ['$1', '$2', '$5', '$10']),
        'draws_until_avg_due': draws_remaining if draws_remaining > 0 else 'Already past its average window — actively due',
        'weeks_until_avg_due': weeks_remaining if draws_remaining > 0 else 0,
    }

    narrative = _build_check_narrative(
        number=num, game=game,
        gap_data=gap_analysis,
        condition_match=condition_match,
        verdict=verdict,
        play_advice=play_advice,
        fingerprint=fingerprint,
        confidence_label=conf_label,
    )

    if data_freshness.get('is_stale'):
        narrative = (
            f"Data freshness alert: analysis is based on draws through {data_freshness.get('as_of_date')} "
            f"({data_freshness.get('days_since_latest_draw')} day(s) old). "
            "Confidence is automatically reduced until fresh draws are ingested. "
            + narrative
        )

    return {
        'valid': True,
        'number': num,
        'game': game,
        'type': n_type,
        'digit': digit,
        'gap_analysis': gap_analysis,
        'historical_conditions': fingerprint,
        'condition_match': condition_match,
        'confidence_score': confidence_score,
        'confidence_label': conf_label,
        'confidence_color': conf_color,
        'verdict': verdict,
        'verdict_label': verdict_label,
        'play_advice': play_advice,
        'narrative': narrative,
        'as_of_date': draws[-1]['date_str'] if draws else None,
        'data_freshness': data_freshness,
    }
