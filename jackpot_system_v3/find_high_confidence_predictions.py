#!/usr/bin/env python3
"""
COMPREHENSIVE HIGH CONFIDENCE FINDER
====================================
Extract high-confidence predictions from all available TEST subscriber data,
using score components to calculate confidence levels properly.
"""

import os
import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()

class RealTimeConfidenceFinder:
    """Find high-confidence predictions from available TEST subscriber data."""
    
    def __init__(self, min_confidence=60):
        self.project_root = PROJECT_ROOT
        self.outputs_dir = self.project_root / "outputs"
        self.min_confidence = min_confidence / 100.0  # Convert to decimal
        self.high_confidence_predictions = []
        
    def calculate_confidence_from_scores(self, score_data):
        """Calculate confidence percentage from score components."""
        try:
            # Extract base score
            base_score = score_data.get("score", 50)
            
            # Get score components for enhancement
            components = score_data.get("score_components", {})
            
            # Calculate enhanced confidence based on components
            confidence_boosts = []
            
            # Check for planetary alignment boosts
            if "planetary_alignment" in components:
                pa_score = components["planetary_alignment"]
                if pa_score > 0.7:
                    confidence_boosts.append(("planetary_alignment", pa_score * 15))
            
            # Check for MMFSN pattern strength
            if "mmfsn_score" in components:
                mmfsn = components["mmfsn_score"]
                if mmfsn > 0.6:
                    confidence_boosts.append(("mmfsn_pattern", mmfsn * 12))
            
            # Check for overlay bonuses
            for key, value in components.items():
                if "overlay" in key.lower() and value > 0.5:
                    confidence_boosts.append((key, value * 8))
            
            # Apply boosts to base score
            total_boost = sum(boost[1] for boost in confidence_boosts)
            enhanced_score = min(base_score + total_boost, 99)  # Cap at 99%
            
            return enhanced_score / 100.0, confidence_boosts
            
        except Exception as e:
            return 0.5, []  # Default 50% confidence
    
    def extract_predictions_from_file(self, json_file, subscriber_id):
        """Extract predictions from a single JSON file."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Calculate confidence for this prediction set
            confidence, boosts = self.calculate_confidence_from_scores(data)
            
            # Only process if confidence meets threshold
            if confidence < self.min_confidence:
                return []
            
            predictions = []
            picks = data.get("picks", {})
            
            # Target games we want
            target_games = ["Cash3", "Cash4", "Cash4Life", "MegaMillions"]
            
            for game in target_games:
                if game not in picks:
                    continue
                
                game_picks = picks[game]
                
                # Get lane system and MMFSN picks
                lane_system = game_picks.get("lane_system", [])
                lane_mmfsn = game_picks.get("lane_mmfsn", [])
                
                all_picks = lane_system + lane_mmfsn
                
                for pick_data in all_picks:
                    prediction = {
                        "subscriber_id": subscriber_id,
                        "date": json_file.stem,  # Date from filename
                        "game": game,
                        "numbers": pick_data,
                        "confidence": confidence,
                        "confidence_percent": f"{confidence*100:.1f}%",
                        "base_score": data.get("score", 50),
                        "boosts": boosts,
                        "score_components": len(data.get("score_components", {})),
                        "my_odds": self._calculate_my_odds(game, confidence)
                    }
                    predictions.append(prediction)
            
            return predictions
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            return []
    
    def _calculate_my_odds(self, game, confidence):
        """Calculate My Best Odds based on confidence."""
        base_odds = {
            "Cash3": 1000,
            "Cash4": 10000, 
            "Cash4Life": 21846048,
            "MegaMillions": 302575350
        }
        
        if game not in base_odds:
            return "Unknown"
        
        # Improve odds based on confidence
        improvement_factor = confidence * 2  # Higher confidence = better odds
        improved_odds = int(base_odds[game] / improvement_factor)
        
        return f"1-in-{improved_odds:,}"
    
    def scan_all_test_subscribers(self):
        """Scan all TEST subscriber output directories."""
        print("🔍 COMPREHENSIVE HIGH CONFIDENCE ANALYSIS")
        print("=" * 80)
        print(f"📊 Minimum Confidence: {self.min_confidence*100:.1f}%")
        print(f"🎯 Target Games: Cash3, Cash4, Cash4Life, MegaMillions")
        print()
        
        # Find all TEST subscriber directories
        test_dirs = []
        for d in self.outputs_dir.iterdir():
            if d.is_dir() and "TEST" in d.name:
                test_dirs.append(d)
        
        print(f"📂 Found {len(test_dirs)} TEST subscriber directories")
        print()
        
        total_files_processed = 0
        total_predictions = 0
        
        for test_dir in test_dirs:
            subscriber_id = self._extract_subscriber_id(test_dir.name)
            
            # Process all JSON files in this directory
            json_files = list(test_dir.glob("*.json"))
            json_files = [f for f in json_files if f.name != "summary.json"]
            
            for json_file in json_files:
                predictions = self.extract_predictions_from_file(json_file, subscriber_id)
                self.high_confidence_predictions.extend(predictions)
                total_predictions += len(predictions)
            
            total_files_processed += len(json_files)
            
            # Progress update every 100 directories
            if len(test_dirs) > 100 and (len([d for d in self.outputs_dir.iterdir() if d <= test_dir]) % 100 == 0):
                processed = len([d for d in self.outputs_dir.iterdir() if d <= test_dir])
                print(f"📊 Progress: {processed}/{len(test_dirs)} directories, {total_predictions} high-confidence picks found")
        
        print(f"✅ Scan complete!")
        print(f"📊 Files processed: {total_files_processed:,}")
        print(f"🎯 High-confidence predictions found: {len(self.high_confidence_predictions):,}")
        
        return self.high_confidence_predictions
    
    def _extract_subscriber_id(self, dir_name):
        """Extract subscriber ID from directory name."""
        if "TEST" in dir_name:
            parts = dir_name.split("_")
            for part in parts:
                if part.startswith("TEST") and len(part) >= 7:  # TEST0001 format
                    return part
        return dir_name
    
    def generate_report(self):
        """Generate comprehensive high-confidence report."""
        if not self.high_confidence_predictions:
            print("❌ No high-confidence predictions found!")
            return
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(self.high_confidence_predictions)
        
        print(f"\n🏆 HIGH CONFIDENCE PREDICTIONS REPORT")
        print("=" * 80)
        
        # Summary statistics
        print(f"📊 SUMMARY STATISTICS:")
        print(f"   Total Predictions: {len(df):,}")
        print(f"   Unique Subscribers: {df['subscriber_id'].nunique():,}")
        print(f"   Games Covered: {', '.join(df['game'].unique())}")
        print(f"   Date Range: {df['date'].min()} to {df['date'].max()}")
        print()
        
        # Confidence distribution
        print(f"📈 CONFIDENCE DISTRIBUTION:")
        print("-" * 50)
        
        confidence_ranges = [
            (90, 100, "🔥 ELITE (90-100%)"),
            (80, 89.99, "⭐ PREMIUM (80-89%)"), 
            (75, 79.99, "💎 HIGH (75-79%)"),
            (70, 74.99, "🎯 STRONG (70-74%)"),
            (65, 69.99, "✅ GOOD (65-69%)"),
            (60, 64.99, "📈 ABOVE AVERAGE (60-64%)")
        ]
        
        for min_conf, max_conf, label in confidence_ranges:
            count = len(df[(df['confidence'] >= min_conf/100) & (df['confidence'] <= max_conf/100)])
            pct = (count / len(df)) * 100 if len(df) > 0 else 0
            print(f"  {label}: {count:,} ({pct:.1f}%)")
        
        print()
        
        # Top predictions by game
        print(f"🎮 TOP PREDICTIONS BY GAME:")
        print("-" * 50)
        
        for game in ["Cash3", "Cash4", "Cash4Life", "MegaMillions"]:
            game_df = df[df['game'] == game].sort_values('confidence', ascending=False)
            if len(game_df) > 0:
                print(f"\n🎲 {game} (Top 5):")
                for idx, row in game_df.head(5).iterrows():
                    print(f"   {row['subscriber_id']}: {row['numbers']} ({row['confidence_percent']}) - {row['my_odds']}")
        
        # Save detailed report
        self.save_detailed_report(df)
    
    def save_detailed_report(self, df):
        """Save detailed report files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sort by confidence descending
        df_sorted = df.sort_values('confidence', ascending=False)
        
        # Save CSV report
        csv_file = self.project_root / f"high_confidence_predictions_{timestamp}.csv"
        df_sorted.to_csv(csv_file, index=False)
        
        # Save JSON report with summary
        json_file = self.project_root / f"high_confidence_analysis_{timestamp}.json"
        
        report_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "min_confidence_threshold": f"{self.min_confidence*100:.1f}%",
            "summary": {
                "total_predictions": len(df),
                "unique_subscribers": df['subscriber_id'].nunique(),
                "games": list(df['game'].unique()),
                "date_range": {
                    "start": df['date'].min(),
                    "end": df['date'].max()
                },
                "confidence_stats": {
                    "mean": f"{df['confidence'].mean()*100:.1f}%",
                    "max": f"{df['confidence'].max()*100:.1f}%",
                    "min": f"{df['confidence'].min()*100:.1f}%"
                }
            },
            "top_100_predictions": df_sorted.head(100).to_dict('records')
        }
        
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 CSV Report: {csv_file}")
        print(f"📄 JSON Report: {json_file}")

def main():
    """Main execution."""
    print("🎯 MY BEST ODDS - HIGH CONFIDENCE FINDER")
    print("=" * 80)
    
    # Run with 60% minimum confidence (more realistic than 75%)
    finder = RealTimeConfidenceFinder(min_confidence=60)
    
    # Scan all available data
    predictions = finder.scan_all_test_subscribers()
    
    # Generate comprehensive report
    finder.generate_report()
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")

if __name__ == "__main__":
    main()