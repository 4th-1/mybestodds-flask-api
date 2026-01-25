"""
rightside_engine_v3_6.py

Right-side Smart Logic engine for My Best Odds v3.6
Applies to:
    - Mega Millions
    - Powerball
    - Cash4Life
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# AUTO-DISCOVER jackpot_ingest_v3_6.py (NO PATH ASSUMPTIONS)
# ---------------------------------------------------------------------
import sys
from pathlib import Path
import importlib.util

THIS_FILE = Path(__file__).resolve()

def load_jackpot_ingest():
    """
    Walk upward from this file and locate jackpot_ingest_v3_6.py anywhere
    in the project tree. Load it by absolute path.
    """
    for root in THIS_FILE.parents:
        candidates = list(root.rglob("jackpot_ingest_v3_6.py"))
        if candidates:
            ingest_path = candidates[0]
            spec = importlib.util.spec_from_file_location(
                "jackpot_ingest_v3_6",
                ingest_path,
            )
            module = importlib.util.module_from_spec(spec)
            
            # ✅ THE FIX: Register in sys.modules BEFORE executing
            # This prevents the "NoneType has no attribute __dict__" error
            # when dataclasses inside the module try to resolve themselves.
            sys.modules["jackpot_ingest_v3_6"] = module
            
            spec.loader.exec_module(module)
            return module, ingest_path

    raise RuntimeError(
        "jackpot_ingest_v3_6.py not found anywhere above project root"
    )

jackpot_ingest, INGEST_PATH = load_jackpot_ingest()

JackpotHistoryConfig = jackpot_ingest.JackpotHistoryConfig
build_feature_context = jackpot_ingest.build_feature_context
GameName = jackpot_ingest.GameName

# ---------------------------------------------------------------------
# Standard imports
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional
from datetime import date, timedelta

import numpy as np
import pandas as pd

KitType = Literal["BOSK", "BOOK", "BOOK3"]

# ---------------------------------------------------------------------
# Canonical ticket compositor
# ---------------------------------------------------------------------
def _format_whites(whites: List[int]) -> str:
    return "-".join(f"{int(n):02d}" for n in sorted(whites or []))


def _format_special(n: Optional[int]) -> str:
    return f"{int(n or 0):02d}"


def compose_ticket_string(game: str, whites: List[int], bonus: Optional[int]) -> str:
    g = (game or "").lower()
    label = "Mega" if g == "megamillions" else "PB" if g == "powerball" else "CB"
    return f"{_format_whites(whites)} | {label} {_format_special(bonus)}"

# ---------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------
@dataclass
class JackpotEngineV36:
    game: GameName
    kit_type: KitType
    context: Dict[str, Any]

    def _confidence_from_features(self, row: pd.Series) -> float:
        conf = (
            0.40 * row.get("cycle_score", 0.5)
            + 0.20 * row.get("pattern_score", 0.5)
            + 0.20 * row.get("bonus_cluster_score", 0.5)
            + 0.10 * row.get("hot_cold_score", 0.5)
            + 0.10 * row.get("overdue_score", 0.5)
        )
        return float(np.clip(conf, 0.10, 0.90))

    def _num_picks_for_kit(self) -> int:
        return 3 if self.kit_type == "BOOK3" else 1

    def _generate_candidate_combos(self) -> List[Dict[str, Any]]:
        if self.game == "megamillions":
            return [{"main_numbers": [3, 18, 24, 41, 55], "bonus": 10}]
        if self.game == "powerball":
            return [{"main_numbers": [6, 13, 29, 48, 58], "bonus": 11}]
        if self.game == "cash4life":
            return [{"main_numbers": [5, 14, 26, 31, 54], "bonus": 3}]
        return []

    def generate_picks_for_range(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        features = self.context["features_50"]
        results: List[Dict[str, Any]] = []

        current = start_date
        while current <= end_date:
            row = features.iloc[-1]
            confidence = self._confidence_from_features(row)

            for rank, combo in enumerate(
                self._generate_candidate_combos()[: self._num_picks_for_kit()],
                start=1,
            ):
                results.append(
                    {
                        "game": self.game,
                        "date": current.isoformat(),
                        "rank": rank,
                        "number": compose_ticket_string(
                            self.game,
                            combo["main_numbers"],
                            combo["bonus"],
                        ),
                        "confidence": round(confidence, 2),
                        "main_numbers": combo["main_numbers"],
                        "bonus_ball": combo["bonus"],
                    }
                )

            current += timedelta(days=1)

        return results

# ---------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------
def build_engine_for_game(
    game: GameName,
    kit_type: KitType,
    history_csv: str,
) -> JackpotEngineV36:
    cfg = JackpotHistoryConfig(game=game, csv_path=Path(history_csv))
    ctx = build_feature_context(cfg)
    return JackpotEngineV36(game=game, kit_type=kit_type, context=ctx)