"""
simulate_historical.py
======================
Walk-forward historical backtest: Jan 1 – Mar 31, 2026
- Calls generate_picks_v3() directly (no HTTP)
- For each day, only uses draw data PRIOR to that date (no future leakage)
- Detects wins (straight + box) against actual Cash3/Cash4 results
- Writes to SQLite DB + CSV report

Usage:
    python simulate_historical.py [--days 91] [--subs 1000] [--start 2026-01-01]
"""

import sys
import os
import csv
import json
import sqlite3
import argparse
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
JACKPOT_ROOT = ROOT / "jackpot_system_v3"
sys.path.insert(0, str(JACKPOT_ROOT))

from core.pick_engine_v3 import generate_picks_v3
from core.v3_7.play_type_resolver_v3_7 import resolve_play_type

# ── Config ───────────────────────────────────────────────────────────────────
# GA actuals - ordered oldest-first; loaders merge and deduplicate
CASH3_SOURCES = [
    ROOT / "historical_data" / "ga_results" / "Cash3_Master_2025.csv",
    ROOT / "historical_data" / "ga_results" / "2026" / "Cash3.csv",
]
CASH4_SOURCES = [
    ROOT / "historical_data" / "ga_results" / "Cash4_Master_2025.csv",
    ROOT / "historical_data" / "ga_results" / "2026" / "Cash4.csv",
]
# Keep single-path constants for jackpot (no 2025 master available)
MM_CSV    = ROOT / "historical_data" / "jackpot_results" / "2026" / "MegaMillions.csv"
PB_CSV    = ROOT / "historical_data" / "jackpot_results" / "2026" / "Powerball.csv"
MFL_CSV   = ROOT / "historical_data" / "jackpot_results" / "2026" / "Millionaire_For_Life.csv"
DB_PATH   = ROOT / "simulation_results.db"
CSV_OUT   = ROOT / "simulation_report.csv"

SESSIONS  = ["MIDDAY", "EVENING", "NIGHT"]

# Prize tables: (white_match, special_match) -> (tier_label, prize_dollars)
# 0 prize = jackpot (varies; stored as tier label only)
_MM_PRIZES = {
    (5, 1): ("JACKPOT",   0),       (5, 0): ("5+0",   1_000_000),
    (4, 1): ("4+MB",  10_000),      (4, 0): ("4+0",        500),
    (3, 1): ("3+MB",     200),      (3, 0): ("3+0",         10),
    (2, 1): ("2+MB",      10),      (1, 1): ("1+MB",          4),
    (0, 1): ("0+MB",       2),
}
_PB_PRIZES = {
    (5, 1): ("JACKPOT",   0),       (5, 0): ("5+0",   1_000_000),
    (4, 1): ("4+PB",  50_000),      (4, 0): ("4+0",        100),
    (3, 1): ("3+PB",     100),      (3, 0): ("3+0",          7),
    (2, 1): ("2+PB",       7),      (1, 1): ("1+PB",          4),
    (0, 1): ("0+PB",       4),
}
_MFL_PRIZES = {
    (5, 1): ("JACKPOT",   0),       (5, 0): ("5+0",    25_000),
    (4, 1): ("4+MB",   2_500),      (4, 0): ("4+0",       500),
    (3, 1): ("3+MB",      50),      (3, 0): ("3+0",        10),
    (2, 1): ("2+MB",       5),      (1, 1): ("1+MB",         2),
    (0, 1): ("0+MB",       1),
}
JACKPOT_PRIZE_TABLES = {
    "MegaMillions":       _MM_PRIZES,
    "Powerball":          _PB_PRIZES,
    "Millionaire For Life": _MFL_PRIZES,
}

