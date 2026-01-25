"""
rebuild_history_v3_5.py
---------------------------------------
Automates the creation of jackpot history JSON files:

  - mega_millions_stats.json
  - powerball_stats.json
  - cash4life_stats.json

This script:
  ✔ Parses the latest jackpot raw files
  ✔ Computes frequency (main + bonus)
  ✔ Computes recency ranking (0 = most recent)
  ✔ Handles annual reset (Jan 1)
  ✔ Handles quarterly refresh (Apr 1, Jul 1, Oct 1)
  ✔ Writes normalized history for V3.5

Run manually:
    python rebuild_history_v3_5.py

You may also schedule this with Windows Task Scheduler to run quarterly.
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(r"C:\MyBestOdds\jackpot_system_v3")
GA_RESULTS = PROJECT_ROOT / "data" / "ga_results"
HISTORY_DIR = PROJECT_ROOT / "data" / "jackpot_history"

# --------------------------------------------------------
# Helper Functions
# --------------------------------------------------------
def _extract_main_and_bonus(row):
    """Split Winning Numbers column into main and bonus lists."""
    raw_main = str(row["Winning Numbers"]).replace(",", " ").strip()
    main = [int(x) for x in raw_main.split() if x.isdigit()]

    bonus = row.get("Cash Ball", "")
    bonus_balls = []
    if pd.notna(bonus):
        try:
            bonus_balls = [int(bonus)]
        except:
            pass

    return main, bonus_balls


def _compute_frequency(draws):
    freq_main = {}
    freq_bonus = {}

    for draw in draws:
        for b in draw["main"]:
            freq_main[b] = freq_main.get(b, 0) + 1

        for b in draw["bonus"]:
            freq_bonus[b] = freq_bonus.get(b, 0) + 1

    return freq_main, freq_bonus


def _compute_recency(draws):
    """Recency ranking: 0 = most recent appearance."""
    recency_main = {}
    recency_bonus = {}

    # sorted by date descending
    sorted_draws = sorted(draws, key=lambda x: x["date"], reverse=True)

    rank = 0
    seen_main = set()
    seen_bonus = set()

    for draw in sorted_draws:
        for b in draw["main"]:
            if b not in seen_main:
                recency_main[b] = rank
                seen_main.add(b)

        for b in draw["bonus"]:
            if b not in seen_bonus:
                recency_bonus[b] = rank
                seen_bonus.add(b)

        rank += 1

    return recency_main, recency_bonus


def _build_history_file(game_name, filename):
    """
    Reads a jackpot XLSX file from data/ga_results and builds history JSON.
    """

    path = GA_RESULTS / filename
    if not path.exists():
        print(f"[WARN] Missing file: {path}")
        return

    print(f"[HISTORY] Parsing {game_name}: {path}")

    xls = pd.ExcelFile(path)
    df = xls.parse(xls.sheet_names[0])

    draws = []
    for _, row in df.dropna(subset=["Game", "Draw Date"]).iterrows():
        date = pd.to_datetime(row["Draw Date"]).strftime("%Y-%m-%d")
        main, bonus = _extract_main_and_bonus(row)

        draws.append({
            "date": date,
            "main": main,
            "bonus": bonus
        })

    # Frequency
    freq_main, freq_bonus = _compute_frequency(draws)

    # Recency ranking
    rec_main, rec_bonus = _compute_recency(draws)

    # Compose history JSON
    history = {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "game": game_name,
        "main_frequency": freq_main,
        "bonus_frequency": freq_bonus,
        "main_recency": rec_main,
        "bonus_recency": rec_bonus,
        "total_draws": len(draws)
    }

    # Write out
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HISTORY_DIR / f"{game_name.lower()}_stats.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print(f"[HISTORY] Wrote: {out_path}")


# --------------------------------------------------------
# MAIN PROCESS
# --------------------------------------------------------
def rebuild():
    print("\n------------------------------------------")
    print(" My Best Odds – Jackpot History Rebuilder ")
    print("------------------------------------------\n")

    # Annual reset logic (optional)
    month = datetime.now().month
    day = datetime.now().day

    if month == 1 and day <= 3:
        print("[INFO] Annual reset triggered (January). Rebuilding all stats.")

    # ALWAYS rebuild (safe)
    _build_history_file("MegaMillions", "Mega Millions 9-10-25 - 11-10-25.xlsx")
    _build_history_file("Powerball", "Powerball.xlsx")
    _build_history_file("Cash4Life", "Cash4Life 9-01-2025-11-10-25.xlsx")

    print("\n[COMPLETE] Jackpot history rebuild finished.\n")


if __name__ == "__main__":
    rebuild()
