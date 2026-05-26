"""
MMFSN PREDICTION ENGINE — Prototype using 742 as the template model.
Once validated, this becomes the subscriber-facing prediction tool for ALL MMFSN numbers.

For each MMFSN number, the engine outputs:
  - Convergence status (CRITICAL / HIGH / MODERATE / WATCH / COLD)
  - Predicted fall window (date range)
  - Best session to play
  - Confidence level
  - Subscriber alert message
"""
import csv, itertools, datetime, collections, statistics

C3_CSV = r"C:\MyBestOdds\jackpot_system_v3\data\ga_results\Cash3_Midday_Evening_Night.csv"
C4_CSV = r"C:\MyBestOdds\jackpot_system_v3\data\ga_results\Cash4_Midday_Evening_Night.csv"

TODAY = datetime.date(2026, 5, 25)
CASH3_MMFSN = ['822', '451', '132', '742', '510']
CASH4_MMFSN = ['0822', '1104', '0115', '0812']

SESSION_MAP = {'Midday': 0, 'Evening': 1, 'Night': 2}

# ── Loaders ───────────────────────────────────────────────────────────────────
def load_c3():
    rows = []
    with open(C3_CSV, newline='') as f:
        for r in csv.DictReader(f):
            rows.append({'date': r['draw_date'],
                         'session': r['session'].strip().title(),
                         'num': r['winning_numbers'].strip().zfill(3)})
    return rows

def load_c4():
    rows = []
    with open(C4_CSV, newline='') as f:
        for r in csv.DictReader(f):
            num_key = 'winning_numbers' if 'winning_numbers' in r else 'winning_number'
            rows.append({'date': r['draw_date'],
                         'session': r['session'].strip().title(),
                         'num': str(r[num_key]).strip().zfill(4)})
    return rows

def box_perms(n):
    return list(set(''.join(p) for p in itertools.permutations(n)))

def digit_sum(n):
    return sum(int(d) for d in n)

