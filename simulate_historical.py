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

# ── Config ───────────────────────────────────────────────────────────────────
CASH3_CSV = ROOT / "historical_data" / "ga_results" / "2026" / "Cash3.csv"
CASH4_CSV = ROOT / "historical_data" / "ga_results" / "2026" / "Cash4.csv"
DB_PATH   = ROOT / "simulation_results.db"
CSV_OUT   = ROOT / "simulation_report.csv"

SESSIONS  = ["MIDDAY", "EVENING", "NIGHT"]

# ── Load actual draw results ──────────────────────────────────────────────────
def load_actuals(csv_path: Path) -> dict:
    """Returns {(date_obj, session): number_str}"""
    actuals = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.strptime(row["date"], "%m/%d/%Y").date()
                actuals[(d, row["session"].upper())] = row["number"].strip()
            except (ValueError, KeyError):
                continue
    return actuals


def load_history_for_engine(csv_path: Path, before_date) -> list:
    """Return rows with draw_date < before_date in engine format."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.strptime(row["date"], "%m/%d/%Y").date()
            except ValueError:
                continue
            if d < before_date:
                rows.append({
                    "draw_date": row["date"],
                    "winning_numbers": row["number"].strip(),
                    "session": row["session"].upper(),
                })
    return rows


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


# ── DB setup ──────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sim_date    TEXT,
            subscriber  TEXT,
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
            any_win       INTEGER DEFAULT 0
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
def generate_subscribers(n: int) -> list:
    """
    Generate n subscriber profiles.
    Uses a pool of 2-letter initials so MMFSN profiles are varied.
    """
    import string
    letters = string.ascii_uppercase
    initials_pool = [a + b for a in letters for b in letters]  # 676 combos
    subs = []
    for i in range(n):
        initials = initials_pool[i % len(initials_pool)]
        subs.append({
            "subscriber_id": f"SIM_{i+1:04d}",
            "initials": initials,
            "games": ["Cash3", "Cash4"],
        })
    return subs


# ── Main simulation ───────────────────────────────────────────────────────────
def run_simulation(start_date: datetime, num_days: int, num_subs: int):
    print(f"\n=== Historical Simulation ===")
    print(f"  Period : {start_date.date()} + {num_days} days")
    print(f"  Subs   : {num_subs}")
    print(f"  Engine : generate_picks_v3() (direct call, no HTTP)")
    print()

    # Load all actual results up front
    cash3_actuals = load_actuals(CASH3_CSV)
    cash4_actuals = load_actuals(CASH4_CSV)

    # Subscriber pool
    subscribers = generate_subscribers(num_subs)

    # DB
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    # CSV report writer
    csv_file = open(CSV_OUT, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow([
        "date", "subscriber", "game", "lane", "pick",
        "actual_mid", "actual_eve", "actual_night",
        "mid_straight", "mid_box", "eve_straight", "eve_box",
        "night_straight", "night_box", "any_win"
    ])

    # Counters for summary
    stats = defaultdict(lambda: {"picks": 0, "straight": 0, "box": 0})

    # Walk-forward loop
    for day_offset in range(num_days):
        sim_date = (start_date + timedelta(days=day_offset)).date()
        date_str  = sim_date.strftime("%Y-%m-%d")

        # Load only history BEFORE this date (no future leakage)
        cash3_hist = load_history_for_engine(CASH3_CSV, sim_date)
        cash4_hist = load_history_for_engine(CASH4_CSV, sim_date)
        ga_data    = build_ga_data(cash3_hist, cash4_hist)

        # Actuals for this date
        actuals_today = {
            "Cash3": {s: cash3_actuals.get((sim_date, s), "") for s in SESSIONS},
            "Cash4": {s: cash4_actuals.get((sim_date, s), "") for s in SESSIONS},
        }

        # Track DB batch
        db_batch = []

        for sub in subscribers:
            picks_raw = generate_picks_v3(sub, None, ga_data, JACKPOT_ROOT)

            for game in ["Cash3", "Cash4"]:
                game_picks = picks_raw.get(game, {})
                for lane, numbers in game_picks.items():
                    for pick in (numbers or []):
                        if not pick:
                            continue
                        pick = str(pick).strip()

                        actual_m = actuals_today[game]["MIDDAY"]
                        actual_e = actuals_today[game]["EVENING"]
                        actual_n = actuals_today[game]["NIGHT"]

                        mid_s = int(bool(actual_m) and is_straight_win(pick, actual_m))
                        mid_b = int(bool(actual_m) and is_box_win(pick, actual_m))
                        eve_s = int(bool(actual_e) and is_straight_win(pick, actual_e))
                        eve_b = int(bool(actual_e) and is_box_win(pick, actual_e))
                        ngt_s = int(bool(actual_n) and is_straight_win(pick, actual_n))
                        ngt_b = int(bool(actual_n) and is_box_win(pick, actual_n))
                        any_w = int(any([mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b]))

                        db_batch.append((
                            date_str, sub["subscriber_id"], game, lane, pick,
                            actual_m, actual_e, actual_n,
                            mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b, any_w
                        ))

                        writer.writerow([
                            date_str, sub["subscriber_id"], game, lane, pick,
                            actual_m, actual_e, actual_n,
                            mid_s, mid_b, eve_s, eve_b, ngt_s, ngt_b, any_w
                        ])

                        # running stats
                        stats[game]["picks"]    += 1
                        stats[game]["straight"] += (mid_s + eve_s + ngt_s)
                        stats[game]["box"]      += (mid_b + eve_b + ngt_b)

        # Batch insert to DB
        conn.executemany(
            """INSERT INTO sim_results
               (sim_date, subscriber, game, lane, pick,
                actual_mid, actual_eve, actual_night,
                mid_straight, mid_box, eve_straight, eve_box,
                night_straight, night_box, any_win)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            db_batch
        )
        conn.commit()

        # Progress
        c3 = stats["Cash3"]
        c4 = stats["Cash4"]
        print(
            f"  [{day_offset+1:3d}/{num_days}] {date_str}  "
            f"Cash3 straight={c3['straight']} box={c3['box']} / {c3['picks']} picks  |  "
            f"Cash4 straight={c4['straight']} box={c4['box']} / {c4['picks']} picks"
        )

    csv_file.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n=== FINAL SUMMARY ===")
    summary_rows = []
    for game in ["Cash3", "Cash4"]:
        s = stats[game]
        total_draw_slots = s["picks"] * 3  # 3 sessions per pick
        s_pct = round(s["straight"] / s["picks"] * 100, 4) if s["picks"] else 0
        b_pct = round(s["box"]      / s["picks"] * 100, 4) if s["picks"] else 0
        print(
            f"  {game}: {s['picks']:,} picks | "
            f"straight hits={s['straight']:,} ({s_pct}%) | "
            f"box hits={s['box']:,} ({b_pct}%)"
        )
        summary_rows.append((game, s["picks"], s["straight"], s_pct, s["box"], b_pct))

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
    parser.add_argument("--subs",  type=int, default=1000, help="Number of subscribers")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    run_simulation(start, args.days, args.subs)
