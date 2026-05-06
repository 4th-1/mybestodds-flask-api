#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
jackpot_secondary_optimizer.py
==============================
Secondary prize optimizer for Powerball, MegaMillions, and Millionaire For Life.

ISOLATED from Cash3 EV system.  Does NOT share state with:
  ev_reranker.py, settle_ev_log.py, production_strategy.py, reranker_config.py

Purpose
-------
All valid lottery combinations carry identical jackpot odds — that is
a fixed property of the game rules.  What CAN be influenced:

  1. Field coverage     — spread numbers across the full range to increase the
                          probability of partial matches at the 3- and 4-ball tiers.
  2. Popular avoidance  — avoid heavily-played clusters (birthdays 1-31, round
                          multiples of 5/10) to reduce split-prize risk when a
                          secondary tier IS hit.
  3. Bonus quality      — avoid commonly played bonus balls to further reduce splits.
  4. Secondary prize EV — expected $ per $1 ticket from non-jackpot tiers.
                          This is a game constant (same for every valid combination).

Score weights
-------------
  field_coverage    0.40
  popular_avoidance 0.45
  bonus_avoidance   0.15

Grade thresholds: A ≥ 0.75 | B ≥ 0.60 | C ≥ 0.45 | D < 0.45

CLI
---
  python jackpot_secondary_optimizer.py
  python jackpot_secondary_optimizer.py --game MegaMillions
  python jackpot_secondary_optimizer.py --game Powerball --main 6 13 29 48 58 --bonus 11
  python jackpot_secondary_optimizer.py --game "Millionaire For Life" --main 5 14 26 31 54 --bonus 3
  python jackpot_secondary_optimizer.py --audit        # historical data quality audit
  python jackpot_secondary_optimizer.py --all          # all three games
  python jackpot_secondary_optimizer.py --prizes       # prize tier tables with odds
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Game configurations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GameConfig:
    name: str
    main_min: int
    main_max: int
    main_count: int
    bonus_min: int
    bonus_max: int
    bonus_count: int
    ticket_price: float        # cost per play in dollars
    # (main_matches, bonus_matches) -> (label, prize_dollars); jackpot prize = 0
    prizes: Dict[Tuple[int, int], Tuple[str, int]]
    data_file: str  # filename in data/results/jackpot_results/


GAME_CONFIGS: Dict[str, GameConfig] = {
    "MegaMillions": GameConfig(
        name="MegaMillions",
        main_min=1, main_max=70, main_count=5,
        bonus_min=1, bonus_max=25, bonus_count=1,
        ticket_price=5.00,
        prizes={
            (5, 1): ("JACKPOT",        0),
            (5, 0): ("5+0",    1_000_000),
            (4, 1): ("4+MB",      10_000),
            (4, 0): ("4+0",           500),
            (3, 1): ("3+MB",          200),
            (3, 0): ("3+0",            10),
            (2, 1): ("2+MB",           10),
            (1, 1): ("1+MB",            4),
            (0, 1): ("0+MB",           2),
        },
        data_file="MegaMillions.csv",
    ),
    "Powerball": GameConfig(
        name="Powerball",
        main_min=1, main_max=69, main_count=5,
        bonus_min=1, bonus_max=26, bonus_count=1,
        ticket_price=2.00,
        prizes={
            (5, 1): ("JACKPOT",        0),
            (5, 0): ("5+0",    1_000_000),
            (4, 1): ("4+PB",      50_000),
            (4, 0): ("4+0",          100),
            (3, 1): ("3+PB",         100),
            (3, 0): ("3+0",            7),
            (2, 1): ("2+PB",           7),
            (1, 1): ("1+PB",           4),
            (0, 1): ("0+PB",           4),
        },
        data_file="Powerball.csv",
    ),
    "Millionaire For Life": GameConfig(
        name="Millionaire For Life",
        main_min=1, main_max=60, main_count=5,
        bonus_min=1, bonus_max=4, bonus_count=1,
        ticket_price=5.00,
        prizes={
            (5, 1): ("JACKPOT",        0),
            (5, 0): ("5+0",       25_000),
            (4, 1): ("4+MB",       2_500),
            (4, 0): ("4+0",           500),
            (3, 1): ("3+MB",           50),
            (3, 0): ("3+0",            10),
            (2, 1): ("2+MB",            5),
            (1, 1): ("1+MB",            2),
            (0, 1): ("0+MB",            1),
        },
        data_file="Cash4Life.csv",  # historical file still uses legacy name
    ),
}

