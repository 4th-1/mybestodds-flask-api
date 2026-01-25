import json
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------
PROJECT_ROOT = Path(r"C:\MyBestOdds\jackpot_system_v3")

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "data" / "ga_results"
AUDIT_DIR = OUTPUTS_DIR / "AUDIT"
AUDIT_DIR.mkdir(exist_ok=True)

START_DATE = "2025-09-01"
END_DATE   = "2025-11-10"

DATE_START = pd.to_datetime(START_DATE).date()
DATE_END   = pd.to_datetime(END_DATE).date()


# --------------------------------------------------------------------
# NORMALIZATION HELPERS
# --------------------------------------------------------------------

def safe_date(raw):
    try:
        return pd.to_datetime(raw).date()
    except Exception:
        return None


def normalize_session(raw: str) -> str:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ["mid", "midday", "mid day", "day"]:
        return "Midday"
    if s in ["eve", "evening", "pm"]:
        return "Evening"
    if s in ["night", "late", "n"]:
        return "Night"
    return s.capitalize()


def normalize_game(raw: str) -> str:
    if raw is None:
        return None
    g = str(raw).strip().lower()
    if "cash 3" in g or "cash3" in g:
        return "Cash3"
    if "cash 4" in g or "cash4" in g:
        return "Cash4"
    if "mega" in g:
        return "MegaMillions"
    if "power" in g:
        return "Powerball"
    if "cash4life" in g or "cash 4 life" in g:
        return "Cash4Life"
    return raw


def normalize_number(num_str: str, game_name: str) -> str:
    if num_str is None:
        return None
    s = "".join(ch for ch in str(num_str) if ch.isdigit())
    if not s:
        return None
    if game_name == "Cash4":
        return s.zfill(4)
    if game_name == "Cash3":
        return s.zfill(3)
    # For jackpot games we just store the cleaned digit string / sequence
    return s


# --------------------------------------------------------------------
# 1. LOAD & AUTO-FIX GA RESULTS (all games)
# --------------------------------------------------------------------

def load_cash3_results():
    path_main = RESULTS_DIR / "Cash3_Midday_Evening_Night.csv"
    path_alt = RESULTS_DIR / "Cash 3 Midday_Night.csv"

    frames = []
    for p in [path_main, path_alt]:
        if p.exists():
            df = pd.read_csv(p)
            frames.append(df)

    if not frames:
        print("[GA:Cash3] No Cash3 files found.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # Expect columns: Game, Draw Date, Time, Winning Numbers
    # Auto-map variations
    if "Draw Date" in df.columns:
        df["date"] = df["Draw Date"].apply(safe_date)
    elif "date" in df.columns:
        df["date"] = df["date"].apply(safe_date)
    else:
        raise ValueError("[GA:Cash3] No date column detected.")

    if "Time" in df.columns:
        df["session"] = df["Time"].apply(normalize_session)
    else:
        df["session"] = None

    if "Winning Numbers" in df.columns:
        df["winning_number"] = df["Winning Numbers"]
    else:
        raise ValueError("[GA:Cash3] No 'Winning Numbers' column detected.")

    df["game"] = "Cash3"

    df = df.dropna(subset=["date", "winning_number"])
    df["winning_number"] = df["winning_number"].apply(
        lambda x: normalize_number(x, "Cash3")
    )
    df = df.dropna(subset=["winning_number"])

    # Restrict to window
    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]

    return df[["date", "game", "session", "winning_number"]]