# ── Core prediction engine ────────────────────────────────────────────────────
def predict(number, draws, game='Cash3'):
    n = number
    perms = box_perms(n)
    box_only = [p for p in perms if p != n]
    all_nums  = [r['num'] for r in draws]
    all_dates = [r['date'] for r in draws]
    sessions  = [r['session'] for r in draws]
    total = len(draws)

    # ── 1. Straight hit history ───────────────────────────────────────────────
    straight_hits = [(i, all_dates[i], sessions[i]) for i, num in enumerate(all_nums) if num == n]

    if straight_hits:
        last_idx, last_date, last_sess = straight_hits[-1]
        gap_draws = total - 1 - last_idx
        last_date_obj = datetime.date.fromisoformat(last_date)
        days_since_straight = (TODAY - last_date_obj).days
        avg_draws_per_hit = total / len(straight_hits)
        gap_ratio = gap_draws / avg_draws_per_hit
    else:
        last_date = 'NEVER'
        last_sess = 'N/A'
        gap_draws = total
        days_since_straight = None
        avg_draws_per_hit = total
        gap_ratio = 1.0

    # ── 2. Box-trigger history ────────────────────────────────────────────────
    box_hits = [(i, all_dates[i], sessions[i], all_nums[i])
                for i, num in enumerate(all_nums) if num in box_only]

    # Measure box-to-straight lags (historical)
    lags_days = []
    lags_draws = []
    for bi, bdate, bsess, bnum in box_hits:
        # Find next straight hit after this box hit
        next_straight = [(si, sddate) for si, sddate, ssess in straight_hits if si > bi]
        if next_straight:
            si, sdate = next_straight[0]
            lag_d = (datetime.date.fromisoformat(sdate) -
                     datetime.date.fromisoformat(bdate)).days
            lag_draws = si - bi
            lags_days.append(lag_d)
            lags_draws.append(lag_draws)

    # Current box trigger
    if box_hits:
        last_box_idx, last_box_date, last_box_sess, last_box_num = box_hits[-1]
        last_box_date_obj = datetime.date.fromisoformat(last_box_date)
        days_since_box = (TODAY - last_box_date_obj).days

        # Is the last box hit after the last straight hit? (i.e., it's an active trigger)
        if straight_hits and last_box_idx < straight_hits[-1][0]:
            trigger_active = False   # box hit was before the last straight — not a fresh trigger
            days_since_box_post_straight = None
        else:
            trigger_active = True
            days_since_box_post_straight = days_since_box
    else:
        days_since_box = None
        last_box_date = 'NONE'
        last_box_num = 'NONE'
        trigger_active = False
        days_since_box_post_straight = None

    # ── 3. Post-trigger prediction window ────────────────────────────────────
    # Use historical lag distribution to predict the window
    if lags_days and len(lags_days) >= 2:
        _s = sorted(lags_days)
        _n = len(_s)
        lag_median  = statistics.median(lags_days)
        lag_p25     = _s[int(_n * 0.25)]
        lag_p75     = _s[int(_n * 0.75)]
        lag_p80     = _s[int(_n * 0.80)]
        lag_max     = max(lags_days)
        lag_min     = min(lags_days)
        lag_mean    = statistics.mean(lags_days)
        lag_stdev   = statistics.stdev(lags_days) if len(lags_days) > 1 else 0
    elif lags_days:
        lag_median = lag_p25 = lag_p75 = lag_p80 = lag_max = lag_min = lag_mean = lags_days[0]
        lag_stdev  = 0
    else:
        lag_median = lag_p25 = lag_p75 = lag_p80 = lag_max = lag_min = lag_mean = lag_stdev = None

    # Session breakdown for straight hits
    sess_counts = collections.Counter(s for _, _, s in straight_hits)
    total_straight = len(straight_hits)
    sess_pct = {s: round(sess_counts.get(s, 0) / max(total_straight, 1) * 100) for s in ['Midday', 'Evening', 'Night']}
    best_sess = max(sess_pct, key=sess_pct.get) if sess_pct else 'Evening'

    # ── 4. Predicted fall window ──────────────────────────────────────────────
    # The IMMINENT / APPROACHING windows are median-proximity triggers:
    # a 7-14 day "PLAY NOW" signal fires when days_since_box is within
    # IMMINENT_DAYS of the historical median lag.
    IMMINENT_DAYS    = 7   # ±7 days around median → "PLAY NOW"
    APPROACHING_DAYS = 21  # 8-21 days from median → "prep window"

    predicted_start        = None   # outer start (lag_min)
    predicted_end          = None   # outer end   (lag_p80)
    predicted_target_start = None   # IQR start   (lag_p25)
    predicted_target_end   = None   # IQR end     (lag_p75)
    predicted_median_date  = None   # single best estimate
    window_status          = 'UNKNOWN'
    days_remaining         = None
    days_to_median         = None

    if trigger_active and days_since_box_post_straight is not None and lag_max is not None:
        box_ref = datetime.date.fromisoformat(last_box_date)
        predicted_start        = box_ref + datetime.timedelta(days=max(1, int(lag_min)))
        predicted_target_start = box_ref + datetime.timedelta(days=int(lag_p25))
        predicted_median_date  = box_ref + datetime.timedelta(days=int(lag_median))
        predicted_target_end   = box_ref + datetime.timedelta(days=int(lag_p75))
        predicted_end          = box_ref + datetime.timedelta(days=int(lag_p80))
        hard_end               = box_ref + datetime.timedelta(days=int(lag_max))

        days_to_median = (predicted_median_date - TODAY).days  # negative = past median

        abs_d = abs(days_to_median)

        if TODAY < predicted_start:
            window_status  = 'PRE-WINDOW'
            days_remaining = (predicted_start - TODAY).days
        elif abs_d <= IMMINENT_DAYS:
            # Within ±7 days of median → PLAY NOW
            window_status  = 'IMMINENT — PLAY NOW'
            days_remaining = max(0, days_to_median)
        elif 0 < days_to_median <= APPROACHING_DAYS:
            # 8-21 days BEFORE median → approaching
            window_status  = 'APPROACHING'
            days_remaining = days_to_median
        elif days_to_median < 0 and abs_d <= APPROACHING_DAYS:
            # 1-21 days AFTER median, still inside IQR → at or past peak
            window_status  = 'AT MEDIAN — PLAY NOW'
            days_remaining = max(0, (predicted_target_end - TODAY).days)
        elif predicted_start <= TODAY < predicted_target_start:
            window_status  = 'EARLY WINDOW'
            days_remaining = (predicted_target_start - TODAY).days
        elif predicted_target_start <= TODAY <= predicted_target_end:
            window_status  = 'PEAK WINDOW'
            days_remaining = (predicted_target_end - TODAY).days
        elif predicted_target_end < TODAY <= predicted_end:
            window_status  = 'EXTENDED WINDOW'
            days_remaining = (predicted_end - TODAY).days
        elif predicted_end < TODAY <= hard_end:
            window_status  = 'LATE WINDOW'
            days_remaining = (hard_end - TODAY).days
        else:
            window_status  = 'WINDOW PASSED'
            days_remaining = 0
    elif not trigger_active:
        window_status = 'NO ACTIVE TRIGGER'

    # ── 5. Convergence score ──────────────────────────────────────────────────
    score = 0
    score_detail = {}

    # Gap overdue (0-25 pts)
    g = min(gap_ratio, 3.0) / 3.0 * 25
    score += g; score_detail['gap_overdue'] = round(g, 1)

    # Box trigger in window (0-35 pts) — highest weight
    if window_status in ('IMMINENT — PLAY NOW', 'AT MEDIAN — PLAY NOW'):
        bt = 35
    elif window_status == 'APPROACHING':
        bt = 28
    elif window_status == 'PEAK WINDOW':
        bt = 20
    elif window_status in ('EXTENDED WINDOW', 'LATE WINDOW'):
        bt = 15
    elif window_status == 'EARLY WINDOW':
        bt = 10
    elif window_status == 'PRE-WINDOW':
        bt = 5
    elif trigger_active:
        bt = 3
    else:
        bt = 0
    score += bt; score_detail['box_trigger'] = bt

    # Session signal (0-15 pts)
    top_pct = sess_pct.get(best_sess, 0)
    ss = (top_pct / 100) * 15
    score += ss; score_detail['session_signal'] = round(ss, 1)

    # Historical lag certainty (0-15 pts) — tighter lag distribution = higher score
    if lag_stdev is not None and lag_mean and lag_mean > 0:
        cv = lag_stdev / lag_mean  # coefficient of variation (lower = more predictable)
        lc = max(0, 1 - cv) * 15
    else:
        lc = 5
    score += lc; score_detail['lag_certainty'] = round(lc, 1)

    # Days-in-window bonus (0-10 pts) — urgency when in PLAY NOW zone
    if window_status in ('IMMINENT — PLAY NOW', 'AT MEDIAN — PLAY NOW'):
        urgency = max(0, 1 - (abs(days_to_median) / IMMINENT_DAYS)) * 10
        score += urgency; score_detail['urgency_bonus'] = round(urgency, 1)
    elif window_status == 'APPROACHING' and days_remaining is not None:
        urgency = max(0, 1 - (days_remaining / APPROACHING_DAYS)) * 5
        score += urgency; score_detail['urgency_bonus'] = round(urgency, 1)
    else:
        score_detail['urgency_bonus'] = 0

    composite = round(min(score, 100), 1)

    # ── 6. Status label ───────────────────────────────────────────────────────
    if composite >= 70:
        status = 'CRITICAL ALERT'
    elif composite >= 50:
        status = 'HIGH ALERT'
    elif composite >= 35:
        status = 'ELEVATED'
    elif composite >= 20:
        status = 'WATCH'
    else:
        status = 'COLD'

    return {
        'number': n, 'game': game, 'composite': composite, 'status': status,
        'straight_hits': len(straight_hits), 'gap_draws': gap_draws,
        'gap_ratio': round(gap_ratio, 2), 'days_since_straight': days_since_straight,
        'last_straight_date': last_date, 'last_straight_session': last_sess,
        'last_box_date': last_box_date, 'last_box_num': last_box_num,
        'days_since_box': days_since_box, 'trigger_active': trigger_active,
        'window_status': window_status, 'days_remaining_in_window': days_remaining,
        'predicted_start': predicted_start, 'predicted_end': predicted_end,
        'predicted_target_start': predicted_target_start,
        'predicted_target_end': predicted_target_end,
        'predicted_median_date': predicted_median_date,
        'days_to_median': days_to_median,
        'best_session': best_sess, 'session_pct': sess_pct,
        'lags_days': lags_days, 'lag_min': lag_min, 'lag_max': lag_max,
        'lag_p25': lag_p25, 'lag_p75': lag_p75,
        'lag_median': lag_median, 'lag_p80': lag_p80, 'lag_mean': round(lag_mean, 1) if lag_mean else None,
        'score_detail': score_detail,
    }

