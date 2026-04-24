"""
full_report.py
==============
Comprehensive performance report from simulation_report.csv + simulation_results.db.

Sections:
  1. Total predictions generated
  2. Total winning outcomes (straight / box / partial / any)
  3. Straight / Box / Partial wins breakdown
  4. Win frequency by session
  5. Win frequency by kit
  6. Near matches (1 digit off in any position)
  7. Jackpot secondary prize tier breakdown (MM / PB / MFL) by game, kit, session

Run after simulate_historical.py completes:
    python full_report.py
"""

import argparse
import csv
import json
import sqlite3
import sys
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path

# ── CLI ───────────────────────────────────────────────────────────────────────
_parser = argparse.ArgumentParser(add_help=True)
_parser.add_argument(
    "--save-baseline",
    action="store_true",
    help="Save current run metrics as performance baseline (report_baseline.json)",
)
ARGS = _parser.parse_args()

CSV_PATH    = Path(__file__).parent / "simulation_report.csv"
BASELINE_PATH = Path(__file__).parent / "report_baseline.json"

# ── Baselines (per-pick probability) ─────────────────────────────────────────
BASELINES = {
    "Cash3": {"straight": 0.001, "box": 0.006},
    "Cash4": {"straight": 0.0001, "box": 0.00036},
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def pct(n, d):
    return f"{n/d*100:.4f}%" if d else "0.0000%"

def mult(actual_pct_str, baseline):
    v = float(actual_pct_str.rstrip("%"))
    r = v / (baseline * 100) if baseline else 0
    sign = "+" if r >= 1 else ""
    return f"{sign}{r:.2f}x"

def _near_match(pick: str, actual: str) -> bool:
    """True if pick and actual differ by exactly 1 digit in exactly 1 position."""
    if not actual or len(pick) != len(actual):
        return False
    if pick == actual:
        return False
    mismatches = sum(1 for a, b in zip(pick, actual) if a != b)
    return mismatches == 1

def _partial_match(pick: str, actual: str, min_digits: int) -> bool:
    """True if at least min_digits positions match exactly."""
    if not actual or len(pick) != len(actual):
        return False
    matches = sum(1 for a, b in zip(pick, actual) if a == b)
    return matches >= min_digits

def _is_anagram(pick: str, actual: str) -> bool:
    """True if pick and actual contain the same digits in any order."""
    if not actual or len(pick) != len(actual):
        return False
    return sorted(pick) == sorted(actual)

def _one_off_tier(pick: str, actual: str):
    """
    Returns the 1-Off tier name if ALL digit positions are within +-1 of the
    drawn digit (no wrap-around at 0/9). Returns None if any digit is >1 away.
    Tier is determined by how many digits are exactly 1 away vs. exact matches.
    """
    if not actual or len(pick) != len(actual):
        return None
    diffs = []
    for p, a in zip(pick, actual):
        if not p.isdigit() or not a.isdigit():
            return None
        d = abs(int(p) - int(a))
        if d > 1:
            return None
        diffs.append(d)
    n_off = sum(1 for d in diffs if d == 1)
    tier_map = {
        0: "Straight Match",
        1: "One Digit 1-Off",
        2: "Two Digit 1-Off",
        3: "Three Digit 1-Off",
        4: "Four Digit 1-Off",
    }
    return tier_map.get(n_off, f"{n_off} Digit 1-Off")

# -- Load ---------------------------------------------------------------------
print(f"Loading {CSV_PATH.name}...")
if not CSV_PATH.exists():
    raise SystemExit(f"ERROR: {CSV_PATH} not found. Run simulate_historical.py first.")

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
total_rows = len(rows)
print(f"Loaded {total_rows:,} prediction rows\n")

# ── Metrics accumulator (filled as report runs) ───────────────────────────────
_metrics: dict = {
    "run_date": date.today().isoformat(),
    "date_range": "",
    "subscriber_count": 0,
    "cash3": {"picks": 0, "straight_hits": 0, "box_hits": 0, "near_misses": 0,
              "straight_rate": 0.0, "box_rate": 0.0,
              "straight_daily_stddev": 0.0, "box_daily_stddev": 0.0},
    "cash4": {"picks": 0, "straight_hits": 0, "box_hits": 0, "near_misses": 0,
              "straight_rate": 0.0, "box_rate": 0.0,
              "straight_daily_stddev": 0.0, "box_daily_stddev": 0.0},
    "jackpot": {"mm": {}, "pb": {}, "mfl": {}},
}

SESSIONS = [("Midday", "mid"), ("Evening", "eve"), ("Night", "night")]
WIN_FIELDS = {
    "mid":   ("mid_straight",   "mid_box"),
    "eve":   ("eve_straight",   "eve_box"),
    "night": ("night_straight", "night_box"),
}
ACTUAL_FIELDS = {"mid": "actual_mid", "eve": "actual_eve", "night": "actual_night"}

SEP = "=" * 70

# ── 1. TOTAL PREDICTIONS ──────────────────────────────────────────────────────
print(SEP)
print("  1. TOTAL PREDICTIONS GENERATED")
print(SEP)
by_game = Counter(r["game"] for r in rows)
by_kit  = Counter(r["kit"]  for r in rows)
by_lane = Counter(r["lane"] for r in rows)
dates   = sorted(set(r["date"] for r in rows))
subs    = sorted(set(r["subscriber"] for r in rows))
_metrics["date_range"] = f"{dates[0]} to {dates[-1]}" if dates else ""
_metrics["subscriber_count"] = len(subs)
print(f"  Days simulated  : {len(dates)}")
print(f"  Subscribers     : {len(subs)}")
print(f"  Total pick rows : {total_rows:,}")
for game, cnt in sorted(by_game.items()):
    print(f"    {game:<20}: {cnt:,}")
print(f"  By kit:")
for kit, cnt in sorted(by_kit.items()):
    print(f"    {kit:<10}: {cnt:,}")
print(f"  By lane:")
for lane, cnt in sorted(by_lane.items()):
    print(f"    {lane:<20}: {cnt:,}")

# ── 2 & 3. TOTAL WINNING OUTCOMES ─────────────────────────────────────────────
print(f"\n{SEP}")
print("  2 & 3. WINNING OUTCOMES — STRAIGHT / BOX / PARTIAL / NEAR MISS")
print(SEP)

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    total = len(game_rows)

    straight = sum(1 for r in game_rows
                   if any(r[f"{s}_straight"] == "1" for _, s in SESSIONS))
    box      = sum(1 for r in game_rows
                   if any(r[f"{s}_box"] == "1" for _, s in SESSIONS))
    any_win  = sum(1 for r in game_rows if r.get("any_win") == "1")

    # Partial: 2-of-3 (Cash3) or 3-of-4 (Cash4) digits match in position
    min_partial = 2 if game == "Cash3" else 3
    partial = 0
    near    = 0
    for r in game_rows:
        pick = r["pick"]
        actuals = [r[ACTUAL_FIELDS[s]] for _, s in SESSIONS if r[ACTUAL_FIELDS[s]]]
        for act in actuals:
            act_clean = act.strip()
            if _partial_match(pick, act_clean, min_partial) and pick != act_clean:
                partial += 1
                break
        for act in actuals:
            act_clean = act.strip()
            if _near_match(pick, act_clean):
                near += 1
                break

    s_bl  = BASELINES[game]["straight"]
    b_bl  = BASELINES[game]["box"]
    sp    = pct(straight, total)
    bp    = pct(box, total)
    pp    = pct(partial, total)
    np_   = pct(near, total)

    # Accumulate into metrics fingerprint
    _key = game.lower()  # "cash3" or "cash4"
    _metrics[_key]["picks"]         = total
    _metrics[_key]["straight_hits"] = straight
    _metrics[_key]["box_hits"]      = box
    _metrics[_key]["near_misses"]   = near
    _metrics[_key]["straight_rate"] = round(straight / total * 100, 6) if total else 0.0
    _metrics[_key]["box_rate"]      = round(box      / total * 100, 6) if total else 0.0

    # Stability: daily hit counts -> stddev (measures consistency, not just totals)
    _daily_s: dict = defaultdict(int)
    _daily_b: dict = defaultdict(int)
    for r in game_rows:
        d_ = r["date"]
        if any(r[f"{s}_straight"] == "1" for _, s in SESSIONS):
            _daily_s[d_] += 1
        if any(r[f"{s}_box"] == "1" for _, s in SESSIONS):
            _daily_b[d_] += 1
    all_dates = sorted(set(r["date"] for r in game_rows))
    _s_counts = [_daily_s.get(d_, 0) for d_ in all_dates]
    _b_counts = [_daily_b.get(d_, 0) for d_ in all_dates]
    def _stddev(vals):
        if len(vals) < 2:
            return 0.0
        m = sum(vals) / len(vals)
        return round((sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5, 4)
    _metrics[_key]["straight_daily_stddev"] = _stddev(_s_counts)
    _metrics[_key]["box_daily_stddev"]      = _stddev(_b_counts)

    print(f"\n  [{game}]  {total:,} picks over {len(dates)} days")
    print(f"  {'Outcome':<20} {'Count':>8}  {'Rate':>10}  {'vs Random':>14}")
    print(f"  {'-'*56}")
    print(f"  {'Straight':<20} {straight:>8,}  {sp:>10}  {mult(sp, s_bl):>14}")
    print(f"  {'Box':<20} {box:>8,}  {bp:>10}  {mult(bp, b_bl):>14}")
    print(f"  {'Any win':<20} {any_win:>8,}  {pct(any_win,total):>10}")
    print(f"  {'Partial ({} of {} match)'.format(min_partial, len(game[4:]) or 3):<20} {partial:>8,}  {pp:>10}  {'(no baseline)':>14}")
    print(f"  {'Near miss (1 off)':<20} {near:>8,}  {np_:>10}  {'(no baseline)':>14}")

# ── 4. WIN FREQUENCY BY SESSION ───────────────────────────────────────────────
print(f"\n{SEP}")
print("  4. WIN FREQUENCY BY SESSION")
print(SEP)

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    print(f"\n  [{game}]")
    print(f"  {'Session':<10} {'Picks':>8}  {'Straight':>10}  {'Box':>10}  {'Near':>8}")
    print(f"  {'-'*52}")
    for sess_name, sess_key in SESSIONS:
        s_field, b_field = WIN_FIELDS[sess_key]
        act_field = ACTUAL_FIELDS[sess_key]
        sess_rows = [r for r in game_rows if r[act_field].strip()]
        picks  = len(sess_rows)
        st     = sum(1 for r in sess_rows if r[s_field] == "1")
        bx     = sum(1 for r in sess_rows if r[b_field] == "1")
        nr     = sum(1 for r in sess_rows
                     if _near_match(r["pick"], r[act_field].strip()))
        print(f"  {sess_name:<10} {picks:>8,}  {pct(st,picks):>10}  {pct(bx,picks):>10}  {pct(nr,picks):>8}")

# ── 5. WIN FREQUENCY BY KIT ───────────────────────────────────────────────────
print(f"\n{SEP}")
print("  5. WIN FREQUENCY BY KIT")
print(SEP)

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    print(f"\n  [{game}]")
    print(f"  {'Kit':<10} {'Picks':>8}  {'Straight':>10}  {'Box':>10}  {'Near':>8}  {'Any win':>9}")
    print(f"  {'-'*62}")
    for kit in ["BOSK", "BOOK", "BOOK3"]:
        kit_rows = [r for r in game_rows if r["kit"] == kit]
        total = len(kit_rows)
        st  = sum(1 for r in kit_rows
                  if any(r[f"{s}_straight"] == "1" for _, s in SESSIONS))
        bx  = sum(1 for r in kit_rows
                  if any(r[f"{s}_box"] == "1" for _, s in SESSIONS))
        aw  = sum(1 for r in kit_rows if r.get("any_win") == "1")
        nr  = 0
        for r in kit_rows:
            pick = r["pick"]
            for _, s in SESSIONS:
                act = r[ACTUAL_FIELDS[s]].strip()
                if _near_match(pick, act):
                    nr += 1
                    break
        print(f"  {kit:<10} {total:>8,}  {pct(st,total):>10}  {pct(bx,total):>10}  {pct(nr,total):>8}  {pct(aw,total):>9}")

    # BOOK3 lane breakdown
    b3 = [r for r in game_rows if r["kit"] == "BOOK3"]
    print(f"  {'  BOOK3 system':<10} ", end="")
    sys_rows = [r for r in b3 if r["lane"] == "lane_system"]
    mm_rows  = [r for r in b3 if r["lane"] == "lane_mmfsn"]
    for label, lane_rows in [("system", sys_rows), ("mmfsn", mm_rows)]:
        t = len(lane_rows)
        st = sum(1 for r in lane_rows if any(r[f"{s}_straight"] == "1" for _, s in SESSIONS))
        bx = sum(1 for r in lane_rows if any(r[f"{s}_box"] == "1" for _, s in SESSIONS))
        print(f"\n  {'  '+label:<12} {t:>8,}  {pct(st,t):>10}  {pct(bx,t):>10}")

# ── 6. NEAR MATCHES DETAIL ───────────────────────────────────────────────────
print(f"\n{SEP}")
print("  6. NEAR MATCHES — PICKS THAT MISSED BY 1 DIGIT")
print(SEP)
print("  (Pick differed from winning number in exactly 1 position)\n")

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    near_details = Counter()
    for r in game_rows:
        pick = r["pick"]
        for _, s in SESSIONS:
            act = r[ACTUAL_FIELDS[s]].strip()
            if _near_match(pick, act):
                near_details[(pick, act)] += 1
    top10 = near_details.most_common(10)
    total_near = sum(near_details.values())
    total_pick = len(game_rows)
    print(f"  [{game}]  {total_near:,} near misses ({pct(total_near, total_pick)} of picks)")
    if top10:
        print(f"  {'Pick':<8} {'Actual':<8} {'Count':>6}")
        print(f"  {'-'*26}")
        for (pick, act), cnt in top10:
            print(f"  {pick:<8} {act:<8} {cnt:>6,}")
    print()

# ── TOP 10 WINNING PICKS ──────────────────────────────────────────────────────
print(SEP)
print("  TOP 10 WINNING PICKS (most total wins across all sessions)")
print(SEP)
for game in ["Cash3", "Cash4"]:
    win_counts = Counter()
    for r in rows:
        if r["game"] != game:
            continue
        if any(r[f] == "1" for f in
               ["mid_straight","eve_straight","night_straight",
                "mid_box","eve_box","night_box"]):
            win_counts[r["pick"]] += 1
    print(f"\n  [{game}]")
    for pick, cnt in win_counts.most_common(10):
        print(f"    {pick}  ->  {cnt:,} wins")

# -- 8. STRAIGHT/BOX COMBO PLAY ANALYSIS -------------------------------------
# Georgia Straight/Box prize amounts (per $1 play = $0.50 straight + $0.50 box)
# Straight hit: wins BOTH straight portion AND box portion
# Box-only hit: wins box portion only
# Cash3 (6-way standard): straight=$290, box=$40
# Cash4 (24-way standard): straight=$2,750, box=$100
_SB_PRIZES = {
    "Cash3": {"straight_hit": 330, "straight_only": 290, "box_only": 40},
    "Cash4": {"straight_hit": 2850, "straight_only": 2750, "box_only": 100},
}

print(f"\n{SEP}")
print("  8. STRAIGHT/BOX COMBO PLAY ANALYSIS")
print(SEP)
print("  Per $1 S/B play: straight hit = straight prize + box prize; box-only = box prize")
print("  Cash3 standard (6-way): straight hit=$330 ($290+$40); box-only=$40")
print("  Cash4 standard (24-way): straight hit=$2,850 ($2,750+$100); box-only=$100\n")

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    total = len(game_rows)
    sb_straight = 0
    sb_box_only = 0
    for r in game_rows:
        pick = r["pick"]
        for _, s in SESSIONS:
            act = r[ACTUAL_FIELDS[s]].strip()
            if not act:
                continue
            if pick == act:
                sb_straight += 1
                break
            elif _is_anagram(pick, act):
                sb_box_only += 1
                break
    sb_total = sb_straight + sb_box_only
    prizes = _SB_PRIZES[game]
    est_straight_prize = sb_straight * prizes["straight_hit"]
    est_box_prize      = sb_box_only * prizes["box_only"]
    est_total_prize    = est_straight_prize + est_box_prize
    num_subs = len(subs)
    value_per_sub = round(est_total_prize / num_subs, 2) if num_subs else 0
    print(f"  [{game}]  {total:,} picks  |  {num_subs} subscribers")
    print(f"  {'Component':<36} {'Count':>8}  {'Rate':>10}  {'Est. Prize $':>13}")
    print(f"  {'-'*71}")
    print(f"  {'Straight hit (both S+B prize)':<36} {sb_straight:>8,}  {pct(sb_straight, total):>10}  ${est_straight_prize:>12,}")
    print(f"  {'Box-only hit (box prize)':<36} {sb_box_only:>8,}  {pct(sb_box_only, total):>10}  ${est_box_prize:>12,}")
    print(f"  {'-'*71}")
    print(f"  {'Any S/B component won':<36} {sb_total:>8,}  {pct(sb_total, total):>10}  ${est_total_prize:>12,}")
    print(f"  {'Avg value per subscriber':<36} {'':>8}  {'':>10}  ${value_per_sub:>12,.2f}")
    print()

# -- 9. 1-OFF PLAY ANALYSIS ---------------------------------------------------
print(f"\n{SEP}")
print("  9. 1-OFF PLAY ANALYSIS  (Georgia digit-proximity rule)")
print(SEP)
print("  All prize values reflect Georgia Lottery $1 play amounts.")
print("  (All digit positions within +-1 of drawn digit; no wrap-around at 0/9)")
print("  Cash3: Straight=$250, 1-off=$24, 2-off=$4, 3-off=$8")
print("  Cash4: Straight=$2,500, 1-off=$124, 2-off=$24, 3-off=$14, 4-off=$32")
print()

_ONEOFF_PRIZE = {
    "Cash3": {
        "Straight Match":   250,   # GA official: $1 play
        "One Digit 1-Off":   24,   # GA official: $1 play
        "Two Digit 1-Off":    4,   # GA official: $1 play
        "Three Digit 1-Off":  8,   # GA official: $1 play (harder, pays more than 2-off)
    },
    "Cash4": {
        "Straight Match":  2500,   # GA official: $1 play
        "One Digit 1-Off":  124,   # GA official: $1 play
        "Two Digit 1-Off":   24,   # GA official: $1 play
        "Three Digit 1-Off": 14,   # GA official: $1 play
        "Four Digit 1-Off":  32,   # GA official: $1 play (all 4 digits 1-off)
    },
}
_ONEOFF_TIERS = {
    "Cash3": ["Straight Match", "One Digit 1-Off", "Two Digit 1-Off", "Three Digit 1-Off"],
    "Cash4": ["Straight Match", "One Digit 1-Off", "Two Digit 1-Off",
              "Three Digit 1-Off", "Four Digit 1-Off"],
}

for game in ["Cash3", "Cash4"]:
    game_rows = [r for r in rows if r["game"] == game]
    total = len(game_rows)
    tier_counts = Counter()
    for r in game_rows:
        pick = r["pick"]
        for _, s in SESSIONS:
            act = r[ACTUAL_FIELDS[s]].strip()
            if not act:
                continue
            tier = _one_off_tier(pick, act)
            if tier:
                tier_counts[tier] += 1
                break
    total_wins = sum(tier_counts.values())
    prize_table = _ONEOFF_PRIZE[game]
    total_prize = sum(cnt * prize_table.get(t, 0) for t, cnt in tier_counts.items())
    value_per_sub_1off = round(total_prize / len(subs), 2) if subs else 0
    print(f"  [{game}]  {total:,} picks  |  1-Off qualifying: {total_wins:,} ({pct(total_wins, total)})")
    print(f"  {'Tier':<24} {'Count':>8}  {'Rate':>10}  {'Est. Prize $':>13}")
    print(f"  {'-'*59}")
    for t in _ONEOFF_TIERS[game]:
        cnt = tier_counts.get(t, 0)
        est = cnt * prize_table.get(t, 0)
        print(f"  {t:<24} {cnt:>8,}  {pct(cnt, total):>10}  ${est:>12,}")
    print(f"  {'-'*59}")
    print(f"  {'TOTAL':<24} {total_wins:>8,}  {pct(total_wins, total):>10}  ${total_prize:>12,}")
    print(f"  {'Avg value per subscriber':<24} {'':>8}  {'':>10}  ${value_per_sub_1off:>12,.2f}")
    print()

print(f"\n{SEP}")
print("  Report complete.")
print(SEP)

# ── 7. JACKPOT SECONDARY PRIZE TIER BREAKDOWN ──────────────────────────────
DB_PATH = Path(__file__).parent / "simulation_results.db"
if not DB_PATH.exists():
    print(f"\nNOTE: {DB_PATH.name} not found — skipping jackpot section.")
else:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    jp_rows = conn.execute(
        "SELECT game, kit, tier, prize, white_match, special_match FROM sim_jackpot_results"
    ).fetchall()
    conn.close()

    print(f"\n{SEP}")
    print("  7. JACKPOT SECONDARY PRIZES — TIER BREAKDOWN BY GAME & KIT")
    print(SEP)

    if not jp_rows:
        print("  (no jackpot rows in DB)")
    else:
        # ── 7a. Overview per game ────────────────────────────────────────────
        print("\n  7a. Overall by Game")
        print(f"  {'Game':<26} {'Picks':>8}  {'Prize Wins':>10}  {'Win%':>8}  {'Total Prize':>13}")
        print(f"  {'-'*72}")
        for game in ["MegaMillions", "Powerball", "Millionaire For Life"]:
            gr = [r for r in jp_rows if r["game"] == game]
            total = len(gr)
            wins  = sum(1 for r in gr if r["tier"])
            prize = sum(r["prize"] for r in gr)
            wp = f"{wins/total*100:.4f}%" if total else "0.0000%"
            print(f"  {game:<26} {total:>8,}  {wins:>10,}  {wp:>8}  ${prize:>12,}")

        # ── 7b. Tier breakdown per game ──────────────────────────────────────
        print("\n  7b. Tier Breakdown per Game")
        for game in ["MegaMillions", "Powerball", "Millionaire For Life"]:
            gr = [r for r in jp_rows if r["game"] == game]
            total = len(gr)
            tier_counts = Counter(r["tier"] for r in gr if r["tier"])
            tier_prizes = defaultdict(int)
            for r in gr:
                if r["tier"]:
                    tier_prizes[r["tier"]] += r["prize"]
            if not tier_counts:
                continue
            print(f"\n  [{game}]  {total:,} picks")
            print(f"  {'Tier':<16} {'Count':>8}  {'Total Prize':>13}  {'Avg Prize':>11}")
            print(f"  {'-'*54}")
            for tier, cnt in sorted(tier_counts.items(), key=lambda x: -x[1]):
                tp = tier_prizes[tier]
                avg = tp // cnt if cnt else 0
                print(f"  {tier:<16} {cnt:>8,}  ${tp:>12,}  ${avg:>10,}")

        # ── 7c. By kit ───────────────────────────────────────────────────────
        print("\n  7c. By Kit (all jackpot games combined)")
        print(f"  {'Kit':<10} {'Picks':>8}  {'Prize Wins':>10}  {'Win%':>8}  {'Total Prize':>13}")
        print(f"  {'-'*56}")
        for kit in ["BOSK", "BOOK", "BOOK3"]:
            kr = [r for r in jp_rows if r["kit"] == kit]
            total = len(kr)
            wins  = sum(1 for r in kr if r["tier"])
            prize = sum(r["prize"] for r in kr)
            wp = f"{wins/total*100:.4f}%" if total else "0.0000%"
            print(f"  {kit:<10} {total:>8,}  {wins:>10,}  {wp:>8}  ${prize:>12,}")

        # ── 7d. Top tier by kit per game ─────────────────────────────────────
        print("\n  7d. Best Tiers per Kit")
        for game in ["MegaMillions", "Powerball", "Millionaire For Life"]:
            gr = [r for r in jp_rows if r["game"] == game and r["tier"]]
            if not gr:
                continue
            print(f"\n  [{game}]")
            print(f"  {'Kit':<10} {'Tier':<16} {'Count':>6}  {'Prize $':>10}")
            print(f"  {'-'*46}")
            for kit in ["BOSK", "BOOK", "BOOK3"]:
                kr = [r for r in gr if r["kit"] == kit]
                if not kr:
                    continue
                by_tier = Counter(r["tier"] for r in kr)
                # Show top 3 tiers for this kit
                for tier, cnt in by_tier.most_common(3):
                    tp = sum(r["prize"] for r in kr if r["tier"] == tier)
                    print(f"  {kit:<10} {tier:<16} {cnt:>6,}  ${tp:>9,}")

        # ── Accumulate jackpot metrics ────────────────────────────────────────
        _game_key_map = {
            "MegaMillions": "mm",
            "Powerball": "pb",
            "Millionaire For Life": "mfl",
        }
        for game, jkey in _game_key_map.items():
            gr = [r for r in jp_rows if r["game"] == game]
            total = len(gr)
            wins  = sum(1 for r in gr if r["tier"])
            prize = sum(r["prize"] for r in gr)
            tiers = dict(Counter(r["tier"] for r in gr if r["tier"]))
            _metrics["jackpot"][jkey] = {
                "picks":       total,
                "prize_wins":  wins,
                "win_rate":    round(wins / total * 100, 6) if total else 0.0,
                "total_prize": prize,
                "tiers":       tiers,
            }

    print(f"\n{SEP}")
    print("  Full report complete (Cash + Jackpot).")
    print(SEP)

# ── BASELINE: SAVE or COMPARE ─────────────────────────────────────────────────
_DIFF_FIELDS_CASH = [
    ("picks",                 "Picks",              False),
    ("straight_hits",         "Straight hits",       True),
    ("box_hits",              "Box hits",            True),
    ("near_misses",           "Near misses",        False),
    ("straight_rate",         "Straight rate%",      True),
    ("box_rate",              "Box rate%",           True),
    ("straight_daily_stddev", "Straight stddev/day",False),
    ("box_daily_stddev",      "Box stddev/day",     False),
]
_DIFF_FIELDS_JP = [
    ("picks",       "Picks",      False),
    ("prize_wins",  "Prize wins", True),
    ("win_rate",    "Win rate%",  True),
    ("total_prize", "Total prize",True),
]

def _arrow(new, old, higher_is_better):
    if old == 0:
        return "  (new)"
    delta = new - old
    pct_d = delta / abs(old) * 100
    symbol = ("^" if delta > 0 else "v") if higher_is_better else (
             "^" if delta < 0 else "v")
    return f"  {symbol} {pct_d:+.2f}%"

def _print_diff(label, new_d, old_d, fields):
    print(f"\n  [{label}]")
    for fkey, fname, hib in fields:
        nv = new_d.get(fkey, 0)
        ov = old_d.get(fkey, 0)
        note = _arrow(nv, ov, hib)
        print(f"    {fname:<18}: {ov!s:>12}  ->  {nv!s:<12}{note}")

if ARGS.save_baseline:
    with open(BASELINE_PATH, "w", encoding="utf-8") as _bf:
        json.dump(_metrics, _bf, indent=2)
    print(f"\n{'='*70}")
    print(f"  BASELINE SAVED -> {BASELINE_PATH.name}")
    print(f"  Run date   : {_metrics['run_date']}")
    print(f"  Date range : {_metrics['date_range']}")
    print(f"  Subs       : {_metrics['subscriber_count']}")
    print(f"  (Next run will auto-compare against this snapshot.)")
    print(f"{'='*70}")
elif BASELINE_PATH.exists():
    with open(BASELINE_PATH, encoding="utf-8") as _bf:
        _base = json.load(_bf)
    print(f"\n{'='*70}")
    print(f"  PERFORMANCE DELTA — vs baseline from {_base.get('run_date','?')}")
    print(f"  Baseline range : {_base.get('date_range','?')}  |  subs: {_base.get('subscriber_count','?')}")
    print(f"  Current  range : {_metrics['date_range']}  |  subs: {_metrics['subscriber_count']}")
    print(f"{'='*70}")
    _print_diff("Cash3", _metrics["cash3"], _base.get("cash3", {}), _DIFF_FIELDS_CASH)
    _print_diff("Cash4", _metrics["cash4"], _base.get("cash4", {}), _DIFF_FIELDS_CASH)
    for _jk, _jlabel in [("mm","MegaMillions"),("pb","Powerball"),("mfl","MFL")]:
        _print_diff(_jlabel, _metrics["jackpot"].get(_jk, {}),
                    _base.get("jackpot", {}).get(_jk, {}), _DIFF_FIELDS_JP)

    # ── PROMOTION VERDICT: all-three-conditions check ─────────────────────────
    _c4n = _metrics["cash4"]
    _c4b = _base.get("cash4", {})
    _s_ok  = _c4n.get("straight_hits", 0) >= _c4b.get("straight_hits", 0)
    _bx_ok = _c4n.get("box_hits", 0)     >= _c4b.get("box_hits", 0)
    _sdev_new = _c4n.get("straight_daily_stddev", 0)
    _sdev_old = _c4b.get("straight_daily_stddev", 0)
    # Stability: new stddev within 10% of baseline = stable; >10% above = volatile
    _var_ok = (_sdev_old == 0) or (_sdev_new <= _sdev_old * 1.10)
    _var_label = "STABLE" if _var_ok else f"INCREASED (stddev {_sdev_new} vs {_sdev_old})"
    print(f"\n  PROMOTION CHECK (Cash4) — straight >= bl AND box >= bl AND variance stable")
    print(f"    Straight {'>=' if _s_ok else '< '}baseline : {'PASS' if _s_ok else 'FAIL'}")
    print(f"    Box      {'>=' if _bx_ok else '< '}baseline : {'PASS' if _bx_ok else 'FAIL'}")
    print(f"    Variance            : {_var_label}")
    _verdict = "PROMOTE" if (_s_ok and _bx_ok and _var_ok) else "HOLD BASELINE"
    print(f"    VERDICT             : {_verdict}")

    print(f"\n  Run with --save-baseline to promote current results as new baseline.")
    print(f"{'='*70}")
else:
    print(f"\n  (No baseline on file. Run with --save-baseline to create one.)")