# Flexible aliases for CLI input
_GAME_ALIASES: Dict[str, str] = {
    "megamillions":         "MegaMillions",
    "mega millions":        "MegaMillions",
    "mega":                 "MegaMillions",
    "mm":                   "MegaMillions",
    "powerball":            "Powerball",
    "pb":                   "Powerball",
    "millionaireforlife":   "Millionaire For Life",
    "millionaire for life": "Millionaire For Life",
    "m4l":                  "Millionaire For Life",
    "mfl":                  "Millionaire For Life",
    "cash4life":            "Millionaire For Life",
    "c4l":                  "Millionaire For Life",
}

_DATA_ROOT = (
    Path(__file__).parent
    / "jackpot_system_v3"
    / "data"
    / "results"
    / "jackpot_results"
)


def resolve_game(name: str) -> Optional[str]:
    """Resolve a free-form game name to its canonical config key."""
    if name in GAME_CONFIGS:
        return name
    return _GAME_ALIASES.get(name.lower().strip())


# ---------------------------------------------------------------------------
# Secondary prize EV (game constant — same for every valid combination)
# ---------------------------------------------------------------------------

def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def secondary_prize_ev(cfg: GameConfig) -> float:
    """
    Expected non-jackpot prize value per $1 ticket.
    Jackpot tier (5+bonus) is excluded.
    Uses exact hypergeometric probability for main ball matches combined
    with uniform bonus ball probability.
    """
    M = cfg.main_max - cfg.main_min + 1   # main pool size
    K = cfg.main_count                     # balls drawn per game
    B = cfg.bonus_max - cfg.bonus_min + 1  # bonus pool size
    total_main_combos = _comb(M, K)

    ev = 0.0
    for (main_k, bonus_b), (label, prize) in cfg.prizes.items():
        if label == "JACKPOT" or prize == 0:
            continue
        p_main = _comb(K, main_k) * _comb(M - K, K - main_k) / total_main_combos
        p_bonus = 1.0 / B if bonus_b == 1 else (B - 1) / B
        ev += p_main * p_bonus * prize

    return round(ev, 6)


def prize_tier_probabilities(cfg: GameConfig) -> List[Dict]:
    """Return all tiers with exact odds and EV contribution, sorted by prize descending."""
    M = cfg.main_max - cfg.main_min + 1
    K = cfg.main_count
    B = cfg.bonus_max - cfg.bonus_min + 1
    total_main_combos = _comb(M, K)

    tiers = []
    for (main_k, bonus_b), (label, prize) in sorted(
        cfg.prizes.items(), key=lambda x: x[1][1], reverse=True
    ):
        p_main = _comb(K, main_k) * _comb(M - K, K - main_k) / total_main_combos
        p_bonus = 1.0 / B if bonus_b == 1 else (B - 1) / B
        prob = p_main * p_bonus
        contrib = prob * prize
        odds_str = f"1 in {int(round(1 / prob)):,}" if prob > 0 else "N/A"
        tiers.append({
            "tier": label,
            "prize": prize,
            "probability": prob,
            "odds": odds_str,
            "ev_contribution": round(contrib, 6),
        })

    return tiers


# ---------------------------------------------------------------------------
# Combination scoring
# ---------------------------------------------------------------------------

# Popular number clusters:
#   Birthday effect: 1–31 (heavily played for birth months/days)
#   Round/memorable: multiples of 5 across the range
_BIRTHDAY_MAX = 31


def _popular_main_set(main_max: int) -> frozenset:
    birthday = frozenset(range(1, _BIRTHDAY_MAX + 1))
    round_nums = frozenset(range(5, main_max + 1, 5))
    return birthday | round_nums


def field_coverage_score(nums: List[int], main_min: int, main_max: int) -> float:
    """
    Zone coverage score [0.0, 1.0].
    Divides the field into 5 equal zones (one per pick slot).
    Base score = zones covered / 5.
    Penalty of -0.04 per pair of adjacent numbers (gap ≤ 2) to penalize clustering.
    """
    field_size = main_max - main_min + 1
    zone_size = field_size / 5
    zones_hit: set = set()
    for n in nums:
        z = int((n - main_min) / zone_size)
        zones_hit.add(min(z, 4))

    zone_score = len(zones_hit) / 5

    sorted_nums = sorted(nums)
    gaps = [sorted_nums[i + 1] - sorted_nums[i] for i in range(len(sorted_nums) - 1)]
    consecutive_pairs = sum(1 for g in gaps if g <= 2)
    spread_penalty = consecutive_pairs * 0.04

    return max(0.0, round(zone_score - spread_penalty, 4))


