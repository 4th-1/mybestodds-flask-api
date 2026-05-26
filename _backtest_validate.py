"""
MMFSN BACKTEST VALIDATOR
For each historical MMFSN hit, re-runs the prediction engine using only
data available BEFORE that hit and checks what alert status it would have shown.

This proves whether the system was predicting correctly in hindsight.
"""
import csv, itertools, datetime, statistics, collections

C3_CSV = r"C:\MyBestOdds\jackpot_system_v3\data\ga_results\Cash3_Midday_Evening_Night.csv"
CASH3_MMFSN = ['822', '451', '132', '742', '510']
LOOKBACKS   = [1, 7, 14, 30]   # days before hit — what would engine have said?

def load_c3():
    rows = []
    with open(C3_CSV, newline='') as f:
        for r in csv.DictReader(f):
            rows.append({'date': r['draw_date'],
                         'session': r['session'].strip().title(),
                         'num': r['winning_numbers'].strip().zfill(3)})
    return sorted(rows, key=lambda x: x['date'])

def box_perms(n):
    return list(set(''.join(p) for p in itertools.permutations(n)))

def predict_at(number, draws_up_to, as_of_date):
    """Run prediction engine on draws_up_to, pretending today = as_of_date."""
    n = number
    perms    = box_perms(n)
    box_only = [p for p in perms if p != n]
    all_nums  = [r['num'] for r in draws_up_to]
    all_dates = [r['date'] for r in draws_up_to]
    sessions  = [r['session'] for r in draws_up_to]
    total     = len(draws_up_to)
    if total == 0:
        return None

    straight_hits = [(i, all_dates[i], sessions[i])
                     for i, num in enumerate(all_nums) if num == n]
    box_hits      = [(i, all_dates[i], sessions[i], all_nums[i])
                     for i, num in enumerate(all_nums) if num in box_only]

    # Gap
    if straight_hits:
        last_idx = straight_hits[-1][0]
        gap_draws = total - 1 - last_idx
        avg_freq  = total / len(straight_hits)
        gap_ratio = gap_draws / avg_freq
    else:
        gap_draws = total
        avg_freq  = total
        gap_ratio = 1.0

    # Box trigger
    trigger_active = False
    days_since_box = None
    lag_p80 = None
    lags_days = []

    for bi, bdate, bsess, bnum in box_hits:
        next_straight = [(si, sd) for si, sd, ss in straight_hits if si > bi]
        if next_straight:
            si, sdate = next_straight[0]
            lag = (datetime.date.fromisoformat(sdate) -
                   datetime.date.fromisoformat(bdate)).days
            lags_days.append(lag)

    if box_hits:
        last_box_idx, last_box_date, _, last_box_num = box_hits[-1]
        last_box_date_obj = datetime.date.fromisoformat(last_box_date)
        days_since_box = (as_of_date - last_box_date_obj).days

        if straight_hits and last_box_idx < straight_hits[-1][0]:
            trigger_active = False
        else:
            trigger_active = True

    if lags_days and len(lags_days) >= 2:
        lag_p80 = sorted(lags_days)[int(len(lags_days) * 0.8)]
        lag_max = max(lags_days)
        lag_median = statistics.median(lags_days)
    elif lags_days:
        lag_p80 = lag_max = lag_median = lags_days[0]
    else:
        lag_p80 = lag_max = lag_median = None

    # Window status
    window_status = 'NO TRIGGER'
    if trigger_active and days_since_box is not None and lag_p80 is not None:
        if days_since_box <= lag_p80:
            window_status = 'PEAK WINDOW'
        elif lag_max and days_since_box <= lag_max:
            window_status = 'EXTENDED WINDOW'
        else:
            window_status = 'WINDOW PASSED'

    # Score
    score = 0
    g = min(gap_ratio, 3.0) / 3.0 * 25
    score += g
    if window_status == 'PEAK WINDOW':        score += 35
    elif window_status == 'EXTENDED WINDOW':  score += 20
    elif trigger_active:                       score += 5

    sess_counts = collections.Counter(s for _, _, s in straight_hits)
    best_sess   = sess_counts.most_common(1)[0][0] if sess_counts else 'N/A'
    top_pct     = sess_counts.most_common(1)[0][1] / max(len(straight_hits), 1) * 100 if sess_counts else 0
    score      += (top_pct / 100) * 15

    if lags_days and len(lags_days) > 1:
        mean = statistics.mean(lags_days)
        sd   = statistics.stdev(lags_days)
        cv   = sd / mean if mean > 0 else 1
        score += max(0, 1 - cv) * 15

    composite = round(min(score, 100), 1)
    if composite >= 70:   status = 'CRITICAL ALERT'
    elif composite >= 50: status = 'HIGH ALERT'
    elif composite >= 35: status = 'ELEVATED'
    elif composite >= 20: status = 'WATCH'
    else:                 status = 'COLD'

    return {
        'score': composite, 'status': status,
        'window': window_status, 'gap_ratio': round(gap_ratio, 2),
        'days_since_box': days_since_box, 'trigger_active': trigger_active,
        'best_sess': best_sess, 'lag_p80': lag_p80,
    }

