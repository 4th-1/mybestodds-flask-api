"""
run_kit_v3_5.py

My Best Odds / SMART LOGIC V3.5
--------------------------------
Main runner to generate BOSK / BOOK / BOOK3 kits
over a date range for one or many subscribers.

Usage (single subscriber):

  python run_kit_v3_5.py BOOK3 2025-12-01 2025-12-31 data/subscribers/BOOK3/JDS.json

Usage (entire folder):

  python run_kit_v3_5.py BOSK 2025-12-01 2025-12-31 data/subscribers/BOSK

If subscriber_path is omitted, defaults to:

  data/subscribers/<KIT>/
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pick_engine_v3_5 import generate_picks_for_day
from tracking_v3_5 import log_pick

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]


# Game/session configuration per kit
KIT_GAMES: Dict[KitType, List[GameType]] = {
    "BOSK": ["Cash3", "Cash4"],
    "BOOK": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
    "BOOK3": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
}

PICK_SESSIONS: List[SessionType] = ["Midday", "Evening", "Night"]


@dataclass
class ForecastRecord:
    kit: KitType
    subscriber_id: str
    game: GameType
    draw_date: str
    session: Optional[SessionType]
    pick_type: str  # "pick" or "jackpot"
    value: str
    main: List[int]
    bonus: List[int]
    confidence: float
    best_odds: str
    confidence_band: str
    lane_sources: List[str]


def _parse_date(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _date_range(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _load_subscriber(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _subscriber_id_from_json(sub: Dict[str, Any], fallback: str) -> str:
    # Try to read an explicit ID; else fallback to file stem
    return str(sub.get("id") or sub.get("subscriber_id") or fallback)


def _default_subscribers_path(kit: KitType) -> Path:
    return Path("data") / "subscribers" / kit


def _find_subscriber_files(path: Path) -> List[Path]:
    if path.is_file() and path.suffix.lower() == ".json":
        return [path]
    if path.is_dir():
        return sorted([p for p in path.glob("*.json") if p.is_file()])
    raise FileNotFoundError(f"Subscriber path not found: {path}")


def _output_root_for_run(kit: KitType, start: date, end: date) -> Path:
    folder = f"{kit}_V3_5_{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"
    root = Path("outputs") / folder
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_json_output(path: Path, records: List[ForecastRecord]) -> None:
    data = [asdict(r) for r in records]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _write_excel_output(path: Path, records: List[ForecastRecord]) -> None:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        print("[WARN] pandas not installed; skipping Excel export.")
        return

    rows = [asdict(r) for r in records]
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)


def run_kit_for_subscribers(
    kit: KitType,
    start_date: date,
    end_date: date,
    subscriber_paths: List[Path],
) -> None:
    games = KIT_GAMES[kit]
    output_root = _output_root_for_run(kit, start_date, end_date)

    for sub_path in subscriber_paths:
        print(f"[RUN] {kit} – {sub_path.name} – {start_date} to {end_date}")
        subscriber_json = _load_subscriber(sub_path)
        subscriber_id = _subscriber_id_from_json(subscriber_json, sub_path.stem)

        all_records: List[ForecastRecord] = []

        for d in _date_range(start_date, end_date):
            for game in games:
                is_pick_game = game in ("Cash3", "Cash4")

                if is_pick_game:
                    for session in PICK_SESSIONS:
                        engine_out = generate_picks_for_day(
                            kit=kit,
                            game=game,
                            draw_date=d,
                            session=session,
                            subscriber=subscriber_json,
                        )
                        final_picks = engine_out["final"]

                        for fp in final_picks:
                            rec = ForecastRecord(
                                kit=kit,
                                subscriber_id=subscriber_id,
                                game=game,
                                draw_date=d.strftime("%Y-%m-%d"),
                                session=session,
                                pick_type="pick",
                                value=fp.value,
                                main=[],
                                bonus=[],
                                confidence=fp.confidence,
                                best_odds=fp.best_odds,
                                confidence_band=fp.confidence_band,
                                lane_sources=fp.lane_sources,
                            )
                            all_records.append(rec)

                            log_pick(
                                kit=kit,
                                subscriber_id=subscriber_id,
                                game=game,
                                draw_date=d,
                                session=session,
                                pick_type="pick",
                                value=fp.value,
                                main_balls=[],
                                bonus_balls=[],
                                confidence=fp.confidence,
                                best_odds=fp.best_odds,
                                confidence_band=fp.confidence_band,
                                lane_sources=fp.lane_sources,
                            )
                else:
                    # Jackpot games: no session
                    engine_out = generate_picks_for_day(
                        kit=kit,
                        game=game,
                        draw_date=d,
                        session=None,
                        subscriber=subscriber_json,
                    )
                    final_picks = engine_out["final"]

                    for fp in final_picks:
                        rec = ForecastRecord(
                            kit=kit,
                            subscriber_id=subscriber_id,
                            game=game,
                            draw_date=d.strftime("%Y-%m-%d"),
                            session=None,
                            pick_type="jackpot",
                            value="",
                            main=fp.main,
                            bonus=fp.bonus,
                            confidence=fp.confidence,
                            best_odds=fp.best_odds,
                            confidence_band=fp.confidence_band,
                            lane_sources=fp.lane_sources,
                        )
                        all_records.append(rec)

                        log_pick(
                            kit=kit,
                            subscriber_id=subscriber_id,
                            game=game,
                            draw_date=d,
                            session=None,
                            pick_type="jackpot",
                            value="",
                            main_balls=fp.main,
                            bonus_balls=fp.bonus,
                            confidence=fp.confidence,
                            best_odds=fp.best_odds,
                            confidence_band=fp.confidence_band,
                            lane_sources=fp.lane_sources,
                        )

        # Write outputs per subscriber
        json_path = output_root / f"{kit}_{subscriber_id}_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.json"
        xlsx_path = output_root / f"{kit}_{subscriber_id}_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.xlsx"

        _write_json_output(json_path, all_records)
        _write_excel_output(xlsx_path, all_records)

        print(f"[DONE] Wrote {len(all_records)} forecasts for {subscriber_id}")
        print(f"       JSON:  {json_path}")
        print(f"       Excel: {xlsx_path}")


def main(argv: List[str]) -> None:
    if len(argv) < 4:
        print(
            "Usage:\n"
            "  python run_kit_v3_5.py KIT START_DATE END_DATE [SUBSCRIBER_PATH]\n\n"
            "Examples:\n"
            "  python run_kit_v3_5.py BOSK 2025-12-01 2025-12-31\n"
            "  python run_kit_v3_5.py BOOK3 2025-12-01 2025-12-31 data/subscribers/BOOK3/JDS.json\n"
            "  python run_kit_v3_5.py BOOK 2025-12-01 2025-12-31 data/subscribers/BOOK\n"
        )
        sys.exit(1)

    kit_str = argv[1].upper()
    if kit_str not in ("BOSK", "BOOK", "BOOK3"):
        raise ValueError(f"Unknown kit: {kit_str}")
    kit: KitType = kit_str  # type: ignore

    start_date = _parse_date(argv[2])
    end_date = _parse_date(argv[3])

    if len(argv) >= 5:
        raw_path = Path(argv[4])
        subscriber_paths = _find_subscriber_files(raw_path)
    else:
        default_path = _default_subscribers_path(kit)
        subscriber_paths = _find_subscriber_files(default_path)

    run_kit_for_subscribers(kit, start_date, end_date, subscriber_paths)


if __name__ == "__main__":
    main(sys.argv)
