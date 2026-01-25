from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any, Dict, Optional, Tuple

OVERLAY_VERSION = "3.7"

# Kit / engine target constants
KIT_BOOK = "BOOK"
KIT_BOOK3 = "BOOK3"
KIT_BOSK = "BOSK"
ENGINE_LEFT = "LEFT"   # Cash3 / Cash4
ENGINE_RIGHT = "RIGHT" # Jackpot (Mega, Powerball, Cash4Life)


@dataclass
class OverlayContext:
    """
    Unified overlay container for v3.7.

    - shared:       global overlays (moon, weather, numerology, planetary hours, etc.)
    - book_only:    BOOK-only overlays (natal, Vedic, etc.)
    - western:      Western astrology overlays for BOOK / BOOK3
    """
    version: str
    target: str
    shared: Dict[str, Any] = field(default_factory=dict)
    book_only: Dict[str, Any] = field(default_factory=dict)
    western: Dict[str, Any] = field(default_factory=dict)

    def get(self, group: str, key: str, default: Any = None) -> Any:
        """
        Convenience accessor:
        ctx.get("shared", "moon_phases")
        ctx.get("book", "vedic_timing")
        ctx.get("western", "house_2_5_11")
        """
        if group == "shared":
            return self.shared.get(key, default)
        if group == "book":
            return self.book_only.get(key, default)
        if group == "western":
            return self.western.get(key, default)
        raise ValueError(f"Unknown overlay group: {group!r}")


def _detect_base_dirs() -> Tuple[Path, Path, Path]:
    """
    Infer base directories from this file location.

    Assumes structure like:
        C:\MyBestOdds\
            jackpot_system_v3\
                core\
                    overlay_loader_v3_7.py
            shared_overlays\
            book_overlays\
    """
    here = Path(__file__).resolve()
    jackpot_root = here.parents[1]   # .../jackpot_system_v3
    project_root = jackpot_root.parent  # .../MyBestOdds

    shared_dir = project_root / "shared_overlays"
    book_dir = project_root / "book_overlays"
    return jackpot_root, shared_dir, book_dir


def _load_json(path: Path, required: bool = True) -> Optional[Dict[str, Any]]:
    """
    Safe JSON loader with clear error messages.
    """
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required overlay file not found: {path}")
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in overlay file {path}: {e}") from e


def _load_shared_overlays(shared_dir: Path) -> Dict[str, Any]:
    """
    Global overlays shared across engines and kits.
    """
    files = {
        "numerology_core": "numerology_core.json",
        "moon_phases": "moon_phases.json",
        "weather_rules": "weather_rules.json",
        "day_of_week": "day_of_week.json",
        "planetary_hours": "planetary_hours.json",
        "bias_patterns": "bias_patterns.json",
        "jackpot_hot_windows": "jackpot_hot_windows.json",
    }

    loaded: Dict[str, Any] = {}
    for key, filename in files.items():
        # jackpot_hot_windows is optional (only used by RIGHT / jackpot)
        data = _load_json(shared_dir / filename, required=(key != "jackpot_hot_windows"))
        if data is not None:
            loaded[key] = data
    return loaded


def _load_book_overlays(book_dir: Path, target: str) -> Dict[str, Any]:
    """
    BOOK-only overlays:
    - natal_chart.json
    - vedic_timing.json (BOOK only, not BOOK3/BOSK)
    """
    overlays: Dict[str, Any] = {}

    natal = _load_json(book_dir / "natal_chart.json", required=False)
    if natal:
        overlays["natal_chart"] = natal

    # VEDIC = BOOK ONLY (per your decision)
    if target == KIT_BOOK:
        vedic = _load_json(book_dir / "vedic_timing.json", required=False)
        if vedic:
            overlays["vedic_timing"] = vedic

    return overlays


def _load_western_overlays(book_dir: Path, target: str) -> Dict[str, Any]:
    """
    Western astrology overlays used by:
    - BOOK
    - BOOK3
    (never BOSK, never raw engines)
    """
    if target not in {KIT_BOOK, KIT_BOOK3}:
        return {}

    western = _load_json(book_dir / "western.json", required=False)
    return western or {}


def _filter_for_target(ctx: OverlayContext) -> OverlayContext:
    """
    Enforce IP / privilege boundaries at the context level.

    - BOSK: shared only, no book_only, no western
    - LEFT: shared only (but includes planetary_hours for timing)
    - RIGHT: shared only (plus jackpot_hot_windows where present)
    - BOOK: shared + book_only + western
    - BOOK3: shared + western only
    """
    t = ctx.target

    if t == KIT_BOSK:
        ctx.book_only.clear()
        ctx.western.clear()

    elif t == ENGINE_LEFT:
        ctx.book_only.clear()
        ctx.western.clear()
        # shared["planetary_hours"] is present and can be used
        # by the left engine to nudge confidence scores.

    elif t == ENGINE_RIGHT:
        ctx.book_only.clear()
        ctx.western.clear()
        # shared["jackpot_hot_windows"] is available if present.

    elif t == KIT_BOOK3:
        # Western OK, but NO natal/Vedic book_only overlays.
        ctx.book_only.clear()

    elif t == KIT_BOOK:
        # Full access: shared + book_only + western
        pass

    else:
        raise ValueError(f"Unknown overlay target: {t!r}")

    return ctx


def load_all_overlays(
    version: str = OVERLAY_VERSION,
    target: str = KIT_BOOK,
) -> OverlayContext:
    """
    Load all overlay JSONs into a single OverlayContext, filtered by target.

    Parameters
    ----------
    version : str
        Overlay / engine version string (currently informational only).
    target : str
        One of: BOOK, BOOK3, BOSK, LEFT, RIGHT.

    Returns
    -------
    OverlayContext
    """
    _, shared_dir, book_dir = _detect_base_dirs()

    shared = _load_shared_overlays(shared_dir)
    book_only = _load_book_overlays(book_dir, target)
    western = _load_western_overlays(book_dir, target)

    ctx = OverlayContext(
        version=version,
        target=target,
        shared=shared,
        book_only=book_only,
        western=western,
    )
    return _filter_for_target(ctx)


if __name__ == "__main__":
    # Simple smoke test when run directly
    for t in [KIT_BOOK, KIT_BOOK3, KIT_BOSK, ENGINE_LEFT, ENGINE_RIGHT]:
        try:
            c = load_all_overlays(target=t)
            print(
                f"[OK] Loaded overlays for target={t}: "
                f"shared={list(c.shared.keys())}, "
                f"book_only={list(c.book_only.keys())}, "
                f"western={list(c.western.keys())}"
            )
        except Exception as e:
            print(f"[ERROR] Failed to load overlays for target={t}: {e}")
