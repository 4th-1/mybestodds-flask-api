#!/usr/bin/env python3
"""
create_new_subscriber.py

Helper utility to create new subscriber files with guaranteed unique IDs.
Prevents conflicts before they happen.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from core.subscriber_id_manager import SubscriberIDManager, SubscriberInfo

def create_subscriber_template(subscriber_info: SubscriberInfo, subscriber_id: str, kit: str) -> dict:
    """Create a subscriber JSON template."""
    return {
        "subscriber_id": subscriber_id,
        "kit_type": kit,
        "dob": subscriber_info.birth_date,
        "coverage_start": "2025-12-22",
        "coverage_end": "2025-12-31",
        "formats": ["JSON"],
        "identity": {
            "first_name": subscriber_info.first_name,
            "last_name": subscriber_info.last_name,
            "birth_date": subscriber_info.birth_date,
            "birth_time": "12:00",  # Default, can be updated
            "birth_city": "Atlanta",  # Default, can be updated
            "birth_state": "GA"  # Default, can be updated
        },
        "preferences": {
            "games": [
                "Cash3",
                "Cash4",
                "MegaMillions",
                "Powerball",
                "Cash4Life"
            ],
            "play_styles": ["STRAIGHT", "BOX", "COMBO"],
            "max_plays_per_day": 5
        }
    }

def main():
    print("🆕 CREATE NEW SUBSCRIBER")
    print("=" * 40)
    
    # Get subscriber information
    print("Enter subscriber information:")
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    birth_date = input("Birth date (YYYY-MM-DD): ").strip()
    
    # Validate birth date format
    try:
        datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return
    
    # Choose kit
    print("\nAvailable kits:")
    print("1. BOOK3")
    print("2. BOOK")
    print("3. BOSK")
    
    kit_choice = input("Choose kit (1-3): ").strip()
    kit_map = {"1": "BOOK3", "2": "BOOK", "3": "BOSK"}
    
    if kit_choice not in kit_map:
        print("❌ Invalid kit choice")
        return
    
    kit = kit_map[kit_choice]
    
    # Generate unique ID
    manager = SubscriberIDManager(PROJECT_ROOT)
    subscriber_info = SubscriberInfo(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date
    )
    
    unique_id = manager.generate_unique_id(subscriber_info)
    
    # Create subscriber data
    subscriber_data = create_subscriber_template(subscriber_info, unique_id, kit)
    
    # Determine output path
    output_dir = PROJECT_ROOT / "data" / "subscribers" / kit
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{unique_id}_{kit}.json"
    output_path = output_dir / filename
    
    # Save file
    with open(output_path, 'w') as f:
        json.dump(subscriber_data, f, indent=2)
    
    print(f"\n✅ Created subscriber: {first_name} {last_name}")
    print(f"   Unique ID: {unique_id}")
    print(f"   File: {output_path}")
    print(f"   Kit: {kit}")
    
    # Update registry with file path
    if unique_id in manager.id_registry["used_ids"]:
        manager.id_registry["used_ids"][unique_id]["file_path"] = str(output_path)
        manager._save_registry()
    
    print(f"\n💡 To process this subscriber:")
    print(f"   python run_kit_v3.py \"{kit}/{filename}\" {kit}")

if __name__ == "__main__":
    main()