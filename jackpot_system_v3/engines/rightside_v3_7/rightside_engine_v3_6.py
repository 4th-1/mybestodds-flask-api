#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
rightside_engine_v3_6.py

Right-side Smart Logic engine for My Best Odds v3.6
Applies to:
    - Mega Millions
    - Powerball
    - Cash4Life

Responsibilities:
- Consume 50-draw feature context from jackpot_ingest_v3_6
- Compute v3.6 jackpot confidence scores
- Decide Play / Play High / Skip for each upcoming draw
- Generate ranked picks (1 for BOSK/BOOK, up to 3 for BOOK3)
- Emit JSON-ready dicts that match the v3.6 schema

v3.7 EXPORT GUARANTEE (CRITICAL):
- Every emitted row MUST include:
    row["number"] = "05-12-23-45-50 | Mega 10"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import hashlib
import json
import random

# -------------------------------------------------------------------------
# ✅ CORRECT RELATIVE IMPORT (FINAL FIX)
# -------------------------------------------------------------------------
from .jackpot_ingest_v3_6 import (
    JackpotHistoryConfig,
    build_feature_context,
    GameName,
)

KitType = Literal["BOSK", "BOOK", "BOOK3"]

# -------------------------------------------------------------------------
# Canonical ticket compositor (single source of truth for "number")
# -------------------------------------------------------------------------
def _format_whites(whites: List[int]) -> str:
    clean = [int(x) for x in (whites or [])]
    clean.sort()
    return "-".join(f"{n:02d}" for n in clean)

def _format_special(n: Optional[int]) -> str:
    if n is None:
        n = 0
    return f"{int(n):02d}"

def compose_ticket_string(
    game_name: str,
    white_balls: List[int],
    special_ball: Optional[int],
) -> str:
    whites_str = _format_whites(white_balls)
    special_str = _format_special(special_ball)

    g = (game_name or "").lower().strip()
    if g == "megamillions":
        label = "Mega"
    elif g == "powerball":
        label = "PB"
    elif g == "cash4life":
        label = "CB"
    else:
        label = "Ball"

    return f"{whites_str} | {label} {special_str}"