# ── Load actual draw results ──────────────────────────────────────────────────
def _norm_row(row: dict):
    """Normalize a CSV row from either the 2025-master or 2026 format.
    2025 master: draw_date(ISO), game, session, digits
    2026 files : date(M/D/Y),         session, number
    Returns (date_obj, session_upper, number_str).
    """
    if "draw_date" in row:
        d = datetime.strptime(row["draw_date"], "%Y-%m-%d").date()
        return d, row["session"].upper(), row["digits"].strip()
    else:
        d = datetime.strptime(row["date"], "%m/%d/%Y").date()
        return d, row["session"].upper(), row["number"].strip()


def load_actuals(csv_path: Path) -> dict:
    """Returns {(date_obj, session): number_str} -- single file (legacy)."""
    actuals = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d, session, number = _norm_row(row)
                actuals[(d, session)] = number
            except (ValueError, KeyError):
                continue
    return actuals


def load_actuals_multi(csv_paths: list) -> dict:
    """Returns {(date_obj, session): number_str} merged from multiple files.
    Later files in the list win on duplicate (date, session) keys.
    """
    actuals = {}
    for csv_path in csv_paths:
        if not Path(csv_path).exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d, session, number = _norm_row(row)
                    actuals[(d, session)] = number
                except (ValueError, KeyError):
                    continue
    return actuals


