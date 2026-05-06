"""
ev_reranker.py — Phase 3A Cash3 EV Reranker
=============================================
Standalone layer that reads Cash3 candidate picks and scores each with:

    ev_score = base_lane_score
             + overlay_bonus
             + night_window_bonus
             + mmfsn_frequency_bonus
             + recent_signal_bonus
             + payout_adjusted_value
             - instability_penalty
             - overexposure_penalty
             - cold_signal_penalty

Decision ladder:
    ALLOW        — production lane + ev_score >= EV_THRESHOLD
    SHADOW_TRACK — below threshold, or BOX lane, or VERY_HIGH research
    BLOCK        — STRAIGHT+1OFF, Cash4, negative ev_score

The production gate (production_strategy.py) remains frozen at v2.
This reranker adds ordering and exposure priority INSIDE the gate.

Run (validation mode):
    python ev_reranker.py

Import (scoring individual picks):
    from ev_reranker import EVReranker, build_history
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

ROOT = Path(__file__).parent
SIM_CSV = ROOT / "simulation_report.csv"
CONDITION_SUMMARY_CSV = ROOT / "condition_summary.csv"
OUT_RANKED = ROOT / "ev_ranked_output.csv"

# ---------------------------------------------------------------------------
# v0 Weights — calibrate after 7–14 day live run
# ---------------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    # Base lane scores (applied by play_type)
    "STRAIGHT_BOX":          1.00,
    "BOX":                   0.35,
    "STRAIGHT_PLUS_1OFF":   -0.75,
    "STRAIGHT":              0.20,
    # Overlay tier bonuses
    "MODERATE_OVERLAY":      0.60,
    "HIGH_OVERLAY":          0.85,
    "VERY_HIGH_OVERLAY":     1.10,
    # Session window
    "NIGHT_WINDOW":          0.75,
    # VERY_HIGH + NIGHT combo (additive on top of VERY_HIGH_OVERLAY)
    "VERY_HIGH_NIGHT":       1.25,
    # MMFSN frequency tiers
    "MMFSN_VERY_HIGH":       1.15,
    "MMFSN_HIGH":            0.75,
    "MMFSN_MEDIUM":          0.35,
    "MMFSN_LOW":            -0.30,
    # Penalties (stored as positive magnitudes; subtracted in formula)
    "OVEREXPOSURE_PENALTY":  0.50,
    "UNSTABLE_LANE_PENALTY": 0.80,
    "COLD_SIGNAL_PENALTY":   0.40,
}

EV_THRESHOLD: float = 2.25

# Payout-adjusted value per play type (normalized; max useful range ≈ 0.0–0.75)
_PAV_TABLE: dict[str, float] = {
    "STRAIGHT_BOX":   0.50,   # max $330
    "BOX":            0.12,   # max  $80
    "STRAIGHT":       0.75,   # max $500
    "STRAIGHT+1OFF":  0.04,   # max  $24
    "ONE_OFF":        0.04,
}

# ---------------------------------------------------------------------------
# Tier assignment (mirrors payout_model / condition_scoring)
# ---------------------------------------------------------------------------
_CONFIDENCE_TIERS = [
    (0.00, 0.25, "LOW"),
    (0.25, 0.50, "MODERATE"),
    (0.50, 0.75, "HIGH"),
    (0.75, 1.01, "VERY_HIGH"),
]

def _score_to_tier(score: float) -> str:
    for lo, hi, label in _CONFIDENCE_TIERS:
        if lo <= score < hi:
            return label
    return "VERY_HIGH"


def _infer_session(row: dict) -> str:
    if row.get("actual_mid", "").strip():
        return "MIDDAY"
    if row.get("actual_eve", "").strip():
        return "EVENING"
    if row.get("actual_night", "").strip():
        return "NIGHT"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# History — pre-computes lookup tables from simulation_report.csv
# ---------------------------------------------------------------------------
class _History:
    """
    Builds from simulation_report.csv:
      - night_draws : [(date, actual_number)] — one entry per unique draw per day
      - lane_daily  : condition_key → {date → [is_win, ...]}
    """

    def __init__(self, csv_path: Path):
        # (date, actual_number) — deduplicated actual night draws
        self.night_draws: list[tuple[date, str]] = []
        # condition_key → date → list of 0/1 win flags
        self.lane_daily: dict[str, dict[date, list]] = defaultdict(lambda: defaultdict(list))
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        if not csv_path.exists():
            return

        seen_draws: set[tuple[date, str]] = set()

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("game", "").strip() != "Cash3":
                    continue

                date_str = row.get("date", "").strip()
                try:
                    d = date.fromisoformat(date_str)
                except ValueError:
                    continue

                session   = _infer_session(row)
                play_type = row.get("play_type", "").strip().upper()
                conf_str  = row.get("confidence_score", "0").strip()
                try:
                    conf = float(conf_str) if conf_str else 0.0
                except ValueError:
                    conf = 0.0
                tier     = _score_to_tier(conf)
                any_win  = int(row.get("any_win", 0) or 0)

                condition_key = f"Cash3|{tier}|{session}|{play_type}"
                self.lane_daily[condition_key][d].append(any_win)

                # Record actual night draw (deduplicated per day)
                if session == "NIGHT":
                    actual = row.get("actual_night", "").strip()
                    if actual:
                        dk = (d, actual)
                        if dk not in seen_draws:
                            seen_draws.add(dk)
                            self.night_draws.append(dk)

        self.night_draws.sort(key=lambda x: x[0])

    def mmfsn_tier(self, pick: str, as_of_date: date, lookback_days: int = 30) -> str:
        """Frequency tier: how often does this pick appear in recent night draws?"""
        cutoff = as_of_date - timedelta(days=lookback_days)
        count = sum(1 for d, num in self.night_draws if cutoff <= d < as_of_date and num == pick)
        if count >= 3:
            return "VERY_HIGH"
        if count == 2:
            return "HIGH"
        if count == 1:
            return "MEDIUM"
        return "LOW"

    def rolling_win_rate(self, condition_key: str, as_of_date: date, lookback_days: int = 7) -> float:
        """Fraction of wins for this condition over the last N days."""
        cutoff = as_of_date - timedelta(days=lookback_days)
        wins, total = 0, 0
        for d, flags in self.lane_daily[condition_key].items():
            if cutoff <= d < as_of_date:
                wins  += sum(flags)
                total += len(flags)
        return wins / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Lane stability from condition_summary.csv
# ---------------------------------------------------------------------------
def _load_lane_stability(csv_path: Path) -> dict[str, float]:
    """Returns {condition_key: roi_pct}."""
    stability: dict[str, float] = {}
    if not csv_path.exists():
        return stability
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("condition_key", "").strip()
            try:
                roi = float(row.get("roi_pct", 0))
            except ValueError:
                roi = 0.0
            stability[key] = roi
    return stability


# ---------------------------------------------------------------------------
# EVReranker
# ---------------------------------------------------------------------------
class EVReranker:
    """
    Scores and ranks Cash3 candidate picks by expected value.

    Usage:
        reranker = EVReranker(history=h, lane_stability=s)
        scored   = [reranker.score_pick(...) for pick in candidates]
        ranked   = reranker.rank_picks(scored)
    """

    def __init__(
        self,
        history: Optional[_History] = None,
        lane_stability: Optional[dict] = None,
        weights: Optional[dict] = None,
        threshold: float = EV_THRESHOLD,
    ):
        self.history       = history
        self.lane_stability = lane_stability or {}
        self.W             = {**WEIGHTS, **(weights or {})}
        self.threshold     = threshold

    # ------------------------------------------------------------------
    # Component methods
    # ------------------------------------------------------------------

    def _base_score(self, play_type: str) -> float:
        pt = play_type.upper()
        if pt == "STRAIGHT_BOX":
            return self.W["STRAIGHT_BOX"]
        if pt == "BOX":
            return self.W["BOX"]
        if pt in ("STRAIGHT+1OFF", "ONE_OFF"):
            return self.W["STRAIGHT_PLUS_1OFF"]
        if pt == "STRAIGHT":
            return self.W["STRAIGHT"]
        return 0.0

    def _overlay_bonus(self, tier: str, session: str) -> float:
        t = tier.upper()
        bonus = 0.0
        if t == "MODERATE":
            bonus = self.W["MODERATE_OVERLAY"]
        elif t == "HIGH":
            bonus = self.W["HIGH_OVERLAY"]
        elif t == "VERY_HIGH":
            bonus = self.W["VERY_HIGH_OVERLAY"]
        # VERY_HIGH + NIGHT combo is additive
        if t == "VERY_HIGH" and session.upper() == "NIGHT":
            bonus += self.W["VERY_HIGH_NIGHT"]
        return bonus

    def _night_bonus(self, session: str) -> float:
        return self.W["NIGHT_WINDOW"] if session.upper() == "NIGHT" else 0.0

    def _mmfsn_bonus(self, mmfsn_t: str) -> float:
        return self.W.get(f"MMFSN_{mmfsn_t.upper()}", 0.0)

    def _pav(self, play_type: str) -> float:
        return _PAV_TABLE.get(play_type.upper(), 0.0)

    def _instability_penalty(self, condition_key: str) -> float:
        roi = self.lane_stability.get(condition_key)
        if roi is not None and roi < -50.0:
            return self.W["UNSTABLE_LANE_PENALTY"]
        return 0.0

    def _cold_penalty(self, rolling_wr: float) -> float:
        return self.W["COLD_SIGNAL_PENALTY"] if rolling_wr == 0.0 else 0.0

    # ------------------------------------------------------------------
    # Full pick scoring
    # ------------------------------------------------------------------

    def score_pick(
        self,
        game: str,
        play_type: str,
        session: str,
        tier: str,
        pick: str,
        draw_date: date,
    ) -> dict:
        condition_key = f"{game}|{tier}|{session}|{play_type.upper()}"

        base    = self._base_score(play_type)
        overlay = self._overlay_bonus(tier, session)
        night   = self._night_bonus(session)
        pav     = self._pav(play_type)

        if self.history:
            mmfsn_t    = self.history.mmfsn_tier(pick, draw_date)
            rolling_wr = self.history.rolling_win_rate(condition_key, draw_date)
        else:
            mmfsn_t    = "LOW"
            rolling_wr = 0.0

        mmfsn_b       = self._mmfsn_bonus(mmfsn_t)
        recent_signal = 0.25 if rolling_wr > 0.01 else 0.0
        instability_p = self._instability_penalty(condition_key)
        cold_p        = self._cold_penalty(rolling_wr)
        overexposure_p = 0.0  # v0: requires per-day pick-count index; reserved

        ev = (base + overlay + night + mmfsn_b + recent_signal + pav
              - instability_p - overexposure_p - cold_p)

        return {
            "date":                str(draw_date),
            "draw":                session,
            "game":                game,
            "lane":                play_type.upper(),
            "pick":                pick,
            "overlay_tier":        tier,
            "mmfsn_tier":          mmfsn_t,
            "base_score":          round(base,            4),
            "overlay_bonus":       round(overlay,         4),
            "night_bonus":         round(night,           4),
            "mmfsn_bonus":         round(mmfsn_b,         4),
            "recent_signal_bonus": round(recent_signal,   4),
            "pav_bonus":           round(pav,             4),
            "instability_penalty": round(instability_p,   4),
            "overexposure_penalty":round(overexposure_p,  4),
            "cold_signal_penalty": round(cold_p,          4),
            "ev_score":            round(ev,              4),
            "rolling_win_rate":    round(rolling_wr,      4),
            "condition_key":       condition_key,
        }

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def _decide(self, row: dict) -> tuple[str, str]:
        ev      = row["ev_score"]
        lane    = row["lane"]
        game    = row["game"]
        session = row["draw"]
        tier    = row["overlay_tier"].upper()

        # Normalize display names for tier comparison
        tier_raw = tier.replace("PRIORITY WATCH", "MODERATE").replace("OVERLAY SUPPORTED", "HIGH")

        # Cash4 is fully isolated
        if game.upper() == "CASH4":
            return "BLOCK", "Cash4 isolated — not in production track"

        # STRAIGHT+1OFF: always blocked (confirmed -100% ROI)
        if lane in ("STRAIGHT+1OFF", "ONE_OFF"):
            return "BLOCK", "Unstable negative shadow lane (STRAIGHT+1OFF confirmed -100% ROI)"

        # Production lane: Cash3 | MODERATE | NIGHT | STRAIGHT_BOX
        in_prod_lane = (
            game == "Cash3"
            and session == "NIGHT"
            and tier_raw in ("MODERATE",)
            and lane == "STRAIGHT_BOX"
        )

        if in_prod_lane:
            if ev >= self.threshold:
                return "ALLOW", (
                    f"Production gate + ev_score={ev:.2f} >= threshold={self.threshold:.2f}"
                )
            else:
                return "SHADOW_TRACK", (
                    f"Production lane but ev_score={ev:.2f} below threshold — cold signal suppressed"
                )

        # BOX: shadow track only
        if lane == "BOX":
            return "SHADOW_TRACK", (
                f"Box shadow lane — tracking until EV proves positive (ev={ev:.2f})"
            )

        # VERY_HIGH | NIGHT | STRAIGHT_BOX: research track (not in prod yet)
        if tier_raw == "VERY_HIGH" and session == "NIGHT" and lane == "STRAIGHT_BOX":
            return "SHADOW_TRACK", (
                f"VERY_HIGH+NIGHT research candidate — needs sample stability (ev={ev:.2f})"
            )

        # Everything else
        if ev < 0:
            return "BLOCK", f"Negative EV ({ev:.2f}) — not viable"

        return "SHADOW_TRACK", f"Below threshold or outside production lane — research tracking"

    # ------------------------------------------------------------------
    # Rank a list of scored picks
    # ------------------------------------------------------------------

    def rank_picks(self, scored: list[dict]) -> list[dict]:
        """Sort by ev_score descending, assign rank and decision."""
        ranked = sorted(scored, key=lambda r: r["ev_score"], reverse=True)
        for i, row in enumerate(ranked, 1):
            row["rank"] = i
            decision, reason = self._decide(row)
            row["decision"] = decision
            row["reason"]   = reason
        return ranked


# ---------------------------------------------------------------------------
# Public builder helpers
# ---------------------------------------------------------------------------

def build_history(csv_path: Path = SIM_CSV) -> _History:
    return _History(csv_path)


def build_reranker(
    history: Optional[_History] = None,
    weights: Optional[dict] = None,
    threshold: float = EV_THRESHOLD,
) -> EVReranker:
    stability = _load_lane_stability(CONDITION_SUMMARY_CSV)
    return EVReranker(
        history=history or build_history(),
        lane_stability=stability,
        weights=weights,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Standalone validation — runs against simulation_report.csv
# ---------------------------------------------------------------------------

_OUTPUT_FIELDS = [
    "date", "draw", "game", "lane", "pick",
    "overlay_tier", "mmfsn_tier",
    "base_score", "overlay_bonus", "night_bonus", "mmfsn_bonus",
    "recent_signal_bonus", "pav_bonus",
    "instability_penalty", "overexposure_penalty", "cold_signal_penalty",
    "ev_score", "rank", "decision", "reason",
    "rolling_win_rate", "condition_key",
]


def _load_unique_daily_picks(csv_path: Path) -> dict[str, list[dict]]:
    """
    Deduplicates simulation_report.csv to unique (date, game, pick, play_type, session)
    combinations for Cash3 only.  Returns {date_str: [pick_dict, ...]}
    """
    daily: dict[str, list[dict]] = defaultdict(list)
    seen: set = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("game", "").strip() != "Cash3":
                continue
            session   = _infer_session(row)
            if session == "UNKNOWN":
                continue
            play_type = row.get("play_type", "").strip().upper()
            pick_str  = row.get("pick", "").strip()
            date_str  = row.get("date", "").strip()
            conf_str  = row.get("confidence_score", "0").strip()
            try:
                conf = float(conf_str) if conf_str else 0.0
            except ValueError:
                conf = 0.0
            tier = _score_to_tier(conf)

            key = (date_str, pick_str, play_type, session)
            if key in seen:
                continue
            seen.add(key)

            try:
                d = date.fromisoformat(date_str)
            except ValueError:
                continue

            daily[date_str].append({
                "game":      "Cash3",
                "play_type": play_type,
                "session":   session,
                "tier":      tier,
                "pick":      pick_str,
                "date":      d,
            })

    return daily


def run_validation(limit_days: int = 30) -> list[dict]:
    print("Loading history ...")
    history   = build_history(SIM_CSV)
    stability = _load_lane_stability(CONDITION_SUMMARY_CSV)
    reranker  = EVReranker(history=history, lane_stability=stability)

    print("Loading unique daily picks ...")
    daily = _load_unique_daily_picks(SIM_CSV)

    all_rows: list[dict] = []
    for date_str in sorted(daily.keys())[:limit_days]:
        candidates = daily[date_str]
        scored = [
            reranker.score_pick(
                game=c["game"],
                play_type=c["play_type"],
                session=c["session"],
                tier=c["tier"],
                pick=c["pick"],
                draw_date=c["date"],
            )
            for c in candidates
        ]
        ranked = reranker.rank_picks(scored)
        all_rows.extend(ranked)

    # Write CSV
    with open(OUT_RANKED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"  Saved: {OUT_RANKED}  ({len(all_rows):,} rows)")

    return all_rows


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def _sep(char="=", w=110): print(char * w)


def print_validation_report(rows: list[dict]) -> None:
    from collections import Counter

    _sep()
    print("  EV RERANKER v0 — VALIDATION REPORT")
    print(f"  Threshold: {EV_THRESHOLD}  |  Rows: {len(rows):,}")
    _sep()

    # Decision summary
    decision_counts = Counter(r["decision"] for r in rows)
    lane_counts     = Counter(r["lane"]     for r in rows)

    _sep("-")
    print("  DECISION BREAKDOWN")
    _sep("-")
    for decision, count in sorted(decision_counts.items()):
        pct = count / len(rows) * 100
        print(f"  {decision:<15} {count:>7,}  ({pct:5.1f}%)")

    print()
    _sep("-")
    print("  LANE COVERAGE")
    _sep("-")
    for lane, count in lane_counts.most_common():
        pct = count / len(rows) * 100
        print(f"  {lane:<25} {count:>7,}  ({pct:5.1f}%)")

    # EV score distribution per decision
    print()
    _sep("-")
    print("  EV SCORE STATS BY DECISION")
    _sep("-")
    by_decision: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_decision[r["decision"]].append(r["ev_score"])

    hdr = f"  {'Decision':<15} {'Count':>7} {'Min':>7} {'Max':>7} {'Avg':>7} {'Median':>8}"
    print(hdr)
    _sep("-")
    for dec in ("ALLOW", "SHADOW_TRACK", "BLOCK"):
        evs = sorted(by_decision.get(dec, []))
        if not evs:
            continue
        n      = len(evs)
        mn     = evs[0]
        mx     = evs[-1]
        avg    = sum(evs) / n
        median = evs[n // 2]
        print(f"  {dec:<15} {n:>7,} {mn:>7.2f} {mx:>7.2f} {avg:>7.2f} {median:>8.2f}")

    # ALLOW breakdown by condition
    allow_rows = [r for r in rows if r["decision"] == "ALLOW"]
    if allow_rows:
        print()
        _sep("-")
        print(f"  ALLOW DECISIONS — condition breakdown  ({len(allow_rows):,} total)")
        _sep("-")
        cond_cnt = Counter(r["condition_key"] for r in allow_rows)
        mmfsn_cnt = Counter(r["mmfsn_tier"] for r in allow_rows)
        for ckey, cnt in cond_cnt.most_common():
            print(f"  {ckey:<50} {cnt:>7,}")
        print()
        print("  MMFSN tier distribution within ALLOW:")
        for mt, cnt in mmfsn_cnt.most_common():
            print(f"    {mt:<12} {cnt:>7,}")

    # Last 3 days sample — ranked output for the most recent date
    print()
    _sep("-")
    print("  SAMPLE: LAST DATE IN VALIDATION WINDOW")
    _sep("-")
    all_dates = sorted(set(r["date"] for r in rows))
    if all_dates:
        last_date = all_dates[-1]
        sample = [r for r in rows if r["date"] == last_date]
        sample_sorted = sorted(sample, key=lambda r: r["ev_score"], reverse=True)[:15]
        hdr2 = (f"  {'Rank':>4} {'Pick':<8} {'Lane':<16} {'Tier':<12} {'MMFSN':<10} "
                f"{'EV':>6} {'Decision':<14} {'Reason'}")
        print(f"  Date: {last_date}  ({len(sample)} unique picks)")
        print(hdr2)
        _sep("-")
        for r in sample_sorted:
            marker = " ***" if r["decision"] == "ALLOW" else ""
            print(f"  {r['rank']:>4} {r['pick']:<8} {r['lane']:<16} {r['overlay_tier']:<12} "
                  f"{r['mmfsn_tier']:<10} {r['ev_score']:>6.2f} {r['decision']:<14} "
                  f"{r['reason'][:55]}{marker}")

    _sep()
    print(f"  Ranked output: {OUT_RANKED}")
    _sep()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not SIM_CSV.exists():
        print(f"ERROR: {SIM_CSV} not found")
        sys.exit(1)

    rows = run_validation(limit_days=30)
    print_validation_report(rows)