def load_cash4_results():
    frames = []

    # Midday & Night CSV
    path_midnight = RESULTS_DIR / "Cash4_Midday_Evening_Night.csv"
    if path_midnight.exists():
        c4 = pd.read_csv(path_midnight)
        if "Draw Date" in c4.columns:
            c4["date"] = c4["Draw Date"].apply(safe_date)
        else:
            raise ValueError("[GA:Cash4] No 'Draw Date' column in Cash4 CSV.")
        if "Time" in c4.columns:
            c4["session"] = c4["Time"].apply(normalize_session)
        else:
            c4["session"] = None
        if "Winning Numbers" in c4.columns:
            c4["winning_number"] = c4["Winning Numbers"]
        else:
            raise ValueError("[GA:Cash4] No 'Winning Numbers' column in Cash4 CSV.")
        c4["game"] = "Cash4"
        frames.append(c4)

    # Evening-only Excel
    path_evening = RESULTS_DIR / "Cash 4 Evening.xlsx"
    if path_evening.exists():
        ev = pd.read_excel(path_evening)
        # Expect columns like: 'Cash 4 Draw Date', 'Time', 'Unnamed: 3' with spaced digits
        date_col = None
        for cand in ["Cash 4 Draw Date", "Draw Date", "date"]:
            if cand in ev.columns:
                date_col = cand
                break
        if date_col is None:
            raise ValueError("[GA:Cash4] No date column in Cash 4 Evening.xlsx")

        ev["date"] = ev[date_col].apply(safe_date)

        if "Time" in ev.columns:
            ev["session"] = ev["Time"].apply(normalize_session)
        else:
            ev["session"] = "Evening"

        # Find the column with the digit sequence
        num_col = None
        for cand in ["Winning Numbers", "Unnamed: 3", "Numbers"]:
            if cand in ev.columns:
                num_col = cand
                break
        if num_col is None:
            raise ValueError("[GA:Cash4] No number column in Cash 4 Evening.xlsx")

        ev["winning_number"] = ev[num_col].astype(str)
        ev["game"] = "Cash4"
        frames.append(ev)

    if not frames:
        print("[GA:Cash4] No Cash4 files found.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["date", "winning_number"])
    df["session"] = df["session"].apply(normalize_session)
    df["winning_number"] = df["winning_number"].apply(
        lambda x: normalize_number(x, "Cash4")
    )
    df = df.dropna(subset=["winning_number"])
    df["game"] = "Cash4"

    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]
    return df[["date", "game", "session", "winning_number"]]


def load_mm_pb_c4l_results():
    frames = []

    # Mega Millions
    mm_path = RESULTS_DIR / "Mega Millions 9-10-25 - 11-10-25.xlsx"
    if mm_path.exists():
        mm = pd.read_excel(mm_path)
        # Expect: Game, Draw Date, Winning Numbers, Cash Ball
        mm["date"] = mm["Draw Date"].apply(safe_date)
        mm["game"] = "MegaMillions"
        mm["session"] = "11PM"
        mm["winning_number"] = mm["Winning Numbers"].astype(str) + " + " + mm["Cash Ball"].astype(str)
        frames.append(mm[["date", "game", "session", "winning_number"]])

    # Powerball
    pb_path = RESULTS_DIR / "Powerball.xlsx"
    if pb_path.exists():
        pb = pd.read_excel(pb_path)
        pb["date"] = pb["Draw Date"].apply(safe_date)
        pb["game"] = "Powerball"
        pb["session"] = "10:59PM"
        pb["winning_number"] = pb["Winning Numbers"].astype(str) + " + " + pb["Cash Ball"].astype(str)
        frames.append(pb[["date", "game", "session", "winning_number"]])

    # Cash4Life
    c4l_path = RESULTS_DIR / "Cash4Life 9-01-2025-11-10-25.xlsx"
    if c4l_path.exists():
        c4l = pd.read_excel(c4l_path)
        c4l["date"] = c4l["Draw Date"].apply(safe_date)
        c4l["game"] = "Cash4Life"
        c4l["session"] = "9PM"
        c4l["winning_number"] = c4l["Winning Numbers"].astype(str) + " + " + c4l["Cash Ball"].astype(str)
        frames.append(c4l[["date", "game", "session", "winning_number"]])

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["date", "winning_number"])
    df = df[(df["date"] >= DATE_START) & (df["date"] <= DATE_END)]
    return df