def load_history_for_engine(csv_path: Path, before_date) -> list:
    """Return rows with draw_date < before_date in engine format -- single file (legacy)."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d, session, number = _norm_row(row)
            except (ValueError, KeyError):
                continue
            if d < before_date:
                rows.append({
                    "draw_date": d.strftime("%m/%d/%Y"),
                    "winning_numbers": number,
                    "session": session,
                })
    return rows


def load_history_for_engine_multi(csv_paths: list, before_date) -> list:
    """Return rows with draw_date < before_date in engine format, merged from
    multiple files and deduplicated by (date, session)."""
    seen = set()
    rows = []
    for csv_path in csv_paths:
        if not Path(csv_path).exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d, session, number = _norm_row(row)
                except (ValueError, KeyError):
                    continue
                if d < before_date:
                    key = (d, session)
                    if key not in seen:
                        seen.add(key)
                        rows.append({
                            "draw_date": d.strftime("%m/%d/%Y"),
                            "winning_numbers": number,
                            "session": session,
                        })
    return rows


def preload_all_history(csv_paths: list) -> list:
    """Load ALL rows from multiple sources into memory once, deduplicated.
    Returns sorted list of engine-format dicts with an extra 'date_obj' key
    for fast date filtering inside the walk-forward loop.
    """
    seen = set()
    rows = []
    for csv_path in csv_paths:
        if not Path(csv_path).exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    d, session, number = _norm_row(row)
                except (ValueError, KeyError):
                    continue
                key = (d, session)
                if key not in seen:
                    seen.add(key)
                    rows.append({
                        "date_obj":       d,
                        "draw_date":      d.strftime("%m/%d/%Y"),
                        "winning_numbers": number,
                        "session":        session,
                    })
    rows.sort(key=lambda r: (r["date_obj"], r["session"]))
    return rows


def filter_history_before(all_rows: list, before_date) -> list:
    """Fast in-memory filter: return engine-format rows with date < before_date."""
    return [
        {"draw_date": r["draw_date"], "winning_numbers": r["winning_numbers"], "session": r["session"]}
        for r in all_rows if r["date_obj"] < before_date
    ]


# ── Build ga_data dict from raw rows ─────────────────────────────────────────
def build_ga_data(cash3_rows: list, cash4_rows: list) -> dict:
    ga = {
        "cash3_mid": [], "cash3_eve": [], "cash3_night": [],
        "cash4_mid": [], "cash4_eve": [], "cash4_night": [],
    }
    sess_map = {"MIDDAY": "_mid", "EVENING": "_eve", "NIGHT": "_night"}
    for row in cash3_rows:
        suffix = sess_map.get(row["session"], "")
        if suffix:
            ga[f"cash3{suffix}"].append(row)
    for row in cash4_rows:
        suffix = sess_map.get(row["session"], "")
        if suffix:
            ga[f"cash4{suffix}"].append(row)
    return ga


# ── Win detection ─────────────────────────────────────────────────────────────
def is_straight_win(pick: str, actual: str) -> bool:
    return pick.strip().zfill(len(actual)) == actual.strip().zfill(len(actual))


def is_box_win(pick: str, actual: str) -> bool:
    if len(pick) != len(actual):
        return False
    return sorted(pick) == sorted(actual)


# ── Play-type resolver helpers ───────────────────────────────────────────────
def build_ctx_for_sub(kit: str, lane: str) -> dict:
    """Map subscriber kit + pick lane -> context flags for play_type_resolver."""
    if kit == "BOSK":
        return {"straight_core": True, "high_confidence": True}
    if kit == "BOOK":
        return {"straight_core": True, "box_safety": True}
    # BOOK3 — mmfsn lane gets 1-off focus; system lane gets straight/box
    if "mmfsn" in (lane or "").lower():
        return {"one_off_focus": True}
    return {"straight_core": True, "box_safety": True}


def is_one_off_win(pick: str, actual: str) -> bool:
    """True if ALL digit positions differ by <=1 (covers all 1-OFF prize tiers).
    Includes exact match (Straight Match tier when playing 1-OFF)."""
    if not actual or len(pick) != len(actual):
        return False
    for p, a in zip(pick, actual):
        if not p.isdigit() or not a.isdigit():
            return False
        if abs(int(p) - int(a)) > 1:
            return False
    return True


# ── Jackpot helpers ───────────────────────────────────────────────────────────
def _parse_jackpot_line(s: str):
    """Parse '06 13 34 43 52 + 04' -> (frozenset of ints, int)."""
    parts = s.split("+")
    whites = frozenset(int(x) for x in parts[0].split())
    special = int(parts[1].strip())
    return whites, special


def load_jackpot_actuals(csv_path: Path) -> dict:
    """Returns {date_obj: (frozenset_whites, special_int)}"""
    actuals = {}
    if not csv_path.exists():
        return actuals
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.strptime(row["date"].strip(), "%m/%d/%Y").date()
                whites, special = _parse_jackpot_line(row["numbers"])
                actuals[d] = (whites, special)
            except (ValueError, KeyError):
                continue
    return actuals


def score_jackpot_pick(pick_str: str, actual_whites: frozenset, actual_special: int,
                       prize_table: dict) -> tuple:
    """Returns (white_match, special_match, tier_label, prize_dollars)."""
    try:
        pick_whites, pick_special = _parse_jackpot_line(pick_str)
    except Exception:
        return (0, 0, "", 0)
    wm = len(pick_whites & actual_whites)
    sm = int(pick_special == actual_special)
    tier, prize = prize_table.get((wm, sm), ("", 0))
    return wm, sm, tier, prize


# ── DB setup ──────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sim_date    TEXT,
            subscriber  TEXT,
            kit         TEXT,
            game        TEXT,
            lane        TEXT,
            pick        TEXT,
            actual_mid  TEXT,
            actual_eve  TEXT,
            actual_night TEXT,
            mid_straight  INTEGER DEFAULT 0,
            mid_box       INTEGER DEFAULT 0,
            eve_straight  INTEGER DEFAULT 0,
            eve_box       INTEGER DEFAULT 0,
            night_straight INTEGER DEFAULT 0,
            night_box      INTEGER DEFAULT 0,
            any_win       INTEGER DEFAULT 0,
            play_type     TEXT    DEFAULT 'STRAIGHT/BOX',
            confidence_score REAL   DEFAULT 0.0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_jackpot_results (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sim_date      TEXT,
            subscriber    TEXT,
            kit           TEXT,
            game          TEXT,
            pick          TEXT,
            actual        TEXT,
            white_match   INTEGER DEFAULT 0,
            special_match INTEGER DEFAULT 0,
            tier          TEXT    DEFAULT '',
            prize         INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_summary (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            run_ts         TEXT,
            total_picks    INTEGER,
            total_wins_straight INTEGER,
            total_wins_box INTEGER,
            cash3_straight_pct REAL,
            cash3_box_pct  REAL,
            cash4_straight_pct REAL,
            cash4_box_pct  REAL
        )
    """)
    conn.commit()