# -------------------------------------------------------------------------
# Engine
# -------------------------------------------------------------------------
@dataclass
class JackpotEngineV36:
    game: GameName
    kit_type: KitType
    context: Dict[str, Any]
    subscriber_seed: int = 0  # ✅ deterministic subscriber variation

    # ----------------------------
    # Subscriber seed + per-day RNG
    # ----------------------------
    def _seed_from_subscriber(self, subscriber: Optional[Dict[str, Any]]) -> int:
        if not subscriber:
            return 0
        base = json.dumps(subscriber, sort_keys=True, default=str)
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return int(h[:12], 16)

    def _daily_rng(self, d: date) -> random.Random:
        # stable per-subscriber, per-day (no nondeterministic randomness)
        day_key = int(d.strftime("%Y%m%d"))
        return random.Random(self.subscriber_seed ^ day_key)

    # ----------------------------
    # Optional history pool (if ingest exposes raw draw df)
    # ----------------------------
    def _history_combo_pool(self) -> List[Dict[str, Any]]:
        """
        Try to pull real historical draw combos from context (if ingest provided it).
        Falls back cleanly if not present.
        """
        df = (
            self.context.get("history_df")
            or self.context.get("history")
            or self.context.get("draws_df")
            or self.context.get("draws")
        )
        if df is None or getattr(df, "empty", True):
            return []

        # expected cols: n1..n5 and one bonus-like col
        cols_main = ["n1", "n2", "n3", "n4", "n5"]
        if not all(c in df.columns for c in cols_main):
            return []

        bonus_col = None
        for candidate in ("bonus", "mega_ball", "powerball", "life_ball", "mb", "pb", "cb"):
            if candidate in df.columns:
                bonus_col = candidate
                break
        if bonus_col is None:
            return []

        tail = df.tail(200)

        pool: List[Dict[str, Any]] = []
        for _, row in tail.iterrows():
            try:
                whites = [int(row[c]) for c in cols_main]
                bonus = int(row[bonus_col])
                pool.append({"main_numbers": whites, "bonus": bonus})
            except Exception:
                continue

        # de-dupe
        seen = set()
        out: List[Dict[str, Any]] = []
        for c in pool:
            key = (tuple(sorted(c["main_numbers"])), int(c["bonus"]))
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    # ----------------------------
    # Confidence + play flag logic
    # ----------------------------
    def _confidence_from_features(self, row: pd.Series) -> float:
        cycle = row.get("cycle_score", 0.5)
        pattern = row.get("pattern_score", 0.5)
        bonus = row.get("bonus_cluster_score", 0.5)
        hotcold = row.get("hot_cold_score", 0.5)
        overdue = row.get("overdue_score", 0.5)

        conf = (
            0.40 * cycle +
            0.20 * pattern +
            0.20 * bonus +
            0.10 * hotcold +
            0.10 * overdue
        )
        return float(np.clip(conf, 0.10, 0.90))

    def _play_flag(self, confidence: float, cycle_score: float, bonus_score: float) -> str:
        if confidence >= 0.70 and cycle_score >= 0.65 and bonus_score >= 0.60:
            return "Play High"
        if confidence >= 0.45 or bonus_score >= 0.50:
            return "Play"
        return "Skip"

    def _num_picks_for_kit(self) -> int:
        if self.kit_type in ("BOSK", "BOOK"):
            return 1
        if self.kit_type == "BOOK3":
            return 3
        return 1

    # ----------------------------
    # Candidate combos (history-first, else static fallback)
    # ----------------------------
    def _generate_candidate_combos(self, rng: Optional[random.Random] = None) -> List[Dict[str, Any]]:
        rng = rng or random.Random(0)

        hist_pool = self._history_combo_pool()
        if hist_pool:
            rng.shuffle(hist_pool)
            return hist_pool

        if self.game == "megamillions":
            base = [
                {"main_numbers": [3, 18, 24, 41, 55], "bonus": 10},
                {"main_numbers": [7, 19, 30, 44, 61], "bonus": 4},
                {"main_numbers": [2, 11, 25, 40, 67], "bonus": 12},
            ]
            rng.shuffle(base)
            return base

        if self.game == "powerball":
            base = [
                {"main_numbers": [6, 13, 29, 48, 58], "bonus": 11},
                {"main_numbers": [9, 21, 33, 52, 60], "bonus": 5},
                {"main_numbers": [4, 17, 28, 39, 62], "bonus": 22},
            ]
            rng.shuffle(base)
            return base

        if self.game == "cash4life":
            base = [
                {"main_numbers": [5, 14, 26, 31, 54], "bonus": 3},
                {"main_numbers": [8, 16, 27, 32, 48], "bonus": 1},
                {"main_numbers": [9, 18, 24, 37, 56], "bonus": 4},
            ]
            rng.shuffle(base)
            return base

        return []

    # ----------------------------
    # Public API
    # ----------------------------
    def generate_picks_for_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        features_50 = self.context["features_50"]
        results: List[Dict[str, Any]] = []

        current = start_date
        while current <= end_date:
            # NOTE: This still uses the latest 50-draw feature row (existing design).
            last = features_50.iloc[-1]

            confidence = self._confidence_from_features(last)

            play = self._play_flag(
                confidence,
                float(last.get("cycle_score", 0.5)),
                float(last.get("bonus_cluster_score", 0.5)),
            )

            rng = self._daily_rng(current)
            combos = self._generate_candidate_combos(rng=rng)[: self._num_picks_for_kit()]

            for rank, combo in enumerate(combos, start=1):
                whites = combo["main_numbers"]
                special = combo["bonus"]

                results.append({
                    "game": self.game,
                    "date": current.isoformat(),
                    "rank": rank,
                    "number": compose_ticket_string(self.game, whites, special),  # ✅ guaranteed
                    "confidence": round(float(confidence), 2),
                    "play_flag": play,
                })

            current += timedelta(days=1)

        return results


# -------------------------------------------------------------------------
# Factory
# -------------------------------------------------------------------------
def build_engine_for_game(
    game: GameName,
    kit_type: KitType,
    history_csv: str,
    subscriber: Optional[Dict[str, Any]] = None,
) -> JackpotEngineV36:

    cfg = JackpotHistoryConfig(game=game, csv_path=Path(history_csv))
    ctx = build_feature_context(cfg)

    engine = JackpotEngineV36(
        game=game,
        kit_type=kit_type,
        context=ctx,
    )

    # 🔑 CRITICAL: bind subscriber seed
    engine.subscriber_seed = _seed_from_subscriber(subscriber)

    return engine