def popular_avoidance_score(nums: List[int], main_max: int) -> float:
    """
    Popular number avoidance score [0.0, 1.0].
    1.0 = no numbers in the birthday/round-number cluster.
    0.0 = all five numbers are popular.
    """
    popular = _popular_main_set(main_max)
    outside = sum(1 for n in nums if n not in popular)
    return round(outside / len(nums), 4)


def bonus_avoidance_score(bonus: int, bonus_min: int, bonus_max: int) -> float:
    """
    Bonus ball avoidance score [0.0, 1.0].
    For tiny ranges (MFL 1–4): returns 0.5 — no meaningful differentiation.
    For larger ranges (MM 1–25, PB 1–26): penalizes low/round bonus balls
    that are heavily played (1, 2, 3, 7, 10, 11, 13, 23).
    """
    pool_size = bonus_max - bonus_min + 1
    if pool_size <= 4:
        return 0.5  # tiny range — no avoidance benefit possible

    popular_bonus = frozenset([1, 2, 3, 7, 10, 11, 13, 23])
    return 0.0 if bonus in popular_bonus else 1.0


@dataclass
class ComboScore:
    game: str
    main_numbers: List[int]
    bonus: int
    field_coverage: float
    popular_avoidance: float
    bonus_avoidance: float
    composite_score: float
    secondary_ev: float          # game constant
    ticket_price: float          # cost per play in dollars
    zones_covered: int
    popular_count: int           # how many main numbers are in popular cluster
    popular_numbers: List[int]   # which ones

    def as_ticket(self) -> str:
        nums = "-".join(f"{n:02d}" for n in sorted(self.main_numbers))
        return f"{nums} | B {self.bonus:02d}"

    def grade(self) -> str:
        if self.composite_score >= 0.75:
            return "A"
        if self.composite_score >= 0.60:
            return "B"
        if self.composite_score >= 0.45:
            return "C"
        return "D"


def score_combination(
    game: str,
    main_numbers: List[int],
    bonus: int,
) -> ComboScore:
    """Score a single combination for secondary prize optimization."""
    cfg = GAME_CONFIGS[game]
    nums = list(main_numbers)

    fc = field_coverage_score(nums, cfg.main_min, cfg.main_max)
    pa = popular_avoidance_score(nums, cfg.main_max)
    ba = bonus_avoidance_score(bonus, cfg.bonus_min, cfg.bonus_max)

    composite = round(0.40 * fc + 0.45 * pa + 0.15 * ba, 4)

    popular = _popular_main_set(cfg.main_max)
    popular_in_combo = sorted(n for n in nums if n in popular)

    field_size = cfg.main_max - cfg.main_min + 1
    zone_size = field_size / 5
    zones: set = set()
    for n in nums:
        z = int((n - cfg.main_min) / zone_size)
        zones.add(min(z, 4))

    ev = secondary_prize_ev(cfg)

    return ComboScore(
        game=game,
        main_numbers=sorted(nums),
        bonus=bonus,
        field_coverage=fc,
        popular_avoidance=pa,
        bonus_avoidance=ba,
        composite_score=composite,
        secondary_ev=ev,
        ticket_price=cfg.ticket_price,
        zones_covered=len(zones),
        popular_count=len(popular_in_combo),
        popular_numbers=popular_in_combo,
    )


# ---------------------------------------------------------------------------
# Historical data audit
# ---------------------------------------------------------------------------

@dataclass
class GameAudit:
    game: str
    draws_loaded: int
    avg_popular_main_pct: float       # avg % of winning numbers in popular cluster
    avg_field_spread: float           # avg field coverage score of winning draws
    high_spread_draws_pct: float      # % of draws with field_coverage >= 0.80
    most_frequent_mains: List[Tuple[int, int]]   # top 10 (number, count)
    most_frequent_bonus: List[Tuple[int, int]]   # top 5 (bonus, count)
    bonus_distribution: Dict[int, int]