# ── Subscriber profiles ───────────────────────────────────────────────────────
def _seeded_picks(seed: int, length: int, count: int) -> list:
    """Generate `count` unique lottery numbers of `length` digits, seeded deterministically."""
    rng = random.Random(seed)
    picks = set()
    attempts = 0
    while len(picks) < count and attempts < 1000:
        n = "".join(str(rng.randint(0, 9)) for _ in range(length))
        picks.add(n)
        attempts += 1
    return list(picks)[:count]


def generate_subscribers(n: int) -> list:
    """
    Generate n subscriber profiles split equally across three kits:

    - BOSK  (Standard)   : system lane only
    - BOOK  (Personalized): system lane only (natal engine not yet in sim)
    - BOOK3 (Precision)  : system + MMFSN personal lane

    1/3 of subs per kit (last group absorbs remainder).
    """
    import string
    mmfsn_dir = JACKPOT_ROOT / "data" / "mmfsn_profiles"
    mmfsn_dir.mkdir(parents=True, exist_ok=True)

    letters = string.ascii_uppercase
    initials_pool = [a + b + c
                     for a in letters
                     for b in letters
                     for c in letters]  # 17,576 unique 3-letter combos

    kit_cycle = ["BOSK", "BOOK", "BOOK3"]

    subs = []
    for i in range(n):
        initials = initials_pool[i % len(initials_pool)]
        kit = kit_cycle[i % 3]

        if kit == "BOOK3":
            # Write synthetic MMFSN profile (skip if real profile already exists)
            profile_path = mmfsn_dir / f"{initials}_mmfsn.json"
            if not profile_path.exists():
                seed = hash(initials) & 0xFFFFFFFF
                profile = {
                    "initials": initials,
                    "mmfsn_numbers": {
                        "Cash3": _seeded_picks(seed,        3, 5),
                        "Cash4": _seeded_picks(seed + 9999, 4, 3),
                    },
                    "weight": 0.60,
                    "notes": "Synthetic profile — auto-generated for simulation",
                }
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2)

        subs.append({
            "subscriber_id": f"SIM_{i+1:04d}",
            "initials": initials,
            "kit": kit,
            "games": ["Cash3", "Cash4"],
        })

    from collections import Counter
    kit_counts = Counter(s["kit"] for s in subs)
    print(f"  Subscribers: {n} total - "
          f"BOSK={kit_counts['BOSK']} (system only), "
          f"BOOK={kit_counts['BOOK']} (system only), "
          f"BOOK3={kit_counts['BOOK3']} (MMFSN+system)")
    return subs