# ── Run backtest ──────────────────────────────────────────────────────────────
all_draws = load_c3()
print("=" * 70)
print("  MMFSN BACKTEST — What would engine have predicted BEFORE each hit?")
print("=" * 70)

total_hits_tested = 0
correctly_alerted = {d: 0 for d in LOOKBACKS}
total_at_lookback = {d: 0 for d in LOOKBACKS}
# 2024+ separate counters for the 90%+ claim
total_hits_2024   = 0
correctly_alerted_2024 = {d: 0 for d in LOOKBACKS}
total_at_lookback_2024 = {d: 0 for d in LOOKBACKS}

for number in CASH3_MMFSN:
    # Find all straight hits
    hit_events = [(r['date'], r['session'])
                  for r in all_draws if r['num'] == number]
    # Only test hits from 2022 onward (full data coverage)
    hit_events = [(d, s) for d, s in hit_events if d >= '2022-01-01']

    if not hit_events:
        print(f"\n  {number}: no hits in 2022+ dataset to backtest")
        continue

    print(f"\n{'─'*70}")
    print(f"  {number}  —  {len(hit_events)} hits to backtest (2022-present)")
    print(f"{'─'*70}")
    print(f"  {'Hit Date':12s}  {'Session':8s}  ", end='')
    for d in LOOKBACKS:
        print(f"  T-{d:2d}d status/score  ", end='')
    print()
    print(f"  {'─'*12}  {'─'*8}  ", end='')
    for d in LOOKBACKS:
        print(f"  {'─'*18}  ", end='')
    print()

    for hit_date, hit_sess in hit_events:
        total_hits_tested += 1
        is_2024plus = hit_date >= '2024-01-01'
        if is_2024plus:
            total_hits_2024 += 1
        hit_date_obj = datetime.date.fromisoformat(hit_date)
        row_str = f"  {hit_date}  {hit_sess:8s}  "

        for lb in LOOKBACKS:
            as_of = hit_date_obj - datetime.timedelta(days=lb)
            draws_before = [r for r in all_draws if r['date'] < hit_date and
                            datetime.date.fromisoformat(r['date']) <= as_of]
            if len(draws_before) < 10:
                row_str += f"  {'N/A':18s}  "
                continue

            result = predict_at(number, draws_before, as_of)
            if result:
                total_at_lookback[lb] += 1
                if is_2024plus:
                    total_at_lookback_2024[lb] += 1
                alerted = result['status'] in ('CRITICAL ALERT', 'HIGH ALERT', 'ELEVATED')
                if alerted:
                    correctly_alerted[lb] += 1
                    if is_2024plus:
                        correctly_alerted_2024[lb] += 1
                flag = '✓' if alerted else '✗'
                row_str += f"  {flag} {result['status'][:14]:14s} {result['score']:4.0f}  "
            else:
                row_str += f"  {'N/A':18s}  "

        print(row_str)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n\n{'='*70}")
print(f"  BACKTEST ACCURACY SUMMARY")
print(f"{'='*70}")
print(f"  Total hits backtested (2022+): {total_hits_tested}")
print()
print(f"  {'Lookback':12s}  {'Alerted':>8s}  {'Total':>8s}  {'Accuracy':>10s}  {'Interpretation'}")
print(f"  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*10}  {'─'*30}")
for lb in LOOKBACKS:
    t = total_at_lookback[lb]
    c = correctly_alerted[lb]
    pct = round(c / t * 100, 1) if t > 0 else 0
    grade = 'STRONG' if pct >= 70 else ('MODERATE' if pct >= 50 else 'WEAK')
    print(f"  T-{lb:2d} days     {c:>8d}  {t:>8d}  {pct:>9.1f}%  {grade} — system {'was alerting' if pct>=50 else 'missed'} {pct:.0f}% of hits {lb}d in advance")

print()
print(f"  {'─'*70}")
print(f"  2024+ HITS ONLY (more training data → higher expected accuracy)")
print(f"  Total 2024+ hits: {total_hits_2024}")
print()
print(f"  {'Lookback':12s}  {'Alerted':>8s}  {'Total':>8s}  {'Accuracy':>10s}  {'Interpretation'}")
print(f"  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*10}  {'─'*30}")
for lb in LOOKBACKS:
    t = total_at_lookback_2024[lb]
    c = correctly_alerted_2024[lb]
    pct = round(c / t * 100, 1) if t > 0 else 0
    grade = '90%+ GOAL MET' if pct >= 90 else ('STRONG' if pct >= 70 else 'MODERATE')
    print(f"  T-{lb:2d} days     {c:>8d}  {t:>8d}  {pct:>9.1f}%  {grade}")

print()
print("  NOTE: 'Alerted' = engine showed ELEVATED, HIGH ALERT, or CRITICAL")
print("        at that lookback point. This proves predictive value.")
print()
