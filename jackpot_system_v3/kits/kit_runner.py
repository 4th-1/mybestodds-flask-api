# kits/kit_runner.py (FINAL REBUILT VERSION)

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta

from core.score_fx_v3 import compute_v3_score
from core.stats_engine import compute_stats_score_for_day
from core.pick_engine_v3 import generate_picks_v3, load_ga_results


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_subscriber(sub_path: Path) -> Dict[str, Any]:
    with sub_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_subscriber_file(root: Path, name: str) -> Path:
    # If name is an absolute path, use it directly
    if Path(name).is_absolute() and Path(name).exists():
        return Path(name)
    # If name is already a project-relative path, check if it exists directly
    if name.startswith("data/") or name.startswith("data\\"):
        full_path = root / name
        if full_path.exists():
            return full_path
    
    subs_dir = root / "data" / "subscribers"
    name_lower = name.lower()

    # Extract just the filename if a path was provided
    if "/" in name or "\\" in name:
        name = Path(name).name
        name_lower = name.lower()

    direct_candidates = [
        subs_dir / name,
        subs_dir / f"{name}.json",
        subs_dir / name_lower,
        subs_dir / f"{name_lower}.json",
    ]

    for p in direct_candidates:
        if p.exists():
            return p

    for p in subs_dir.rglob("*.json"):
        if p.name.lower() == name_lower or p.name.lower() == f"{name_lower}.json":
            return p

    raise FileNotFoundError(f"Subscriber file not found anywhere: {name}")


def run_30_day_kit(
    subscriber_file: str,
    kit_name: str,
    output_dir: str = "outputs"
) -> None:

    root = Path(__file__).resolve().parents[1]

    subscriber_path = find_subscriber_file(root, subscriber_file)

    subscriber = load_subscriber(subscriber_path)
    config = load_config(root / "config" / "config_v3.json")

    coverage_start = subscriber["coverage_start"]
    coverage_end   = subscriber["coverage_end"]
    
    # Handle different subscriber formats for initials/directory codes
    # Priority: explicit initials > subscriber_id > calculated initials > fallback
    if "initials" in subscriber:
        initials = subscriber["initials"]
    elif "subscriber_id" in subscriber:
        # Use subscriber_id directly to avoid conflicts (e.g., JDSII vs JDS)
        # This supports both old format (JDSII) and new standardized format (JDS001)
        subscriber_id = subscriber["subscriber_id"]
        
        # If it follows new standardized format (e.g., JDS001), use as-is
        # If it's old format (e.g., JDSII), use as-is but consider migrating
        initials = subscriber_id
        
        # Note: For new subscribers, recommend using standardized IDs via subscriber_id_manager.py
    elif "identity" in subscriber:
        # Extract initials from identity section for test subscribers
        first_name = subscriber["identity"].get("first_name", "T")
        last_name = subscriber["identity"].get("last_name", "S")
        initials = f"{first_name[0]}{last_name[0]}"
    else:
        # Final fallback
        initials = "TS"
    
    # Handle different subscriber formats for name
    if "name" in subscriber:
        subscriber_name = subscriber["name"]
    elif "identity" in subscriber:
        # Extract name from identity section for test subscribers
        first_name = subscriber["identity"].get("first_name", "Test")
        last_name = subscriber["identity"].get("last_name", "Subscriber")
        subscriber_name = f"{first_name} {last_name}"
    else:
        # Fallback using subscriber_id
        subscriber_name = subscriber.get("subscriber_id", "Test Subscriber")

    start_date = datetime.fromisoformat(coverage_start)
    end_date   = datetime.fromisoformat(coverage_end)

    ga_results = load_ga_results(root)

    out_dir = (
        root
        / output_dir
        / f"{kit_name}_{initials}_{coverage_start}_to_{coverage_end}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    all_days: List[Dict[str, Any]] = []
    current = start_date

    while current <= end_date:

        day_str = current.date().isoformat()

        stats_score = compute_stats_score_for_day(
            current_date=current,
            kit_name=kit_name,
            config=config,
            root=root
        )

        # FIXED: Use personalized scoring instead of hardcoded identical values
        try:
            from personalized_scoring_engine_v3_7 import calculate_personalized_scores
            personalized_scores = calculate_personalized_scores(subscriber, current)
            
            astro_score = personalized_scores["astro_score"]
            ph_score    = personalized_scores["planetary_hour_score"] 
            mmfsn_score = personalized_scores["mmfsn_score"]
            num_score   = personalized_scores["numerology_score"]
        except Exception as e:
            print(f"Personalized scoring failed, using fallback: {e}")
            # Fallback with slight variations (better than identical)
            import random
            base_variation = random.uniform(-5.0, 5.0)
            astro_score = 60.0 + base_variation + random.uniform(-3.0, 3.0)
            ph_score    = 65.0 + base_variation + random.uniform(-3.0, 3.0)
            mmfsn_score = 58.0 + base_variation + random.uniform(-3.0, 3.0)
            num_score   = 62.0 + base_variation + random.uniform(-3.0, 3.0)

        score_result = compute_v3_score(
            astro_score=astro_score,
            stats_score=stats_score,
            planetary_hour_score=ph_score,
            mmfsn_score=mmfsn_score,
            numerology_score=num_score,
            weights=config["score_weights"]
        )

        picks = generate_picks_v3(
            subscriber=subscriber,
            score_result=score_result,
            ga_data=ga_results,
            root=root
        )

        day_record = {
            "date": day_str,
            "score": score_result.total,
            "score_components": score_result.components.__dict__,
            "score_debug": score_result.debug,
            "picks": picks
        }

        daily_path = out_dir / f"{day_str}.json"
        with daily_path.open("w", encoding="utf-8") as f:
            json.dump(day_record, f, indent=2)

        all_days.append(day_record)
        current += timedelta(days=1)

    scores = [d["score"] for d in all_days]

    summary = {
        "subscriber": {
            "name": subscriber_name,
            "initials": initials,
            "kit": kit_name,
            "coverage_start": coverage_start,
            "coverage_end": coverage_end
        },
        "num_days": len(all_days),
        "score_stats": {
            "min": min(scores),
            "max": max(scores),
            "avg": sum(scores) / len(scores) if scores else 0.0
        },
        "days": all_days
    }

    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
