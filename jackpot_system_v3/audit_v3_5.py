"""
audit_v3_5.py

My Best Odds / SMART LOGIC V3.5
--------------------------------
Audit engine for BOSK / BOOK / BOOK3 kits.

Uses:
  - data/tracking/<KIT>_tracking_v3_5.csv   (from tracking_v3_5.py)
  - data/ga_results/*                       (GA result files you maintain)

Produces:
  - outputs/<KIT>_audit_v3_5.xlsx           (multi-sheet audit workbook)

What it measures:
  - Overall hit rate
  - Hit rate by game
  - Hit rate by confidence band (🟩/🟨/🤎/🚫)
  - Hit rate by session (Cash3/Cash4 Midday/Evening/Night)
  - Hit rate by lane (P_A, P_B, etc.) via lane_sources
  - Jackpot match breakdown (jackpot_full, match_5, match_4, etc.)
  - Near misses (2-of-3 for Cash3, 3-of-4 for Cash4)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import pandas as pd

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]

TRACKING_ROOT = Path("data") / "tracking"
GA_RESULTS_ROOT = Path("data") / "ga_results"
OUTPUT_ROOT = Path("outputs")


# =========================
# Data structures
# =========================

@dataclass
class TrackingRow:
    timestamp_generated: str
    kit: KitType
    subscriber_id: str
    game: GameType
    draw_date: str      # YYYY-MM-DD
    session: str        # "", Midday, Evening, Night
    pick_type: str      # "pick" or "jackpot"
    value: str          # "123" for pick games
    main_balls: List[int]
    bonus_balls: List[int]
    confidence: float
    best_odds: str
    confidence_band: str
    lane_sources: List[str]


@dataclass
class ResultRow:
    game: GameType
    draw_date: str      # YYYY-MM-DD
    session: str        # "", Midday, Evening, Night
    main_balls: List[int]
    bonus_balls: List[int]
    value: str          # for Cash3/Cash4, the 3/4-digit result string


# =========================
# Load tracking
# =========================

def _tracking_path_for_kit(kit: KitType) -> Path:
    return TRACKING_ROOT / f"{kit}_tracking_v3_5.csv"


def _load_tracking_rows(kit: KitType) -> List[TrackingRow]:
    path = _tracking_path_for_kit(kit)
    if not path.exists():
        raise FileNotFoundError(f"Tracking file not found for {kit}: {path}")

    rows: List[TrackingRow] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            main = [int(x) for x in r["main_balls"].split() if x.strip().isdigit()]
            bonus = [int(x) for x in r["bonus_balls"].split() if x.strip().isdigit()]
            lanes = [x for x in r["lane_sources"].split("|") if x]

            rows.append(
                TrackingRow(
                    timestamp_generated=r["timestamp_generated"],
                    kit=r["kit"],  # type: ignore
                    subscriber_id=r["subscriber_id"],
                    game=r["game"],  # type: ignore
                    draw_date=r["draw_date"],
                    session=r["session"],
                    pick_type=r["pick_type"],
                    value=r["value"],
                    main_balls=main,
                    bonus_balls=bonus,
                    confidence=float(r["confidence"]) if r["confidence"] else 0.0,
                    best_odds=r["best_odds"],
                    confidence_band=r["confidence_band"],
                    lane_sources=lanes,
                )
            )
    return rows


# =========================
# Load GA results
# =========================

def _standardize_date_str(raw: Any) -> str:
    """
    Convert GA 'Draw Date' into ISO YYYY-MM-DD.
    Handles strings like '9/1/2025' or datetime-like values.
    """
    # Use pandas for flexible parsing
    ts = pd.to_datetime(raw)
    return ts.strftime("%Y-%m-%d")


def _load_cash3_results() -> List[ResultRow]:
    """
    Combines:
      - Cash 3 Midday & Night from CSV
      - Cash 3 Evening from separate CSV
    """
    rows: List[ResultRow] = []

    # Midday & Night
    path_midnight = GA_RESULTS_ROOT / "Cash 3 Midday_Night.csv"
    if path_midnight.exists():
        df = pd.read_csv(path_midnight)
        for _, r in df.dropna(subset=["Game", "Draw Date", "Time"]).iterrows():
            game = str(r["Game"]).strip()
            if "Cash" not in game:
                continue
            g: GameType = "Cash3"  # type: ignore

            draw_date = _standardize_date_str(r["Draw Date"])
            session = str(r["Time"]).strip()  # Midday or Night
            # Winning Numbers may be float (e.g., 700.0)
            wn = r["Winning Numbers"]
            if pd.isna(wn):
                continue
            try:
                num_int = int(float(wn))
                value = f"{num_int:03d}"
            except Exception:
                value = str(wn).strip()

            rows.append(
                ResultRow(
                    game=g,
                    draw_date=draw_date,
                    session=session,
                    main_balls=[],
                    bonus_balls=[],
                    value=value,
                )
            )

    # Evening
    path_evening = GA_RESULTS_ROOT / "Cash3 Evening 901-1110 (1).csv"
    if path_evening.exists():
        df2 = pd.read_csv(path_evening)
        for _, r in df2.dropna(subset=["Game", "Draw Date", "Time"]).iterrows():
            game = str(r["Game"]).strip()
            if "Cash" not in game:
                continue
            g: GameType = "Cash3"  # type: ignore

            draw_date = _standardize_date_str(r["Draw Date"])
            session = str(r["Time"]).strip()  # Evening
            wn = r["Winning Numbers"]
            if pd.isna(wn):
                continue
            try:
                num_int = int(float(wn))
                value = f"{num_int:03d}"
            except Exception:
                value = str(wn).strip()

            rows.append(
                ResultRow(
                    game=g,
                    draw_date=draw_date,
                    session=session,
                    main_balls=[],
                    bonus_balls=[],
                    value=value,
                )
            )

    return rows


def _load_cash4_results() -> List[ResultRow]:
    """
    Placeholder: adapt when you add your Cash4 GA CSV/XLSX.

    For now, returns an empty list so audits won't break if
    Cash 4 files aren't present yet.
    """
    return []


def _load_jackpot_results_from_excel(fname: str, game_name: GameType) -> List[ResultRow]:
    """
    Generic loader for:
      - Mega Millions 9-10-25 - 11-10-25.xlsx
      - Powerball.xlsx
      - Cash4Life 9-01-2025-11-10-25.xlsx
    With columns:
      Game, Draw Date, Winning Numbers, Cash Ball
    """
    rows: List[ResultRow] = []
    path = GA_RESULTS_ROOT / fname
    if not path.exists():
        return rows

    xls = pd.ExcelFile(path)
    df = xls.parse(xls.sheet_names[0])

    for _, r in df.dropna(subset=["Game", "Draw Date"]).iterrows():
        game = str(r["Game"]).strip()
        if game_name == "MegaMillions" and "Mega" not in game:
            continue
        if game_name == "Powerball" and "Power" not in game:
            continue
        if game_name == "Cash4Life" and "Cash4Life" not in game:
            continue

        draw_date = _standardize_date_str(r["Draw Date"])
        session = ""  # jackpots have no session

        wn = str(r["Winning Numbers"]).replace(",", " ").strip()
        main_balls = [int(x) for x in wn.split() if x.strip().isdigit()]

        bonus = r.get("Cash Ball", "")
        bonus_balls: List[int] = []
        if pd.notna(bonus):
            try:
                bonus_balls = [int(bonus)]
            except Exception:
                pass

        rows.append(
            ResultRow(
                game=game_name,
                draw_date=draw_date,
                session=session,
                main_balls=main_balls,
                bonus_balls=bonus_balls,
                value="",
            )
        )

    return rows


def _load_all_results() -> Dict[Tuple[GameType, str, str], ResultRow]:
    """
    Index results by key: (game, draw_date, session)
    For jackpots, session = "".
    """
    result_index: Dict[Tuple[GameType, str, str], ResultRow] = {}

    # Cash3
    for r in _load_cash3_results():
        key = (r.game, r.draw_date, r.session)
        result_index[key] = r

    # Cash4 (placeholder: none yet)
    for r in _load_cash4_results():
        key = (r.game, r.draw_date, r.session)
        result_index[key] = r

    # Mega Millions
    for r in _load_jackpot_results_from_excel(
        "Mega Millions 9-10-25 - 11-10-25.xlsx", "MegaMillions"
    ):
        key = (r.game, r.draw_date, "")
        result_index[key] = r

    # Powerball
    for r in _load_jackpot_results_from_excel(
        "Powerball.xlsx", "Powerball"
    ):
        key = (r.game, r.draw_date, "")
        result_index[key] = r

    # Cash4Life
    for r in _load_jackpot_results_from_excel(
        "Cash4Life 9-01-2025-11-10-25.xlsx", "Cash4Life"
    ):
        key = (r.game, r.draw_date, "")
        result_index[key] = r

    return result_index


# =========================
# Hit classification
# =========================

def _classify_pick_hit(tr: TrackingRow, rr: Optional[ResultRow]) -> Optional[str]:
    if rr is None:
        return None

    if not tr.value or not rr.value:
        return None

    # Straight
    if tr.value == rr.value:
        return "straight"

    # Box: same digits, any order
    t_digits = sorted(int(ch) for ch in tr.value if ch.isdigit())
    r_digits = sorted(int(ch) for ch in rr.value if ch.isdigit())
    if len(t_digits) == len(r_digits) and t_digits == r_digits:
        return "box"

    # Near misses (2-of-3 or 3-of-4)
    overlap = sum(1 for d in t_digits if d in r_digits)
    if len(t_digits) == 3 and overlap == 2:
        return "near_miss_2of3"
    if len(t_digits) == 4 and overlap == 3:
        return "near_miss_3of4"

    return None


def _classify_jackpot_hit(tr: TrackingRow, rr: Optional[ResultRow]) -> Optional[str]:
    if rr is None:
        return None

    t_main = set(tr.main_balls)
    r_main = set(rr.main_balls)
    t_bonus = set(tr.bonus_balls)
    r_bonus = set(rr.bonus_balls)

    main_matches = len(t_main & r_main)
    bonus_matches = len(t_bonus & r_bonus)

    if not rr.main_balls:
        return None

    # Simple matrix
    if main_matches == len(r_main) and (not r_bonus or bonus_matches == len(r_bonus)):
        return "jackpot_full"
    if main_matches == len(r_main) and bonus_matches == 0:
        return "match_all_main"
    if main_matches == 5:
        return "match_5"
    if main_matches == 4 and bonus_matches >= 1:
        return "match_4_plus_bonus"
    if main_matches == 4:
        return "match_4"
    if main_matches == 3 and bonus_matches >= 1:
        return "match_3_plus_bonus"
    if main_matches == 3:
        return "match_3"
    if main_matches == 2 and bonus_matches >= 1:
        return "match_2_plus_bonus"
    if bonus_matches >= 1 and main_matches == 0:
        return "bonus_only"

    return None


# =========================
# Main audit logic
# =========================

def run_audit(kit: KitType) -> None:
    tracking_rows = _load_tracking_rows(kit)
    result_index = _load_all_results()

    # Build base DataFrame from tracking
    base_records: List[Dict[str, Any]] = []

    for tr in tracking_rows:
        key = (tr.game, tr.draw_date, tr.session if tr.session else "")
        rr = result_index.get(key)

        if tr.game in ("Cash3", "Cash4"):
            hit_type = _classify_pick_hit(tr, rr)
        else:
            hit_type = _classify_jackpot_hit(tr, rr)

        hit_flag = hit_type is not None

        base_records.append(
            {
                "kit": tr.kit,
                "subscriber_id": tr.subscriber_id,
                "game": tr.game,
                "draw_date": tr.draw_date,
                "session": tr.session,
                "pick_type": tr.pick_type,
                "value": tr.value,
                "main_balls": " ".join(str(x) for x in tr.main_balls),
                "bonus_balls": " ".join(str(x) for x in tr.bonus_balls),
                "confidence": tr.confidence,
                "best_odds": tr.best_odds,
                "confidence_band": tr.confidence_band,
                "lane_sources": "|".join(tr.lane_sources),
                "hit_flag": hit_flag,
                "hit_type": hit_type or "",
            }
        )

    if not base_records:
        print(f"[AUDIT] No tracking records for {kit}. Nothing to audit.")
        return

    df = pd.DataFrame(base_records)

    # ---------- Sheet 1: Summary ----------
    # Overall and by game
    summary_rows: List[Dict[str, Any]] = []

    total_picks = len(df)
    total_hits = int(df["hit_flag"].sum())
    summary_rows.append(
        {
            "scope": "ALL",
            "game": "ALL",
            "picks": total_picks,
            "hits": total_hits,
            "hit_rate": total_hits / total_picks if total_picks else 0.0,
        }
    )

    for game, gdf in df.groupby("game"):
        gpicks = len(gdf)
        ghits = int(gdf["hit_flag"].sum())
        summary_rows.append(
            {
                "scope": "GAME",
                "game": game,
                "picks": gpicks,
                "hits": ghits,
                "hit_rate": ghits / gpicks if gpicks else 0.0,
            }
        )

    summary_df = pd.DataFrame(summary_rows)

    # ---------- Sheet 2: Confidence Bands ----------
    band_rows: List[Dict[str, Any]] = []
    for band, bdf in df.groupby("confidence_band"):
        bpicks = len(bdf)
        bhits = int(bdf["hit_flag"].sum())
        band_rows.append(
            {
                "confidence_band": band,
                "picks": bpicks,
                "hits": bhits,
                "hit_rate": bhits / bpicks if bpicks else 0.0,
                "avg_confidence": bdf["confidence"].mean() if bpicks else 0.0,
            }
        )
    bands_df = pd.DataFrame(band_rows)

    # ---------- Sheet 3: Session Performance (Cash3/Cash4 only) ----------
    pick_df = df[df["game"].isin(["Cash3", "Cash4"])].copy()
    session_rows: List[Dict[str, Any]] = []
    for (game, session), sdf in pick_df.groupby(["game", "session"]):
        spicks = len(sdf)
        shits = int(sdf["hit_flag"].sum())
        session_rows.append(
            {
                "game": game,
                "session": session,
                "picks": spicks,
                "hits": shits,
                "hit_rate": shits / spicks if spicks else 0.0,
            }
        )
    sessions_df = pd.DataFrame(session_rows)

    # ---------- Sheet 4: Lane Performance ----------
    lane_rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        lanes = [x for x in str(row["lane_sources"]).split("|") if x]
        for ln in lanes:
            lane_rows.append(
                {
                    "lane": ln,
                    "game": row["game"],
                    "hit_flag": row["hit_flag"],
                }
            )

    if lane_rows:
        lane_df = pd.DataFrame(lane_rows)
        lane_perf_rows: List[Dict[str, Any]] = []
        for lane, ldf in lane_df.groupby("lane"):
            lpicks = len(ldf)
            lhits = int(ldf["hit_flag"].sum())
            lane_perf_rows.append(
                {
                    "lane": lane,
                    "picks": lpicks,
                    "hits": lhits,
                    "hit_rate": lhits / lpicks if lpicks else 0.0,
                }
            )
        lanes_df = pd.DataFrame(lane_perf_rows)
    else:
        lanes_df = pd.DataFrame(columns=["lane", "picks", "hits", "hit_rate"])

    # ---------- Sheet 5: Jackpot Match Matrix ----------
    jackpot_df = df[df["game"].isin(["MegaMillions", "Powerball", "Cash4Life"])].copy()
    jm_rows: List[Dict[str, Any]] = []
    if not jackpot_df.empty:
        for hit_type, jdf in jackpot_df.groupby("hit_type"):
            jpicks = len(jdf)
            jm_rows.append(
                {
                    "hit_type": hit_type or "(none)",
                    "picks": jpicks,
                }
            )
    jackpot_matrix_df = pd.DataFrame(jm_rows)

    # ---------- Sheet 6: Near Misses ----------
    near_df = df[df["hit_type"].isin(["near_miss_2of3", "near_miss_3of4"])].copy()

    # =========================
    # Write Excel workbook
    # =========================
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_ROOT / f"{kit}_audit_v3_5.xlsx"

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="RawTracking+Hits")
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        bands_df.to_excel(writer, index=False, sheet_name="ConfidenceBands")
        sessions_df.to_excel(writer, index=False, sheet_name="Sessions")
        lanes_df.to_excel(writer, index=False, sheet_name="Lanes")
        jackpot_matrix_df.to_excel(writer, index=False, sheet_name="JackpotMatrix")
        near_df.to_excel(writer, index=False, sheet_name="NearMisses")

    print(f"[AUDIT] Completed for {kit}. Workbook: {out_path}")


def main(argv: List[str]) -> None:
    import sys
    if len(argv) < 2:
        print(
            "Usage:\n"
            "  python audit_v3_5.py KIT\n\n"
            "Example:\n"
            "  python audit_v3_5.py BOOK3\n"
        )
        sys.exit(1)

    kit_str = argv[1].upper()
    if kit_str not in ("BOSK", "BOOK", "BOOK3"):
        raise ValueError(f"Unknown kit: {kit_str}")
    kit: KitType = kit_str  # type: ignore

    run_audit(kit)


if __name__ == "__main__":
    import sys
    main(sys.argv)
