#!/usr/bin/env python3
"""
Generate 2000 Test Subscribers for December 22-31, 2025
========================================================
Creates test subscribers specifically for the current date range with today's predictions.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, date
import random

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class TestSubscriberGenerator:
    """Generate test subscribers for December 22-31, 2025."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.subscribers_dir = self.project_root / "data" / "subscribers" / "BOOK3_TEST"
        self.subscribers_dir.mkdir(parents=True, exist_ok=True)
        
        # Date range: December 22-31, 2025
        self.start_date = "2025-12-22"
        self.end_date = "2025-12-31"
        
        # Sample names for variety
        self.first_names = [
            "Alexander", "Benjamin", "Catherine", "Daniel", "Elizabeth", "Francis", "Grace", "Henry",
            "Isabella", "Jacob", "Katherine", "Liam", "Madison", "Noah", "Olivia", "Patrick",
            "Quinn", "Rachel", "Samuel", "Taylor", "Uma", "Victor", "Willow", "Xavier", "Yvonne", "Zachary"
        ]
        
        self.last_names = [
            "Anderson", "Brown", "Clark", "Davis", "Evans", "Foster", "Garcia", "Harris",
            "Jackson", "Johnson", "Kelly", "Lewis", "Martinez", "Nelson", "O'Connor", "Parker",
            "Rodriguez", "Smith", "Taylor", "Thompson", "Williams", "Wilson", "Young", "Zhang"
        ]
    
    def generate_random_subscriber(self, test_id: int) -> dict:
        """Generate a single test subscriber."""
        
        # Random personal details
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        
        # Random birth date (for astrological calculations)
        birth_year = random.randint(1960, 2000)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)  # Safe day range
        
        # Random preferences
        favorite_numbers = sorted(random.sample(range(1, 50), 6))
        lucky_colors = random.sample(["red", "blue", "green", "yellow", "purple", "orange"], 2)
        
        subscriber_data = {
            "subscriber_id": f"TEST{test_id:04d}",
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": f"{birth_year}-{birth_month:02d}-{birth_day:02d}",
            "start_date": self.start_date,
            "end_date": self.end_date,
            "kit": "BOOK3_TEST",
            "preferences": {
                "favorite_numbers": favorite_numbers,
                "lucky_colors": lucky_colors,
                "play_style": random.choice(["conservative", "aggressive", "balanced"]),
                "focus_games": ["Cash3", "Cash4", "Cash4Life", "MegaMillions", "Powerball"]
            },
            "subscription": {
                "type": "TEST",
                "status": "active",
                "created_date": "2025-12-22",
                "notes": f"Test subscriber {test_id} for high-confidence analysis"
            }
        }
        
        return subscriber_data
    
    def generate_all_subscribers(self, count: int = 2000):
        """Generate all 2000 test subscribers."""
        
        print(f"🎯 GENERATING {count} TEST SUBSCRIBERS")
        print("=" * 60)
        print(f"📅 Date Range: {self.start_date} to {self.end_date}")
        print(f"📁 Output Directory: {self.subscribers_dir}")
        print()
        
        generated_files = []
        
        for test_id in range(1, count + 1):
            subscriber_data = self.generate_random_subscriber(test_id)
            
            # Save subscriber file
            filename = f"TEST{test_id:04d}_BOOK3.json"
            filepath = self.subscribers_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(subscriber_data, f, indent=2)
            
            generated_files.append(str(filepath))
            
            # Progress updates
            if test_id % 100 == 0:
                print(f"✅ Generated {test_id}/{count} subscribers...")
        
        print(f"\n🎉 Successfully generated {count} test subscribers!")
        print(f"📊 Files created: {len(generated_files)}")
        print(f"📂 Location: {self.subscribers_dir}")
        
        return generated_files

def main():
    """Main execution."""
    print("🎯 MY BEST ODDS - TEST SUBSCRIBER GENERATOR")
    print("=" * 80)
    print("📅 Target Date Range: December 22-31, 2025")
    print("🎮 Target Games: Cash3, Cash4, Cash4Life, MegaMillions, Powerball")
    print()
    
    generator = TestSubscriberGenerator()
    files = generator.generate_all_subscribers(2000)
    
    print("\n" + "=" * 80)
    print("✅ GENERATION COMPLETE!")
    print("🚀 Ready to run predictions for December 22, 2025")

if __name__ == "__main__":
    main()