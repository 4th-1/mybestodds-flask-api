# build_ga_results.py (FULLY FIXED VERSION)

import json
from pathlib import Path
import pandas as pd  # pip install pandas openpyxl

ROOT = Path(__file__).resolve().parent
GA_DIR = ROOT / "data" / "ga_results"

# ---------------------------------------------------------
# NORMALIZATION HELPERS
# ---------------------------------------------------------

def normalize_columns(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def normalize_game(text: str) -> str:
    """
    Normalize all variations of game labels:
    'Cash 3', 'Cash3', 'CASH 3', 'Pick 3', etc.
    """
    if not text:
        return ""
    t = text.strip().lower().replace(" ", "")
    if "cash3" in t or "pick3" in t or t == "c3":
        return "cash3"
    if "cash4" in t or "pick4" in t or t == "c4":
        return "cash4"
    return ""


def normalize_time(text: str) -> str:
    """
    Normalize all variations of time labels:
    Midday / Mid / Mid day / MIDDAY
    Night / Evening / Nite / NIGHT
    """
    if not text:
        return ""
    t = text.strip().lower()

    if "mid" in t or "day" in t:
        return "midday"
    if "even" in t or "night" in t or "nite" in t:
        return "night"

    return ""


# ---------------------------------------------------------
# LOADERS
# ---------------------------------------------------------

def load_cash3_cash4_template():
    xlsx_path = GA_DIR / "Cash 3 & Cash 4 Template.xlsx"
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Missing file: {xlsx_path}")

    df = pd.read_excel(xlsx_path)
    df = normalize_columns(df)

    col_map = {
        "Game": "game",
        "Draw Date": "draw_date",
        "Time": "time",
        "Winning Numbers": "winning_numbers",
    }
    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(
            f"Cash 3 & Cash 4 Template.xlsx is missing columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    df = df[list(col_map.keys())].rename(columns=col_map)

    # Normalize values
    df["draw_date"] = pd.to_datetime(df["draw_date"]).dt.strftime("%Y-%m-%d")
    df["game_norm"] = df["game"].apply(normalize_game)
    df["time_norm"] = df["time"].apply(normalize_time)

    # Preserve leading zeros
    df["winning_numbers"] = (
        df["winning_numbers"].astype(str).str.strip().apply(lambda x: x.zfill(4))
    )

    return df


def load_cash3_evening_csv():
    csv_path = GA_DIR / "Cash3 Evening 901-1110 (1).csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing file: {csv_path}")

    df = pd.read_csv(csv_path)
    df = normalize_columns(df)

    col_map = {
        "Draw Date": "draw_date",
        "Winning Numbers": "winning_numbers",
        "Time": "time",
    }
    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(
            f"Cash3 Evening CSV is missing columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    df = df[list(col_map.keys())].rename(columns=col_map)

    df["game_norm"] = "cash3"
    df["draw_date"] = pd.to_datetime(df["draw_date"]).dt.strftime("%Y-%m-%d")
    df["time_norm"] = df["time"].apply(normalize_time)

    # Preserve leading zeros (Cash3 uses 3 digits)
    df["winning_numbers"] = (
        df["winning_numbers"].astype(str).str.strip().apply(lambda x: x.zfill(3))
    )

    return df


# ---------------------------------------------------------
# FILTER FUNCTIONS
# ---------------------------------------------------------

def filter_cash3_midday(df):
    return df[(df["game_norm"] == "cash3") & (df["time_norm"] == "midday")].copy()


def filter_cash3_evening(df):
    return df[(df["game_norm"] == "cash3") & (df["time_norm"] == "night")].copy()


def filter_cash4_night(df):
    return df[(df["game_norm"] == "cash4") & (df["time_norm"] == "night")].copy()


# ---------------------------------------------------------
# JSON EXPORTER
# ---------------------------------------------------------

def df_to_json_records(df):
    return df[["game_norm", "draw_date", "time_norm", "winning_numbers"]].rename(
        columns={
            "game_norm": "game",
            "time_norm": "time",
        }
    ).to_dict(orient="records")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    GA_DIR.mkdir(parents=True, exist_ok=True)

    template_df = load_cash3_cash4_template()
    eve_df_raw = load_cash3_evening_csv()

    c3_mid_df = filter_cash3_midday(template_df)
    c4_night_df = filter_cash4_night(template_df)
    c3_eve_df = filter_cash3_evening(eve_df_raw)

    print("\n[SUMMARY] Rows after filtering:")
    print(f"  Cash3 Midday rows : {len(c3_mid_df)}")
    print(f"  Cash3 Evening rows: {len(c3_eve_df)}")
    print(f"  Cash4 Night rows  : {len(c4_night_df)}")

    out_mid = GA_DIR / "cash3_midday.json"
    out_eve = GA_DIR / "cash3_evening.json"
    out_c4n = GA_DIR / "cash4_night.json"

    with out_mid.open("w", encoding="utf-8") as f:
        json.dump(df_to_json_records(c3_mid_df), f, indent=2)

    with out_eve.open("w", encoding="utf-8") as f:
        json.dump(df_to_json_records(c3_eve_df), f, indent=2)

    with out_c4n.open("w", encoding="utf-8") as f:
        json.dump(df_to_json_records(c4_night_df), f, indent=2)

    print("\n[WRITE] GA JSON exports complete:")
    print(f"  -> {out_mid}")
    print(f"  -> {out_eve}")
    print(f"  -> {out_c4n}")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