def audit_historical(game: str) -> GameAudit:
    """Load historical CSV and compute draw quality statistics."""
    cfg = GAME_CONFIGS[game]
    data_path = _DATA_ROOT / cfg.data_file

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    popular = _popular_main_set(cfg.main_max)
    draws: List[List[int]] = []
    bonuses: List[int] = []
    main_freq: Dict[int, int] = {}
    bonus_freq: Dict[int, int] = {}

    with open(data_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                nums = [int(row[f"n{i}"]) for i in range(1, 6)]
                b = int(row["bonus"])
                draws.append(nums)
                bonuses.append(b)
                for n in nums:
                    main_freq[n] = main_freq.get(n, 0) + 1
                bonus_freq[b] = bonus_freq.get(b, 0) + 1
            except (KeyError, ValueError):
                continue

    if not draws:
        raise ValueError(f"No valid draws found in {data_path}")

    popular_pcts = [sum(1 for n in d if n in popular) / 5 for d in draws]
    spread_scores = [
        field_coverage_score(d, cfg.main_min, cfg.main_max) for d in draws
    ]
    high_spread = sum(1 for s in spread_scores if s >= 0.80)

    return GameAudit(
        game=game,
        draws_loaded=len(draws),
        avg_popular_main_pct=round(
            sum(popular_pcts) / len(popular_pcts) * 100, 1
        ),
        avg_field_spread=round(sum(spread_scores) / len(spread_scores), 3),
        high_spread_draws_pct=round(high_spread / len(draws) * 100, 1),
        most_frequent_mains=sorted(
            main_freq.items(), key=lambda x: -x[1]
        )[:10],
        most_frequent_bonus=sorted(
            bonus_freq.items(), key=lambda x: -x[1]
        )[:5],
        bonus_distribution=bonus_freq,
    )


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------

def _sep(char: str = "=", width: int = 64) -> str:
    return char * width


def print_game_header(game: str) -> None:
    cfg = GAME_CONFIGS[game]
    ev = secondary_prize_ev(cfg)
    print(f"\n{_sep()}")
    print(f"  {game}")
    print(
        f"  Main pool : {cfg.main_count} balls from {cfg.main_min}–{cfg.main_max}  "
        f"|  Bonus: 1 ball from {cfg.bonus_min}–{cfg.bonus_max}"
    )
    print(f"  Secondary EV  : ${ev:.4f} per $1 ticket  (game constant)")
    print(_sep())


def print_prize_table(game: str) -> None:
    cfg = GAME_CONFIGS[game]
    tiers = prize_tier_probabilities(cfg)
    print(f"\n  Prize Tiers — {game}")
    print(f"  {'Tier':<10}  {'Prize':>12}  {'Odds':>24}  {'EV Contrib':>12}")
    print(f"  {'-'*10}  {'-'*12}  {'-'*24}  {'-'*12}")
    for t in tiers:
        prize_str = "JACKPOT (varies)" if t["prize"] == 0 else f"${t['prize']:,}"
        ev_str = "—" if t["prize"] == 0 else f"${t['ev_contribution']:.6f}"
        print(
            f"  {t['tier']:<10}  {prize_str:>12}  {t['odds']:>24}  {ev_str:>12}"
        )


def print_combo_score(cs: ComboScore, show_ev: bool = True) -> None:
    print(f"\n  Ticket  : {cs.as_ticket()}")
    print(f"  Grade   : {cs.grade()}  (composite {cs.composite_score:.4f})")
    pop_str = str(cs.popular_numbers) if cs.popular_numbers else "none"
    print(
        f"  ├─ Field coverage    : {cs.field_coverage:.4f}  "
        f"({cs.zones_covered}/5 zones)"
    )
    print(
        f"  ├─ Popular avoidance : {cs.popular_avoidance:.4f}  "
        f"({cs.popular_count} popular: {pop_str})"
    )
    print(f"  └─ Bonus avoidance   : {cs.bonus_avoidance:.4f}")
    if show_ev:
        print(f"  Secondary EV (game const): ${cs.secondary_ev:.4f}/ticket")


def print_audit(audit: GameAudit) -> None:
    print(f"\n  Historical Audit — {audit.game}  ({audit.draws_loaded} draws)")
    print(f"  ├─ Avg popular numbers per draw  : {audit.avg_popular_main_pct:.1f}%")
    print(f"  ├─ Avg field spread score        : {audit.avg_field_spread:.3f}")
    print(f"  ├─ Draws with ≥80% spread        : {audit.high_spread_draws_pct:.1f}%")
    top_mains = ", ".join(f"{n}({c})" for n, c in audit.most_frequent_mains)
    print(f"  ├─ Top 10 main numbers           : {top_mains}")
    top_bonus = ", ".join(f"{b}({c})" for b, c in audit.most_frequent_bonus)
    print(f"  └─ Top 5 bonus balls             : {top_bonus}")


# ---------------------------------------------------------------------------
# Example combinations (for default demo mode — NOT recommended picks)
# ---------------------------------------------------------------------------

_EXAMPLE_COMBOS: Dict[str, List[Tuple[List[int], int]]] = {
    "MegaMillions": [
        ([4, 19, 33, 52, 67], 14),   # spread — should score well
        ([3, 7, 12, 21, 28], 2),     # birthday cluster — should score poorly
        ([9, 27, 41, 58, 70], 18),   # good spread, avoids birthday cluster
    ],
    "Powerball": [
        ([8, 22, 37, 55, 66], 15),   # spread example
        ([1, 5, 10, 15, 20], 3),     # round number cluster — should score poorly
        ([11, 34, 47, 62, 68], 19),  # spread, avoids birthday cluster
    ],
    "Millionaire For Life": [
        ([7, 18, 32, 46, 57], 3),    # spread example
        ([2, 8, 14, 22, 29], 1),     # birthday cluster — should score poorly
        ([13, 28, 39, 51, 59], 4),   # good spread
    ],
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_combination(
    cfg: GameConfig,
    main_nums: List[int],
    bonus_num: int,
) -> Optional[str]:
    """Return an error string if invalid, or None if valid."""
    if len(main_nums) != cfg.main_count:
        return f"Need exactly {cfg.main_count} main numbers, got {len(main_nums)}"
    if len(set(main_nums)) != cfg.main_count:
        return "Main numbers must be unique"
    for n in main_nums:
        if not (cfg.main_min <= n <= cfg.main_max):
            return f"Main number {n} out of range [{cfg.main_min}–{cfg.main_max}]"
    if not (cfg.bonus_min <= bonus_num <= cfg.bonus_max):
        return (
            f"Bonus {bonus_num} out of range "
            f"[{cfg.bonus_min}–{cfg.bonus_max}]"
        )
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Jackpot secondary prize optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python jackpot_secondary_optimizer.py --audit\n"
            "  python jackpot_secondary_optimizer.py --game Powerball --prizes\n"
            "  python jackpot_secondary_optimizer.py --game mm "
            "--main 8 22 37 55 66 --bonus 15\n"
            "  python jackpot_secondary_optimizer.py --all\n"
        ),
    )
    p.add_argument(
        "--game", type=str, default=None,
        help="Game: MegaMillions, Powerball, 'Millionaire For Life', mm, pb, mfl, m4l",
    )
    p.add_argument(
        "--main", type=int, nargs=5, default=None,
        metavar=("N1", "N2", "N3", "N4", "N5"),
        help="Five main ball numbers to score (requires --game and --bonus)",
    )
    p.add_argument(
        "--bonus", type=int, default=None,
        help="Bonus ball number to score (requires --game and --main)",
    )
    p.add_argument(
        "--audit", action="store_true",
        help="Show historical draw quality statistics for all games",
    )
    p.add_argument(
        "--all", dest="all_games", action="store_true",
        help="Run prize tables and example scoring for all three games",
    )
    p.add_argument(
        "--prizes", action="store_true",
        help="Show prize tier table with exact odds and EV contributions",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve which games to show
    if args.all_games:
        games_to_run = list(GAME_CONFIGS.keys())
    elif args.game:
        resolved = resolve_game(args.game)
        if not resolved:
            print(
                f"ERROR: Unknown game '{args.game}'. "
                f"Valid: {', '.join(GAME_CONFIGS.keys())}"
            )
            return
        games_to_run = [resolved]
    else:
        games_to_run = list(GAME_CONFIGS.keys())

    for game in games_to_run:
        print_game_header(game)

        # Always show prize table if --prizes, --all, or no specific combo given
        if args.prizes or args.all_games or (not args.main and not args.audit):
            print_prize_table(game)

        if args.audit:
            try:
                audit = audit_historical(game)
                print_audit(audit)
            except (FileNotFoundError, ValueError) as exc:
                print(f"\n  AUDIT ERROR: {exc}")

        elif args.main is not None and args.bonus is not None:
            # Score a specific combination (only for the targeted game)
            if not args.game:
                print("  ERROR: --main/--bonus require --game to be specified")
                return
            cfg = GAME_CONFIGS[game]
            err = validate_combination(cfg, args.main, args.bonus)
            if err:
                print(f"  ERROR: {err}")
                return
            cs = score_combination(game, list(args.main), args.bonus)
            print_combo_score(cs)

        else:
            # Default: show example combination scores
            print(
                f"\n  Example Combination Scores"
                f"  (use --main N N N N N --bonus N to score your own)"
            )
            for ex_main, ex_bonus in _EXAMPLE_COMBOS.get(game, []):
                cs = score_combination(game, ex_main, ex_bonus)
                print_combo_score(cs, show_ev=False)
            cfg = GAME_CONFIGS[game]
            ev = secondary_prize_ev(cfg)
            print(f"\n  Secondary EV (all combos, game constant): ${ev:.4f}/ticket")

    if not args.audit:
        print(
            f"\n  Tip: run with --audit to see historical draw quality statistics."
        )
    print()


if __name__ == "__main__":
    main()
