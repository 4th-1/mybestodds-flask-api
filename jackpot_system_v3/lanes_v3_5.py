"""
lanes_v3_5.py

My Best Odds / SmartLogic V3.5
--------------------------------
Lane engine for PICK (Cash3/Cash4) and JACKPOT (MegaMillions, Powerball, Cash4Life).

This module does NOT try to be "mystical" on its own.
It provides a clean structure / API where the deep overlays
(MMFSN, Δ-high, numerology, astro, planetary hours, dream sync)
can be plugged in gradually without breaking the rest of V3.5.

High-level responsibilities:
- Define lane types and outputs.
- Provide per-game, per-kit lane logic dispatcher.
- Ensure BOSK / BOOK / BOOK3 routing is respected.
- Return a normalized structure that pick_engine_v3_5.py can use.

Lane design (V3.5)

PICK Lanes (Cash3/Cash4):
- Lane P_A: Δ-High + MMFSN + core stats.
- Lane P_B: Numerology & vibrational overlays (Life Path / Personal Year/Month).
- Lane P_C: Planetary hour + session alignment (placeholder-friendly).
- Lane P_D: DreamSync / journal entries.

JACKPOT Lanes (MegaMillions, Powerball, Cash4Life):
- Lane J_A: Frequency / recency / sum & range filters (history_v3_5).
- Lane J_B: Numerology + North Node + wealth houses 2/5/11 (placeholder-friendly).
- Lane J_C: Astro transits, moon phase, planetary context (placeholder-friendly).
- Lane J_D: Compression / elimination of low-composite-score zones.

Kits:
- BOSK:       Pick lanes only (Cash3 / Cash4).
- BOOK:       Pick + Jackpot lanes; no extra MMFSN emphasis.
- BOOK3:      Pick + Jackpot lanes; strongest MMFSN / "My Number Timing".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Literal, Optional, Any

from history_v3_5 import (
    GameType as HistoryGameType,
    BallStats,
    get_jackpot_stats,
    get_hot_balls,
    get_due_balls,
    rank_all_balls,
)

# -----------------------------
# Type definitions
# -----------------------------

KitType = Literal["BOSK", "BOOK", "BOOK3"]
GameType = Literal["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
SessionType = Literal["Midday", "Evening", "Night"]

LaneKind = Literal["pick", "jackpot"]

# For jackpots we distinguish main vs bonus
JackpotField = Literal["main", "bonus"]


@dataclass
class CandidatePick:
    """
    Represents a single PICK-style candidate (Cash3 / Cash4).

    We store:
    - value: string like "123" or "1023"
    - digits: list of ints for downstream analysis
    """
    value: str
    digits: List[int]

    def __post_init__(self) -> None:
        if not self.digits:
            self.digits = [int(ch) for ch in self.value]


@dataclass
class CandidateJackpot:
    """
    Represents a single JACKPOT-style candidate.

    For example, MegaMillions:
    - main: 5 distinct balls
    - bonus: 1 bonus ball
    """
    main: List[int]
    bonus: List[int]  # 0 or 1 ball depending on game configuration


@dataclass
class LaneOutput:
    """
    Output from one lane (P_A, P_B, J_A, etc.) for a specific draw.
    """
    kit: KitType
    game: GameType
    kind: LaneKind
    lane_id: str  # e.g. "P_A", "P_B", "J_A", ...
    draw_date: date
    session: Optional[SessionType]

    # Candidates:
    pick_candidates: List[CandidatePick] = field(default_factory=list)
    jackpot_candidates: List[CandidateJackpot] = field(default_factory=list)

    # Base lane score (before score_fx_v3_5 recalibration)
    base_lane_score: float = 0.0

    # Tags/flags for downstream scoring & auditing
    tags: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# Utility helpers
# -----------------------------


def _normalize_draw_date(d: Any) -> date:
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    # naive parse: expect "YYYY-MM-DD"
    return datetime.strptime(str(d), "%Y-%m-%d").date()


def _safe_int_list_from_str(num_str: str) -> List[int]:
    return [int(ch) for ch in num_str if ch.isdigit()]


def _get_basic_numerology_from_subscriber(sub: Dict[str, Any]) -> Dict[str, Any]:
    """
    Very light, placeholder numerology extractor.

    In your deeper system, you'll likely pre-compute:
    - life_path
    - personal_year
    - personal_month
    and store them in the subscriber JSON.

    Here we try to read them if present, else compute a crude fallback
    from DOB for minimal behavior.
    """
    out: Dict[str, Any] = {}

    lp = sub.get("life_path")
    py = sub.get("personal_year")
    pm = sub.get("personal_month")
    dob_str = sub.get("dob") or sub.get("DOB")  # "YYYY-MM-DD"

    if lp is not None:
        out["life_path"] = int(lp)
    if py is not None:
        out["personal_year"] = int(py)
    if pm is not None:
        out["personal_month"] = int(pm)

    if dob_str and ("life_path" not in out):
        try:
            y, m, d = [int(x) for x in str(dob_str).split("-")]
            digits = list(map(int, str(y) + str(m) + str(d)))
            s = sum(digits)
            while s > 9 and s not in (11, 22, 33):
                s = sum(int(ch) for ch in str(s))
            out["life_path"] = s
        except Exception:
            pass

    return out


# -----------------------------
# PICK Lanes (Cash3 / Cash4)
# -----------------------------


def _lane_pick_A_delta_mmfsn(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: SessionType,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane P_A: Δ-High + MMFSN + core stats.

    NOTE: This is a STRUCTURAL implementation.
    The real Δ-high / MMFSN logic should be plugged into
    the TODO areas below.

    For now, we generate a small, deterministic set of candidates
    using:
    - subscriber's DOB digits
    - day-of-month
    - last digit of year

    so the system runs end-to-end without crashing.
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="pick",
        lane_id="P_A",
        draw_date=draw_date,
        session=session,
        base_lane_score=0.6,  # initial weight, to be recalibrated
        tags={"lane_desc": "Δ-High + MMFSN (structural placeholder)"},
    )

    dob_str = str(subscriber.get("dob") or subscriber.get("DOB") or "")
    dom = draw_date.day
    year = draw_date.year

    base_digits: List[int] = []
    for ch in dob_str:
        if ch.isdigit():
            base_digits.append(int(ch))

    if not base_digits:
        # fallback to simple date digits
        base_digits = _safe_int_list_from_str(draw_date.strftime("%Y%m%d"))

    # For Cash3 / Cash4, build a few naive combos
    length = 3 if game == "Cash3" else 4

    # Example simple deterministic combos
    combos: List[str] = []

    # Combo 1: last 'length' digits from DOB-based digits (padded)
    while len(base_digits) < length:
        base_digits.append(base_digits[-1] if base_digits else dom % 10)
    combos.append("".join(str(d) for d in base_digits[-length:]))

    # Combo 2: rotate
    rotated = base_digits[1:] + base_digits[:1]
    combos.append("".join(str(d) for d in rotated[-length:]))

    # Combo 3: include day-of-month and year-last-digit pattern
    combos.append(
        "".join(
            str(d % 10)
            for d in [
                dom % 10,
                (year % 10),
                (dom + year) % 10,
                0 if length == 4 else None,
            ]
            if d is not None
        )
    )

    # De-duplicate while preserving order
    seen = set()
    final_combos: List[str] = []
    for c in combos:
        if c not in seen and len(c) == length:
            seen.add(c)
            final_combos.append(c)

    lane.pick_candidates = [
        CandidatePick(value=c, digits=_safe_int_list_from_str(c)) for c in final_combos
    ]

    lane.tags["combo_count"] = len(lane.pick_candidates)
    return lane


def _lane_pick_B_numerology(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: SessionType,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane P_B: Numerology & vibrational overlays.
    Uses Life Path / Personal Year / Personal Month if available.

    Placeholder logic:
    - Convert LP / PY / PM into digit sequences.
    - Build a small set of combos around that.

    In your real system, this is where Moorish numerology,
    Ken Dickkerson's principles, and Ghannam overlays will plug in.
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="pick",
        lane_id="P_B",
        draw_date=draw_date,
        session=session,
        base_lane_score=0.5,
        tags={"lane_desc": "Numerology & vibrational overlays (placeholder)"},
    )

    numerology = _get_basic_numerology_from_subscriber(subscriber)
    length = 3 if game == "Cash3" else 4

    seeds: List[int] = []
    for key in ("life_path", "personal_year", "personal_month"):
        v = numerology.get(key)
        if v is not None:
            seeds.extend([int(ch) for ch in str(v)])

    if not seeds:
        # fallback: day/month
        seeds.extend([draw_date.day % 10, draw_date.month % 10])

    # Build up a couple combos
    combos: List[str] = []
    while len(seeds) < length:
        seeds.append(seeds[-1])

    combos.append("".join(str(d % 10) for d in seeds[-length:]))

    # Reverse order combo
    combos.append("".join(str(d % 10) for d in reversed(seeds[-length:])))

    seen = set()
    final_combos: List[str] = []
    for c in combos:
        if c not in seen and len(c) == length:
            seen.add(c)
            final_combos.append(c)

    lane.pick_candidates = [
        CandidatePick(value=c, digits=_safe_int_list_from_str(c)) for c in final_combos
    ]
    lane.tags["numerology"] = numerology
    lane.tags["combo_count"] = len(lane.pick_candidates)

    return lane


def _lane_pick_C_planetary(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: SessionType,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane P_C: Planetary hour + session alignment.

    This is a placeholder lane that *structurally* exists.
    True planetary-hour calculations require ephemeris + geo.

    Here we:
    - Use day-of-week as a proxy.
    - Slightly bias combos based on that.

    In the real engine, this will integrate:
    - Planetary hours
    - Moon sign
    - User's 2/5/11 houses
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="pick",
        lane_id="P_C",
        draw_date=draw_date,
        session=session,
        base_lane_score=0.4,
        tags={"lane_desc": "Planetary hour + session alignment (placeholder)"},
    )

    length = 3 if game == "Cash3" else 4
    dow = draw_date.weekday()  # 0=Mon
    # simple mapping to digits
    base_digit = (dow + (0 if session == "Midday" else 3 if session == "Evening" else 6)) % 10

    # Build some minimal combos around base_digit
    combos: List[str] = []
    combos.append("".join(str((base_digit + i) % 10) for i in range(length)))
    combos.append("".join(str((base_digit + 2 * i) % 10) for i in range(length)))

    seen = set()
    final_combos: List[str] = []
    for c in combos:
        if c not in seen and len(c) == length:
            seen.add(c)
            final_combos.append(c)

    lane.pick_candidates = [
        CandidatePick(value=c, digits=_safe_int_list_from_str(c)) for c in final_combos
    ]
    lane.tags["day_of_week"] = dow
    lane.tags["combo_count"] = len(lane.pick_candidates)

    return lane


def _lane_pick_D_dreamsync(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: SessionType,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane P_D: DreamSync / journal entries.

    We expect future subscriber JSON to include something like:
    - "dream_numbers": ["123", "7184", ...]

    For now, if dream_numbers exist, we pull them;
    otherwise, this lane may produce 0 candidates.

    This is intentionally "opt-in / sparse".
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="pick",
        lane_id="P_D",
        draw_date=draw_date,
        session=session,
        base_lane_score=0.3,
        tags={"lane_desc": "DreamSync / journal numbers"},
    )

    dream_nums = subscriber.get("dream_numbers") or []
    if not isinstance(dream_nums, list):
        dream_nums = []

    length = 3 if game == "Cash3" else 4

    combos: List[str] = []
    for raw in dream_nums:
        s = "".join(ch for ch in str(raw) if ch.isdigit())
        if not s:
            continue
        if len(s) > length:
            s = s[-length:]
        elif len(s) < length:
            s = s.rjust(length, "0")
        combos.append(s)

    seen = set()
    final_combos: List[str] = []
    for c in combos:
        if c not in seen and len(c) == length:
            seen.add(c)
            final_combos.append(c)

    lane.pick_candidates = [
        CandidatePick(value=c, digits=_safe_int_list_from_str(c)) for c in final_combos
    ]
    lane.tags["combo_count"] = len(lane.pick_candidates)
    lane.tags["has_dream_data"] = bool(final_combos)

    return lane


def _generate_pick_lanes_for_draw(
    kit: KitType,
    game: GameType,
    draw_date: date,
    session: SessionType,
    subscriber: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[LaneOutput]:
    """
    Generate all PICK lanes (P_A–P_D) for the given draw.
    """
    if context is None:
        context = {}

    lanes: List[LaneOutput] = []

    # Lane A always included
    lanes.append(
        _lane_pick_A_delta_mmfsn(
            kit=kit,
            game=game,
            draw_date=draw_date,
            session=session,
            subscriber=subscriber,
            context=context,
        )
    )

    # Lane B (numerology) always included
    lanes.append(
        _lane_pick_B_numerology(
            kit=kit,
            game=game,
            draw_date=draw_date,
            session=session,
            subscriber=subscriber,
            context=context,
        )
    )

    # Lane C (planetary)
    lanes.append(
        _lane_pick_C_planetary(
            kit=kit,
            game=game,
            draw_date=draw_date,
            session=session,
            subscriber=subscriber,
            context=context,
        )
    )

    # Lane D (DreamSync) - may be empty if no dream data
    lanes.append(
        _lane_pick_D_dreamsync(
            kit=kit,
            game=game,
            draw_date=draw_date,
            session=session,
            subscriber=subscriber,
            context=context,
        )
    )

    return lanes


# -----------------------------
# JACKPOT Lanes (MM / PB / C4L)
# -----------------------------


def _map_game_to_history(game: GameType) -> HistoryGameType:
    if game == "MegaMillions":
        return "MegaMillions"
    if game == "Powerball":
        return "Powerball"
    if game == "Cash4Life":
        return "Cash4Life"
    raise ValueError(f"Game {game} not supported by history_v3_5")


def _lane_jackpot_A_frequency_recency(
    kit: KitType,
    game: GameType,
    draw_date: date,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane J_A: Frequency / recency / composite-based field narrowing.
    Uses history_v3_5 to select high-composite main and bonus balls,
    then builds a small set of candidate lines.

    This is intentionally modest in count to avoid explosion.
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="jackpot",
        lane_id="J_A",
        draw_date=draw_date,
        session=None,
        base_lane_score=0.6,
        tags={"lane_desc": "Frequency/Recency jackpot core (history-based)"},
    )

    h_game = _map_game_to_history(game)
    stats = get_jackpot_stats(h_game)

    # Game-specific configuration
    if game == "MegaMillions":
        main_count = 5
        bonus_count = 1
    elif game == "Powerball":
        main_count = 5
        bonus_count = 1
    elif game == "Cash4Life":
        main_count = 5
        bonus_count = 1
    else:
        raise ValueError(f"Unsupported jackpot game: {game}")

    # Take top composite main and bonus balls
    # (You can tune these sizes later)
    ranked_main = list(stats.main_balls.values())
    ranked_main.sort(key=lambda b: b.composite_score, reverse=True)
    top_main = ranked_main[:main_count + 3]  # a bit extra

    ranked_bonus = list(stats.bonus_balls.values())
    ranked_bonus.sort(key=lambda b: b.composite_score, reverse=True)
    top_bonus = ranked_bonus[:max(bonus_count, 3)]

    # Build candidate lines by sliding window in top_main and pairing with top_bonus
    candidates: List[CandidateJackpot] = []
    for i in range(0, max(1, len(top_main) - main_count + 1)):
        main_balls = [b.ball for b in top_main[i : i + main_count]]
        if len(main_balls) < main_count:
            continue

        for bb in top_bonus[:bonus_count]:
            candidates.append(
                CandidateJackpot(
                    main=sorted(main_balls),
                    bonus=[bb.ball] if bonus_count > 0 else [],
                )
            )

    # De-duplicate
    uniq = []
    seen = set()
    for c in candidates:
        key = (tuple(sorted(c.main)), tuple(sorted(c.bonus)))
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    lane.jackpot_candidates = uniq
    lane.tags["combo_count"] = len(uniq)
    lane.tags["history_last_updated"] = stats.last_updated

    return lane


def _lane_jackpot_B_numerology_wealth(
    kit: KitType,
    game: GameType,
    draw_date: date,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane J_B: Numerology + North Node + wealth houses (2/5/11) placeholder.

    For now, this lane:
    - Reads basic numerology (LP/PY/PM).
    - Maps these to ball numbers within valid ranges (roughly).
    - Builds a small set of lines around those "personal" balls.

    In the full system, this is where:
    - North Node in Capricorn (11H)
    - 2/5/11 house transits
    - Moorish numerology overlays
    will get layered in with real astro data.
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="jackpot",
        lane_id="J_B",
        draw_date=draw_date,
        session=None,
        base_lane_score=0.5,
        tags={"lane_desc": "Numerology + wealth houses (structural placeholder)"},
    )

    numerology = _get_basic_numerology_from_subscriber(subscriber)

    # Very lightweight game bounds (can be moved to config later)
    if game == "MegaMillions":
        main_max, bonus_max = 70, 25
        main_count, bonus_count = 5, 1
    elif game == "Powerball":
        main_max, bonus_max = 69, 26
        main_count, bonus_count = 5, 1
    elif game == "Cash4Life":
        main_max, bonus_max = 60, 4
        main_count, bonus_count = 5, 1
    else:
        raise ValueError(f"Unsupported jackpot game: {game}")

    seeds: List[int] = []
    for key in ("life_path", "personal_year", "personal_month"):
        v = numerology.get(key)
        if v is not None:
            seeds.append(int(v))

    if not seeds:
        seeds.append(draw_date.day)

    # Convert seeds to plausible main balls
    main_pool = sorted({((s - 1) % main_max) + 1 for s in seeds})
    while len(main_pool) < main_count:
        # simple expansion
        main_pool.append(((main_pool[-1] + 7) - 1) % main_max + 1)
        main_pool = sorted(set(main_pool))

    main_pool = main_pool[:main_count + 2]

    # Bonus balls from seeds
    bonus_pool = sorted({((s - 1) % bonus_max) + 1 for s in seeds})
    if not bonus_pool:
        bonus_pool = [((draw_date.month + draw_date.day) - 1) % bonus_max + 1]
    bonus_pool = bonus_pool[:bonus_count + 2]

    candidates: List[CandidateJackpot] = []

    for i in range(0, max(1, len(main_pool) - main_count + 1)):
        main = sorted(main_pool[i : i + main_count])
        if len(main) < main_count:
            continue
        for bb in bonus_pool[:bonus_count]:
            candidates.append(
                CandidateJackpot(main=main, bonus=[bb] if bonus_count > 0 else [])
            )

    uniq = []
    seen = set()
    for c in candidates:
        key = (tuple(sorted(c.main)), tuple(sorted(c.bonus)))
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    lane.jackpot_candidates = uniq
    lane.tags["numerology"] = numerology
    lane.tags["combo_count"] = len(uniq)
    return lane


def _lane_jackpot_C_astro_window(
    kit: KitType,
    game: GameType,
    draw_date: date,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane J_C: Astro transits, moon phase, planetary context.

    Placeholder lane:
    - Uses day-of-week and month as crude proxies for "window".
    - Slightly biases towards certain ranges of balls.

    In the real system, this taps:
    - Swiss Ephemeris-based transits
    - Moon phase
    - JDS North Node timing
    - Houses 2/5/11 and wealth transits
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="jackpot",
        lane_id="J_C",
        draw_date=draw_date,
        session=None,
        base_lane_score=0.4,
        tags={"lane_desc": "Astro window / moon phase (placeholder)"},
    )

    if game == "MegaMillions":
        main_max, bonus_max = 70, 25
        main_count, bonus_count = 5, 1
    elif game == "Powerball":
        main_max, bonus_max = 69, 26
        main_count, bonus_count = 5, 1
    elif game == "Cash4Life":
        main_max, bonus_max = 60, 4
        main_count, bonus_count = 5, 1
    else:
        raise ValueError(f"Unsupported jackpot game: {game}")

    dow = draw_date.weekday()
    month = draw_date.month

    # crude mapping to ball ranges
    base_main_start = (dow * 7 + month * 3) % (main_max - main_count)
    main = [((base_main_start + i) % main_max) + 1 for i in range(main_count)]

    base_bonus = (dow + month * 2) % bonus_max + 1
    bonus = [base_bonus] if bonus_count > 0 else []

    lane.jackpot_candidates = [CandidateJackpot(main=sorted(main), bonus=bonus)]
    lane.tags["day_of_week"] = dow
    lane.tags["month"] = month
    lane.tags["combo_count"] = 1

    return lane


def _lane_jackpot_D_compression(
    kit: KitType,
    game: GameType,
    draw_date: date,
    subscriber: Dict[str, Any],
    context: Dict[str, Any],
) -> LaneOutput:
    """
    Lane J_D: Compression / elimination of low-composite-score zones.

    Structural placeholder:
    - Reads overall ranking from history_v3_5.
    - Selects only balls above a composite threshold.
    - Builds a minimal number of lines.

    In your advanced logic, this lane becomes the "probability shield"
    that cuts out cold/dead zones aggressively.
    """
    lane = LaneOutput(
        kit=kit,
        game=game,
        kind="jackpot",
        lane_id="J_D",
        draw_date=draw_date,
        session=None,
        base_lane_score=0.3,
        tags={"lane_desc": "Composite-score compression (placeholder)"},
    )

    h_game = _map_game_to_history(game)
    stats = get_jackpot_stats(h_game)

    if game == "MegaMillions":
        main_count = 5
        bonus_count = 1
    elif game == "Powerball":
        main_count = 5
        bonus_count = 1
    elif game == "Cash4Life":
        main_count = 5
        bonus_count = 1
    else:
        raise ValueError(f"Unsupported jackpot game: {game}")

    # Keep only balls with composite_score >= median
    all_main = list(stats.main_balls.values())
    if not all_main:
        return lane

    sorted_main = sorted(all_main, key=lambda b: b.composite_score)
    median_index = len(sorted_main) // 2
    median_score = sorted_main[median_index].composite_score

    filtered_main = [b for b in all_main if b.composite_score >= median_score]
    filtered_main.sort(key=lambda b: b.composite_score, reverse=True)

    all_bonus = list(stats.bonus_balls.values())
    if all_bonus:
        sorted_bonus = sorted(all_bonus, key=lambda b: b.composite_score)
        median_index_b = len(sorted_bonus) // 2
        median_score_b = sorted_bonus[median_index_b].composite_score
        filtered_bonus = [b for b in all_bonus if b.composite_score >= median_score_b]
        filtered_bonus.sort(key=lambda b: b.composite_score, reverse=True)
    else:
        filtered_bonus = []

    # Build a very small set of lines from filtered sets
    candidates: List[CandidateJackpot] = []
    main_pool = filtered_main[:main_count + 2]
    bonus_pool = filtered_bonus[:max(1, bonus_count)]

    for i in range(0, max(1, len(main_pool) - main_count + 1)):
        main = sorted(b.ball for b in main_pool[i : i + main_count])
        if len(main) < main_count:
            continue
        for bb in bonus_pool[:bonus_count] if bonus_count > 0 else [None]:
            candidates.append(
                CandidateJackpot(
                    main=main,
                    bonus=[bb.ball] if (bb is not None and bonus_count > 0) else [],
                )
            )

    uniq = []
    seen = set()
    for c in candidates:
        key = (tuple(sorted(c.main)), tuple(sorted(c.bonus)))
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    lane.jackpot_candidates = uniq
    lane.tags["median_score"] = median_score
    lane.tags["combo_count"] = len(uniq)

    return lane


def _generate_jackpot_lanes_for_draw(
    kit: KitType,
    game: GameType,
    draw_date: date,
    subscriber: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[LaneOutput]:
    """
    Generate all JACKPOT lanes (J_A–J_D) for the given draw.
    """
    if context is None:
        context = {}

    lanes: List[LaneOutput] = []

    lanes.append(
        _lane_jackpot_A_frequency_recency(
            kit=kit,
            game=game,
            draw_date=draw_date,
            subscriber=subscriber,
            context=context,
        )
    )

    lanes.append(
        _lane_jackpot_B_numerology_wealth(
            kit=kit,
            game=game,
            draw_date=draw_date,
            subscriber=subscriber,
            context=context,
        )
    )

    lanes.append(
        _lane_jackpot_C_astro_window(
            kit=kit,
            game=game,
            draw_date=draw_date,
            subscriber=subscriber,
            context=context,
        )
    )

    lanes.append(
        _lane_jackpot_D_compression(
            kit=kit,
            game=game,
            draw_date=draw_date,
            subscriber=subscriber,
            context=context,
        )
    )

    return lanes


# -----------------------------
# PUBLIC API – what pick_engine_v3_5 should call
# -----------------------------


def generate_lanes_for_draw(
    kit: KitType,
    game: GameType,
    draw_date: Any,
    session: Optional[SessionType],
    subscriber: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[LaneOutput]:
    """
    Main external entry point.

    Given:
    - kit (BOSK, BOOK, BOOK3)
    - game
    - draw_date
    - session (for Cash3/Cash4; can be None for jackpots)
    - subscriber JSON data
    - optional context (pre-computed astro, moon, etc.)

    Return:
    - A list of LaneOutput objects representing all active lanes
      for that kit/game/draw.

    Kit routing:

    BOSK:
      - Only PICK games (Cash3/Cash4).
      - Only PICK lanes (P_A–P_D).
      - No jackpot lanes.

    BOOK:
      - PICK games:
          P_A–P_D.
      - JACKPOT games:
          J_A–J_D, normal strength.

    BOOK3:
      - PICK games:
          Same lanes, but interpreted as "enhanced" MMFSN overlays.
          (Your deeper MMFSN / personal-number logic will plug into P_A)
      - JACKPOT games:
          J_A–J_D with same structure, but you can later give them
          extra base weights in score_fx_v3_5 if needed.
    """
    d = _normalize_draw_date(draw_date)
    if context is None:
        context = {}

    lanes: List[LaneOutput] = []

    is_pick_game = game in ("Cash3", "Cash4")
    is_jackpot_game = game in ("MegaMillions", "Powerball", "Cash4Life")

    if is_pick_game:
        if session is None:
            raise ValueError("Session (Midday/Evening/Night) required for pick games.")

        lanes.extend(
            _generate_pick_lanes_for_draw(
                kit=kit,
                game=game,
                draw_date=d,
                session=session,
                subscriber=subscriber,
                context=context,
            )
        )

    if is_jackpot_game and kit in ("BOOK", "BOOK3"):
        # BOSK never includes jackpot lanes
        lanes.extend(
            _generate_jackpot_lanes_for_draw(
                kit=kit,
                game=game,
                draw_date=d,
                subscriber=subscriber,
                context=context,
            )
        )

    return lanes


if __name__ == "__main__":
    # Quick smoke test skeleton
    test_sub = {
        "dob": "1972-08-22",
        "life_path": 4,
        "personal_year": 3,
        "personal_month": 9,
        "dream_numbers": ["822", "4110"],
    }
    today = date.today()

    print("=== TEST: Cash3 BOSK Midday ===")
    lanes = generate_lanes_for_draw(
        kit="BOSK",
        game="Cash3",
        draw_date=today,
        session="Midday",
        subscriber=test_sub,
    )
    for l in lanes:
        print(l.lane_id, l.kind, [c.value for c in l.pick_candidates])

    print("\n=== TEST: MegaMillions BOOK3 ===")
    lanes_j = generate_lanes_for_draw(
        kit="BOOK3",
        game="MegaMillions",
        draw_date=today,
        session=None,
        subscriber=test_sub,
    )
    for l in lanes_j:
        print(
            l.lane_id,
            l.kind,
            [
                (cj.main, cj.bonus)
                for cj in l.jackpot_candidates[:3]
            ],
            "...",
        )