def load_all_ga_results():
    print("[GA] Loading GA results from data\\results ...")
    c3 = load_cash3_results()
    c4 = load_cash4_results()
    jackpots = load_mm_pb_c4l_results()

    frames = [df for df in [c3, c4, jackpots] if not df.empty]
    if not frames:
        print("[GA] ERROR: No GA result data loaded.")
        return pd.DataFrame()

    results = pd.concat(frames, ignore_index=True)
    results = results.dropna(subset=["date", "game", "winning_number"])
    results["game"] = results["game"].apply(normalize_game)
    out_path = AUDIT_DIR / f"GA_results_{START_DATE}_to_{END_DATE}.csv"
    results.to_csv(out_path, index=False)
    print(f"[GA] Normalized GA results saved to: {out_path}")
    return results


# --------------------------------------------------------------------
# 2. LOAD KIT PREDICTIONS (per-subscriber folder, per-day JSON)
# --------------------------------------------------------------------

def load_kit_predictions(kit_name: str) -> pd.DataFrame:
    """
    kit_name: 'BOOK', 'BOOK3', 'BOSK'

    Expects directories like:
        outputs\BOSK_ZL_2025-09-01_to_2025-11-10\
    with daily files:
        2025-09-01.json, 2025-09-02.json, ...

    Each JSON:
    {
      "date": "2025-09-01",
      "score": 57.5,
      "picks": {
        "Cash3": { "lane_mmfsn": [], "lane_system": ["726","029"] },
        "Cash4": { "lane_system": [...] }
      }
    }
    """
    print(f"[{kit_name}] Loading predictions (Auto-Fix Mode C)...")
    rows = []

    for sub_dir in OUTPUTS_DIR.iterdir():
        if not sub_dir.is_dir():
            continue
        if not sub_dir.name.startswith(f"{kit_name}_"):
            continue
        if f"{START_DATE}_to_{END_DATE}" not in sub_dir.name:
            continue

        # Extract subscriber id from folder name: KIT_SUBID_...
        parts = sub_dir.name.split("_")
        subscriber_id = parts[1] if len(parts) > 1 else sub_dir.name
        subscriber_name = subscriber_id  # we don't have full names here

        print(f"[{kit_name}] Reading subscriber folder: {sub_dir.name}")

        for json_file in sorted(sub_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[{kit_name}] JSON error in {json_file}: {e} (SKIPPED)")
                continue

            draw_date = safe_date(data.get("date"))
            if draw_date is None:
                continue
            if not (DATE_START <= draw_date <= DATE_END):
                continue

            score = data.get("score", 50.0)  # day-level score -> used as confidence
            picks = data.get("picks", {})
            if not isinstance(picks, dict):
                continue

            for game_key, game_block in picks.items():
                game_norm = normalize_game(game_key)
                if game_norm not in ["Cash3", "Cash4"]:
                    # For now, we focus audit on Cash3/Cash4; jackpots can be added later
                    continue

                if not isinstance(game_block, dict):
                    continue

                for lane_name, nums in game_block.items():
                    if not isinstance(nums, list):
                        continue
                    for num in nums:
                        norm_num = normalize_number(num, game_norm)
                        if not norm_num:
                            continue

                        row = {
                            "kit": kit_name,
                            "subscriber_id": subscriber_id,
                            "subscriber_name": subscriber_name,
                            "date": draw_date,
                            "game": game_norm,
                            "session": None,  # current V3 outputs are date-only for lanes
                            "predicted_number": norm_num,
                            "lane": lane_name,
                            "confidence_score": score,
                        }
                        rows.append(row)

    if not rows:
        print(f"[{kit_name}] WARNING: No predictions found for this kit.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    out_path = AUDIT_DIR / f"{kit_name}_predictions_{START_DATE}_to_{END_DATE}.csv"
    df.to_csv(out_path, index=False)
    print(f"[{kit_name}] Flattened predictions saved to: {out_path}")
    return df


# --------------------------------------------------------------------
# 3. HIT CLASSIFICATION (DATE + GAME LEVEL)
# --------------------------------------------------------------------

def classify_hits(pred_df: pd.DataFrame, results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Because current V3 daily JSON output doesn't include sessions,
    we do a DATE+GAME-level audit:

    A prediction is a 'hit' if it matches ANY session's winning_number
    for that date & game.
    """

    if pred_df.empty:
        return pred_df

    # Restrict GA results to Cash3/Cash4 for now
    r = results_df[results_df["game"].isin(["Cash3", "Cash4"])].copy()

    # Build list of winning numbers per (date, game)
    agg = (
        r.groupby(["date", "game"])["winning_number"]
        .apply(list)
        .reset_index()
        .rename(columns={"winning_number": "winning_numbers"})
    )

    merged = pred_df.merge(
        agg,
        how="left",
        left_on=["date", "game"],
        right_on=["date", "game"],
    )

    def hit_type(row):
        wins = row.get("winning_numbers")
        if not isinstance(wins, list):
            return "no_result"
        predicted = row["predicted_number"]
        if predicted in wins:
            # We don't know session, so treat as a date-level straight hit
            return "straight"
        return "miss"

    merged["hit_type"] = merged.apply(hit_type, axis=1)
    return merged


# --------------------------------------------------------------------
# 4. SUMMARY + EXCEL EXPORT
# --------------------------------------------------------------------

def summarize_and_export(kit_name: str, merged: pd.DataFrame):
    if merged.empty:
        print(f"[{kit_name}] Nothing to summarize.")
        return

    merged["date"] = pd.to_datetime(merged["date"])

    summary_hits = (
        merged.groupby("hit_type")["predicted_number"]
        .count()
        .rename("count")
        .reset_index()
    )

    by_game = (
        merged.groupby(["game", "hit_type"])["predicted_number"]
        .count()
        .rename("count")
        .reset_index()
    )

    by_subscriber = (
        merged.groupby(["subscriber_id", "subscriber_name", "hit_type"])["predicted_number"]
        .count()
        .rename("count")
        .reset_index()
    )

    merged["confidence_score"] = pd.to_numeric(
        merged["confidence_score"], errors="coerce"
    ).fillna(50.0)

    merged["confidence_band"] = pd.cut(
        merged["confidence_score"],
        bins=[-1, 20, 40, 60, 80, 100],
        labels=["0-20", "21-40", "41-60", "61-80", "81-100"],
    )

    by_conf = (
        merged.groupby(["confidence_band", "hit_type"])["predicted_number"]
        .count()
        .rename("count")
        .reset_index()
    )

    out_xlsx = AUDIT_DIR / f"{kit_name}_audit_{START_DATE}_to_{END_DATE}.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as writer:
        summary_hits.to_excel(writer, sheet_name="summary_hits", index=False)
        by_game.to_excel(writer, sheet_name="by_game", index=False)
        by_subscriber.to_excel(writer, sheet_name="by_subscriber", index=False)
        by_conf.to_excel(writer, sheet_name="by_confidence", index=False)
        merged.to_excel(writer, sheet_name="raw_predictions", index=False)

    print(f"[{kit_name}] Audit workbook written to: {out_xlsx}")


# --------------------------------------------------------------------
# 5. MAIN RUNNER
# --------------------------------------------------------------------

def run_audit_for_kit(kit_name: str, results_df: pd.DataFrame):
    print(f"\n========== AUDIT START: {kit_name} ==========")
    preds = load_kit_predictions(kit_name)
    if preds.empty:
        print(f"[{kit_name}] No predictions. Skipping.")
        return
    merged = classify_hits(preds, results_df)
    summarize_and_export(kit_name, merged)
    print(f"========== AUDIT FINISHED: {kit_name} ==========\n")


if __name__ == "__main__":
    results_df = load_all_ga_results()
    if results_df.empty:
        print("[GLOBAL] No GA results – cannot continue audit.")
    else:
        for kit in ["BOOK", "BOOK3", "BOSK"]:
            run_audit_for_kit(kit, results_df)
