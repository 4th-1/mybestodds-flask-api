#!/usr/bin/env python3
"""
Test MMFSN Course Correction Integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from personalized_scoring_engine_v3_7 import calculate_personalized_scores
import json

def test_mmfsn_weight_integration():
    """Test that MMFSN weights are properly applied"""
    
    # Create test subscriber
    test_subscriber = {
        "identity": {
            "first_name": "JDS",  # Joseph David Smith
            "last_name": "Smith", 
            "date_of_birth": "1985-03-15"
        },
        "mmfsn": {
            "Cash3": [1, 2, 3],
            "Cash4": [1, 2, 3, 4]
        }
    }
    
    # Create test config with MMFSN weight adjustment
    test_config = {
        "subscribers": {
            "JDS": {
                "mmfsn_weight": 0.75,  # Reduced weight due to misses
                "last_adjustment": "2025-12-23T10:30:00",
                "adjustment_reason": "High MMFSN miss rate: 45%"
            }
        }
    }
    
    # Save test config
    with open("test_config_mmfsn.json", "w") as f:
        json.dump(test_config, f, indent=2)
    
    # Test scoring with original weight (should be 1.0)
    print("🧪 Testing MMFSN Weight Integration")
    print("=" * 50)
    
    # Test with default weight
    scores_default = calculate_personalized_scores(test_subscriber, datetime(2025, 12, 23), "nonexistent_config.json")
    print(f"📊 Default MMFSN Score: {scores_default['mmfsn_score']:.1f} (weight: {scores_default['mmfsn_weight']:.3f})")
    
    # Test with adjusted weight  
    scores_adjusted = calculate_personalized_scores(test_subscriber, datetime(2025, 12, 23), "test_config_mmfsn.json")
    print(f"📉 Adjusted MMFSN Score: {scores_adjusted['mmfsn_score']:.1f} (weight: {scores_adjusted['mmfsn_weight']:.3f})")
    
    # Show the difference
    difference = scores_default['mmfsn_score'] - scores_adjusted['mmfsn_score']
    print(f"⚖️  Score Reduction: {difference:.1f} points due to course correction")
    
    # Verify weight was applied correctly
    if scores_adjusted['mmfsn_weight'] < 1.0:
        print("✅ MMFSN weight adjustment successfully applied!")
        print(f"📝 Adjustment reason: {test_config['subscribers']['JDS']['adjustment_reason']}")
    else:
        print("❌ MMFSN weight adjustment not applied")
    
    # Clean up
    os.remove("test_config_mmfsn.json")
    
    print("\n🎯 COURSE CORRECTION SUMMARY:")
    print("=" * 50)
    print("• When high-confidence MMFSN predictions miss")
    print("• System reduces MMFSN weight for that subscriber") 
    print("• Lower weight = less influence on future predictions")
    print("• Prevents repeated misses from same MMFSN patterns")
    print("• Personalizes system to each subscriber's actual results")

if __name__ == "__main__":
    test_mmfsn_weight_integration()