def subscriber_alert(r):
    """Generate the subscriber-facing prediction message."""
    lines = []
    lines.append("=" * 62)
    lines.append(f"  MY BEST ODDS — MMFSN PREDICTION REPORT")
    lines.append(f"  {r['game'].upper()}  Number: {r['number']}    As of: {TODAY}")
    lines.append("=" * 62)

    # Status banner
    if r['status'] == 'CRITICAL ALERT':
        banner = "🔴 CRITICAL ALERT — PLAY NOW"
    elif r['status'] == 'HIGH ALERT':
        banner = "🟠 HIGH ALERT — STRONG PLAY WINDOW"
    elif r['status'] == 'ELEVATED':
        banner = "🟡 ELEVATED — CONDITIONS BUILDING"
    elif r['status'] == 'WATCH':
        banner = "🔵 WATCH — MONITOR CLOSELY"
    else:
        banner = "⚪ COLD — NO ACTION RECOMMENDED"
    lines.append(f"\n  STATUS: {banner}")
    lines.append(f"  CONVERGENCE SCORE: {r['composite']}/100\n")

    # Gap context
    if r['days_since_straight']:
        lines.append(f"  Last exact hit : {r['last_straight_date']} ({r['last_straight_session']}) — {r['days_since_straight']} days ago")
    else:
        lines.append(f"  Last exact hit : NEVER IN RECORDED HISTORY ({r['gap_draws']} draws without a hit)")
    lines.append(f"  Overdue factor : {r['gap_ratio']}× avg frequency ({r['straight_hits']} total hits on record)\n")

    # Box trigger
    if r['trigger_active']:
        lines.append(f"  Box trigger    : {r['last_box_date']} ({r['last_box_num']}) — {r['days_since_box']} days ago")
        lines.append(f"  Window status  : {r['window_status']}")
        if r['predicted_median_date']:
            dtm = r['days_to_median']
            if dtm is not None and dtm > 0:
                lines.append(f"  Median target  : {r['predicted_median_date']}  ({dtm} days away — PLAY NOW ZONE opens ~{r['predicted_median_date'] - datetime.timedelta(days=7)})")
            elif dtm is not None and dtm <= 0:
                lines.append(f"  Median target  : {r['predicted_median_date']}  (passed {abs(dtm)}d ago — AT/PAST PEAK)")
        if r['predicted_target_start'] and r['predicted_target_end']:
            lines.append(f"  IQR zone       : {r['predicted_target_start']} – {r['predicted_target_end']}  (P25–P75)")
        if r['days_remaining_in_window'] is not None and r['days_remaining_in_window'] > 0:
            if r['window_status'] in ('IMMINENT — PLAY NOW', 'AT MEDIAN — PLAY NOW'):
                lines.append(f"  *** PLAY NOW — within {abs(r['days_to_median'])}d of median target ***")
            elif r['window_status'] == 'APPROACHING':
                lines.append(f"  Days to PLAY NOW : {r['days_remaining_in_window']} days until median target")
    else:
        lines.append(f"  Box trigger    : No active trigger (last box: {r['last_box_date']})")

    # Session recommendation
    sp = r['session_pct']
    lines.append(f"\n  Session recommendation:")
    for sess in sorted(sp, key=sp.get, reverse=True):
        bar = '█' * (sp[sess] // 5)
        flag = ' ← PLAY THIS' if sess == r['best_session'] else ''
        lines.append(f"    {sess:8s}  {bar:12s}  {sp[sess]}%{flag}")

    # Historical evidence
    if r['lags_days']:
        lines.append(f"\n  Historical evidence (post-box → exact hit):")
        lines.append(f"    Precedents   : {len(r['lags_days'])} confirmed instances")
        lines.append(f"    Fastest      : {r['lag_min']} days after box hit")
        lines.append(f"    25th pct     : {r['lag_p25']} days")
        lines.append(f"    Typical      : {r['lag_median']} days (median)")
        lines.append(f"    75th pct     : {r['lag_p75']} days")
        lines.append(f"    Max observed : {r['lag_max']} days")

    # The bottom line
    lines.append(f"\n{'─'*62}")
    if r['window_status'] == 'PEAK WINDOW':
        lines.append(f"  BOTTOM LINE: {r['number']} is in its TARGET ZONE right now.")
        lines.append(f"  Based on {len(r['lags_days'])} precedents, 50% of hits fall between")
        lines.append(f"  {r['predicted_target_start']} – {r['predicted_target_end']}.")
        lines.append(f"  Best session: {r['best_session']}.")
    elif r['window_status'] == 'EARLY WINDOW':
        lines.append(f"  BOTTOM LINE: {r['number']} is active — early in the window.")
        lines.append(f"  Target zone opens {r['predicted_target_start']}. Begin play now,")
        lines.append(f"  intensify at the target zone. Best session: {r['best_session']}.")
    elif r['window_status'] in ('EXTENDED WINDOW', 'LATE WINDOW'):
        lines.append(f"  BOTTOM LINE: {r['number']} target zone has passed but number")
        lines.append(f"  remains active through {r['predicted_end']}.")
        lines.append(f"  Continue playing. Best session: {r['best_session']}.")
    elif r['window_status'] == 'PRE-WINDOW':
        lines.append(f"  BOTTOM LINE: {r['number']} has a trigger set. Outer window opens")
        lines.append(f"  {r['predicted_start']}. Target zone: {r['predicted_target_start']} – {r['predicted_target_end']}.")
    elif r['status'] in ('CRITICAL ALERT', 'HIGH ALERT'):
        lines.append(f"  BOTTOM LINE: {r['number']} is significantly overdue.")
        lines.append(f"  No active box trigger, but gap pressure is extreme.")
    else:
        lines.append(f"  BOTTOM LINE: No high-confidence window active for {r['number']}.")
        lines.append(f"  Continue monitoring.")
    lines.append("=" * 62)
    return '\n'.join(lines)

# ── Run all MMFSN numbers ─────────────────────────────────────────────────────
c3_draws = load_c3()
c4_draws = load_c4()

print(f"Data: Cash3={len(c3_draws)} draws through {c3_draws[-1]['date']}")
print(f"      Cash4={len(c4_draws)} draws through {c4_draws[-1]['date']}\n")

all_results = []

for num in CASH3_MMFSN:
    r = predict(num, c3_draws, 'Cash3')
    all_results.append(r)

for num in CASH4_MMFSN:
    r = predict(num, c4_draws, 'Cash4')
    all_results.append(r)

# Sort by composite
all_results.sort(key=lambda x: x['composite'], reverse=True)

# Print subscriber alerts for all
for r in all_results:
    print(subscriber_alert(r))
    print()

# Quick summary table
print("\n" + "="*62)
print("  MASTER RANKINGS — ALL MMFSN NUMBERS")
print("="*62)
print(f"  {'#':<3} {'Game':<7} {'#':^6} {'Score':>6}  {'Status':<16}  {'Window':<22}  {'Best Session'}")
print(f"  {'─'*3} {'─'*7} {'─'*6} {'─'*6}  {'─'*16}  {'─'*30}  {'─'*12}")
for rank, r in enumerate(all_results, 1):
    ws = r['window_status']
    if r['predicted_target_end'] and ws in ('PEAK WINDOW', 'EARLY WINDOW'):
        win_str = f"{ws} → target {r['predicted_target_end']}"
    elif r['predicted_end'] and ws in ('EXTENDED WINDOW', 'LATE WINDOW'):
        win_str = f"{ws} → {r['predicted_end']}"
    else:
        win_str = ws
    print(f"  {rank:<3} {r['game']:<7} {r['number']:^6} {r['composite']:>6.1f}  "
          f"{r['status']:<16}  {win_str:<34}  {r['best_session']}")
print()