# ── Main simulation ───────────────────────────────────────────────────────────
def run_simulation(start_date: datetime, num_days: int, num_subs: int):
    print(f"\n=== Historical Simulation ===")
    print(f"  Period : {start_date.date()} + {num_days} days")
    print(f"  Subs   : {num_subs}")
    print(f"  Engine : generate_picks_v3() (direct call, no HTTP)")
    print()

    # Load all actual results up front (combined 2025 + 2026)
    cash3_actuals = load_actuals_multi(CASH3_SOURCES)
    cash4_actuals = load_actuals_multi(CASH4_SOURCES)
    print(f"  Cash3 actuals: {len(cash3_actuals)} draw slots loaded")
    print(f"  Cash4 actuals: {len(cash4_actuals)} draw slots loaded")

    # Preload ALL history into memory once — filtered cheaply per day (no per-day file I/O)
    all_cash3_hist = preload_all_history(CASH3_SOURCES)
    all_cash4_hist = preload_all_history(CASH4_SOURCES)
    print(f"  Engine history preloaded: Cash3={len(all_cash3_hist)} rows, Cash4={len(all_cash4_hist)} rows")

    mm_actuals  = load_jackpot_actuals(MM_CSV)
    pb_actuals  = load_jackpot_actuals(PB_CSV)
    mfl_actuals = load_jackpot_actuals(MFL_CSV)
    jackpot_actuals = {
        "MegaMillions":         mm_actuals,
        "Powerball":            pb_actuals,
        "Millionaire For Life": mfl_actuals,
    }
    print(f"  Jackpot actuals loaded: MM={len(mm_actuals)} draws, "
          f"PB={len(pb_actuals)} draws, MFL={len(mfl_actuals)} draws")

    # Subscriber pool
    subscribers = generate_subscribers(num_subs)

    # DB
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    # CSV report writer
    csv_file = open(CSV_OUT, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow([
        "date", "subscriber", "kit", "game", "lane", "pick",
        "actual_mid", "actual_eve", "actual_night",
        "mid_straight", "mid_box", "eve_straight", "eve_box",
        "night_straight", "night_box", "any_win", "play_type", "confidence_score"
    ])

    # Counters for summary
    stats = defaultdict(lambda: {"picks": 0, "straight": 0, "box": 0, "one_off": 0})
    pt_stats = defaultdict(int)  # play_type -> win count
    jp_stats = defaultdict(lambda: {"picks": 0, "wins": 0, "prize_total": 0, "tiers": defaultdict(int)})

    # Walk-forward loop
    for day_offset in range(num_days):
        sim_date = (start_date + timedelta(days=day_offset)).date()
        date_str  = sim_date.strftime("%Y-%m-%d")

        # Load only history BEFORE this date (no future leakage)
        # Fast in-memory filter from preloaded all-history lists
        cash3_hist = filter_history_before(all_cash3_hist, sim_date)
        cash4_hist = filter_history_before(all_cash4_hist, sim_date)
        ga_data    = build_ga_data(cash3_hist, cash4_hist)

        # Actuals for this date
        actuals_today = {
            "Cash3": {s: cash3_actuals.get((sim_date, s), "") for s in SESSIONS},
            "Cash4": {s: cash4_actuals.get((sim_date, s), "") for s in SESSIONS},
        }

        # Track DB batch
        db_batch = []
        jp_day_batch = []

        for sub in subscribers:
            # EXP-11: session-specific cash picks — train and score per session.
            # Each session call trains only on that session's draw history so
            # the model reflects patterns unique to MIDDAY, EVENING, or NIGHT.
            for _sim_sess in SESSIONS:
                sess_picks = generate_picks_v3(sub, None, ga_data, JACKPOT_ROOT, session=_sim_sess)

                # Confidence normalisation for this session's stat pool
                _raw_stats = sess_picks.get("_stats", {})
                _conf_map: dict[str, dict[str, float]] = {}
                for _g, _gkey in (("Cash3", "cash3"), ("Cash4", "cash4")):
                    _gs = _raw_stats.get(_gkey, {})
                    if _gs:
                        _max = max(v["score"] for v in _gs.values())
                        _conf_map[_g] = {
                            combo: v["score"] / _max if _max else 0.0
                            for combo, v in _gs.items()
                        }
                    else:
                        _conf_map[_g] = {}

                # Only score this pick against its own session's actual
                for game in ["Cash3", "Cash4"]:
                    game_picks = sess_picks.get(game, {})
                    for lane, numbers in game_picks.items():
                        for pick in (numbers or []):
                            if not pick:
                                continue
                            pick = str(pick).strip()

                            actual_this = actuals_today[game][_sim_sess]

                            _is_s = int(bool(actual_this) and is_straight_win(pick, actual_this))
                            _is_b = int(bool(actual_this) and is_box_win(pick, actual_this))

                            # Fill only the column for this session; others zero
                            if _sim_sess == "MIDDAY":
                                mid_s, mid_b = _is_s, _is_b
                                eve_s = eve_b = ngt_s = ngt_b = 0
                                actual_m, actual_e, actual_n = actual_this, "", ""
                            elif _sim_sess == "EVENING":
                                eve_s, eve_b = _is_s, _is_b
                                mid_s = mid_b = ngt_s = ngt_b = 0
                                actual_m, actual_e, actual_n = "", actual_this, ""
                            else:  # NIGHT
                                ngt_s, ngt_b = _is_s, _is_b
                                mid_s = mid_b = eve_s = eve_b = 0
                                actual_m, actual_e, actual_n = "", "", actual_this

                            conf_score = round(_conf_map.get(game, {}).get(pick, 0.0), 6)

                            kit = sub.get("kit", "BOOK")
                            play_type = resolve_play_type(
                                game,
                                build_ctx_for_sub(kit, lane)
                            )

                            mid_1off = int(bool(actual_m) and is_one_off_win(pick, actual_m)) \
                                if play_type == "1-OFF" else 0
                            eve_1off = int(bool(actual_e) and is_one_off_win(pick, actual_e)) \
                                if play_type == "1-OFF" else 0
                            ngt_1off = int(bool(actual_n) and is_one_off_win(pick, actual_n)) \
                                if play_type == "1-OFF" else 0

                            if play_type == "STRAIGHT":
                                any_w = int(any([mid_s, eve_s, ngt_s]))
                            elif play_type == "BOX":
                                any_w = int(any([mid_b, eve_b, ngt_b]))
                            elif play_type == "1-OFF":
                                any_w = int(any([mid_1off, eve_1off, ngt_1off]))
                            else:
                                any_w = int(any([mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b]))

                            db_batch.append((
                                date_str, sub["subscriber_id"], kit, game, lane, pick,
                                actual_m, actual_e, actual_n,
                                mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b, any_w,
                                play_type, conf_score
                            ))

                            writer.writerow([
                                date_str, sub["subscriber_id"], kit, game, lane, pick,
                                actual_m, actual_e, actual_n,
                                mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b, any_w,
                                play_type, conf_score
                            ])

                            stats[game]["picks"]    += 1
                            stats[game]["straight"] += _is_s
                            stats[game]["box"]      += _is_b
                            stats[game]["one_off"]  += (mid_1off + eve_1off + ngt_1off)
                            if any_w:
                                pt_stats[f"{game}:{play_type}"] += 1

            # ── Jackpot games — single pooled call ────────────────────────────
            picks_raw = generate_picks_v3(sub, None, ga_data, JACKPOT_ROOT)

            # ── Jackpot games ─────────────────────────────────────────────────
            kit = sub.get("kit", "BOOK")
            for jp_game in ["MegaMillions", "Powerball", "Millionaire For Life"]:
                actual_draw = jackpot_actuals[jp_game].get(sim_date)
                if actual_draw is None:
                    continue  # no draw that day
                actual_whites, actual_special = actual_draw
                actual_str = (
                    " ".join(f"{n:02d}" for n in sorted(actual_whites))
                    + f" + {actual_special:02d}"
                )
                prize_table = JACKPOT_PRIZE_TABLES[jp_game]
                jp_picks = picks_raw.get(jp_game, {}).get("lane_system", [])
                for pick_str in (jp_picks or []):
                    if not pick_str:
                        continue
                    wm, sm, tier, prize = score_jackpot_pick(
                        pick_str, actual_whites, actual_special, prize_table
                    )
                    jp_day_batch.append((
                        date_str, sub["subscriber_id"], kit,
                        jp_game, pick_str, actual_str,
                        wm, sm, tier, prize
                    ))
                    jp_stats[jp_game]["picks"] += 1
                    if tier:
                        jp_stats[jp_game]["wins"] += 1
                        jp_stats[jp_game]["prize_total"] += prize
                        jp_stats[jp_game]["tiers"][tier] += 1

        # Batch insert to DB
        conn.executemany(
            """INSERT INTO sim_results
               (sim_date, subscriber, kit, game, lane, pick,
                actual_mid, actual_eve, actual_night,
                mid_straight, mid_box, eve_straight, eve_box,
                night_straight, night_box, any_win, play_type, confidence_score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            db_batch
        )
        if jp_day_batch:
            conn.executemany(
                """INSERT INTO sim_jackpot_results
                   (sim_date, subscriber, kit, game, pick, actual,
                    white_match, special_match, tier, prize)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                jp_day_batch
            )
        conn.commit()

        # Progress
        c3 = stats["Cash3"]
        c4 = stats["Cash4"]
        jp_win_today = sum(jp_stats[g]["wins"] for g in ["MegaMillions", "Powerball", "Millionaire For Life"])
        print(
            f"  [{day_offset+1:3d}/{num_days}] {date_str}  "
            f"Cash3 s={c3['straight']} b={c3['box']} / {c3['picks']}  |  "
            f"Cash4 s={c4['straight']} b={c4['box']} / {c4['picks']}  |  "
            f"JP wins={jp_win_today}"
        )

    csv_file.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n=== FINAL SUMMARY ===")
    summary_rows = []
    for game in ["Cash3", "Cash4"]:
        s = stats[game]
        s_pct = round(s["straight"] / s["picks"] * 100, 4) if s["picks"] else 0
        b_pct = round(s["box"]      / s["picks"] * 100, 4) if s["picks"] else 0
        o_pct = round(s["one_off"]  / s["picks"] * 100, 4) if s["picks"] else 0
        print(
            f"  {game}: {s['picks']:,} picks | "
            f"straight hits={s['straight']:,} ({s_pct}%) | "
            f"box hits={s['box']:,} ({b_pct}%) | "
            f"1-off hits={s['one_off']:,} ({o_pct}%)"
        )
        summary_rows.append((game, s["picks"], s["straight"], s_pct, s["box"], b_pct))

    print("\n  -- Wins by play type --")
    for key in sorted(pt_stats):
        print(f"    {key:<30}: {pt_stats[key]:,} wins")

    print()
    print("  -- Jackpot Secondary Prizes --")
    for jp_game in ["MegaMillions", "Powerball", "Millionaire For Life"]:
        s = jp_stats[jp_game]
        if s["picks"] == 0:
            print(f"  {jp_game}: no draws in simulation window")
            continue
        win_pct = round(s["wins"] / s["picks"] * 100, 4)
        print(f"  {jp_game}: {s['picks']:,} picks | "
              f"prize wins={s['wins']:,} ({win_pct}%) | "
              f"estimated prize total=${s['prize_total']:,}")
        for tier, cnt in sorted(s["tiers"].items(), key=lambda x: -x[1]):
            print(f"      {tier:12s} x{cnt:,}")

    # Write summary to DB
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c3 = stats["Cash3"]
    c4 = stats["Cash4"]
    conn.execute(
        """INSERT INTO sim_summary
           (run_ts, total_picks, total_wins_straight, total_wins_box,
            cash3_straight_pct, cash3_box_pct, cash4_straight_pct, cash4_box_pct)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            run_ts,
            c3["picks"] + c4["picks"],
            c3["straight"] + c4["straight"],
            c3["box"] + c4["box"],
            round(c3["straight"] / c3["picks"] * 100, 4) if c3["picks"] else 0,
            round(c3["box"]      / c3["picks"] * 100, 4) if c3["picks"] else 0,
            round(c4["straight"] / c4["picks"] * 100, 4) if c4["picks"] else 0,
            round(c4["box"]      / c4["picks"] * 100, 4) if c4["picks"] else 0,
        )
    )
    conn.commit()
    conn.close()

    print(f"\n  DB  : {DB_PATH}")
    print(f"  CSV : {CSV_OUT}")
    print("Done.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walk-forward historical simulation")
    parser.add_argument("--start", default="2026-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--days",  type=int, default=91,   help="Number of days")
    parser.add_argument("--subs", type=int, default=999, help="Number of subscribers (use multiple of 3)")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    run_simulation(start, args.days, args.subs)
