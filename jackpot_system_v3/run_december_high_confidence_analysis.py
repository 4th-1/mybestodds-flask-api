#!/usr/bin/env python3
"""
Run 2000 Test Subscribers for December 22-31, 2025
==================================================
Process all 2000 test subscribers and extract high-confidence predictions (75-100%)
for Cash3, Cash4, Cash4Life, MegaMillions, and Powerball for December 22, 2025.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pandas as pd

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class DecemberHighConfidenceFinder:
    """Process 2000 test subscribers for December 22-31 and find high-confidence predictions."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.subscribers_dir = self.project_root / "data" / "subscribers" / "BOOK3_TEST"
        self.outputs_dir = self.project_root / "outputs"
        
        # Target parameters
        self.target_date = "2025-12-22"
        self.target_games = ["Cash3", "Cash4", "Cash4Life", "MegaMillions", "Powerball"]
        self.confidence_threshold = 0.75  # 75% minimum
        
        # Results storage
        self.high_confidence_results = []
        self.processing_stats = {
            "total_processed": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "high_confidence_found": 0
        }
        self.lock = threading.Lock()
    
    def run_single_subscriber(self, subscriber_id: int) -> tuple:
        """Run prediction for a single test subscriber."""
        subscriber_file = f"TEST{subscriber_id:04d}_BOOK3.json"
        
        try:
            # Run the prediction system for December 22-31 range
            cmd = ["python", "run_kit_v3.py", f"BOOK3_TEST/{subscriber_file}", "BOOK3_TEST"]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            if result.returncode == 0:
                return (subscriber_id, "success", None)
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                return (subscriber_id, "failed", error_msg)
                
        except subprocess.TimeoutExpired:
            return (subscriber_id, "timeout", "Processing timeout")
        except Exception as e:
            return (subscriber_id, "error", str(e))
    
    def extract_high_confidence_predictions(self, subscriber_id: int) -> list:
        """Extract high-confidence predictions for December 22, 2025."""
        test_id = f"TEST{subscriber_id:04d}"
        
        # Find output directory - should be for December 22-31 range
        output_pattern = f"BOOK3_TEST_{test_id}_2025-12-22_to_2025-12-31"
        output_dir = None
        
        for d in self.outputs_dir.iterdir():
            if d.is_dir() and output_pattern in d.name:
                output_dir = d
                break
        
        if not output_dir:
            return []
        
        # Read December 22, 2025 predictions
        today_file = output_dir / f"{self.target_date}.json"
        if not today_file.exists():
            return []
        
        try:
            with open(today_file, 'r') as f:
                daily_data = json.load(f)
            
            high_confidence_predictions = []
            
            # Extract predictions from the daily data
            picks = daily_data.get("picks", {})
            
            for game in self.target_games:
                if game not in picks:
                    continue
                
                game_picks = picks[game]
                
                # Get lane system and MMFSN picks
                lane_system = game_picks.get("lane_system", [])
                lane_mmfsn = game_picks.get("lane_mmfsn", [])
                
                all_picks = lane_system + lane_mmfsn
                
                # Calculate confidence from score components
                confidence = self._calculate_confidence(daily_data, game)
                
                if confidence >= self.confidence_threshold:
                    for pick in all_picks:
                        prediction = {
                            "subscriber_id": test_id,
                            "game": game,
                            "date": self.target_date,
                            "numbers": pick,
                            "confidence": confidence,
                            "confidence_percent": f"{confidence*100:.1f}%",
                            "base_score": daily_data.get("score", 0),
                            "score_components": daily_data.get("score_components", {}),
                            "my_odds": self._calculate_my_odds(game, confidence),
                            "play_type": "STRAIGHT",  # Default for high confidence
                            "prediction_type": "lane_system" if pick in lane_system else "lane_mmfsn"
                        }
                        high_confidence_predictions.append(prediction)
            
            return high_confidence_predictions
            
        except Exception as e:
            print(f"   ❌ Error extracting {test_id}: {e}")
            return []
    
    def _calculate_confidence(self, daily_data: dict, game: str) -> float:
        """Calculate confidence from score components and base score."""
        try:
            base_score = daily_data.get("score", 50)
            components = daily_data.get("score_components", {})
            
            # Start with base confidence
            confidence = base_score / 100.0
            
            # Apply boosts based on score components
            boosts = 0
            
            # Planetary alignment boost
            if "planetary_alignment" in components:
                pa_score = components.get("planetary_alignment", 0)
                if pa_score > 0.7:
                    boosts += pa_score * 0.25  # Up to 25% boost
            
            # MMFSN pattern boost
            if "mmfsn_score" in components:
                mmfsn = components.get("mmfsn_score", 0)
                if mmfsn > 0.6:
                    boosts += mmfsn * 0.20  # Up to 20% boost
            
            # Overlay boosts
            overlay_boost = 0
            for key, value in components.items():
                if "overlay" in key.lower() and isinstance(value, (int, float)):
                    if value > 0.5:
                        overlay_boost += value * 0.10  # Up to 10% per overlay
            
            boosts += min(overlay_boost, 0.30)  # Cap overlay boost at 30%
            
            # Game-specific boosts
            if game in ["Cash3", "Cash4"]:
                # Daily games get slight boost for recent patterns
                boosts += 0.05
            elif game in ["MegaMillions", "Powerball"]:
                # Jackpot games need higher thresholds
                if base_score > 60:
                    boosts += 0.10
            
            final_confidence = min(confidence + boosts, 0.99)  # Cap at 99%
            return final_confidence
            
        except Exception:
            return 0.50  # Default 50% confidence
    
    def _calculate_my_odds(self, game: str, confidence: float) -> str:
        """Calculate My Best Odds based on confidence."""
        base_odds = {
            "Cash3": 1000,
            "Cash4": 10000,
            "Cash4Life": 21846048,
            "MegaMillions": 302575350,
            "Powerball": 292201338
        }
        
        if game not in base_odds:
            return "Unknown"
        
        # Improve odds based on confidence
        improvement_factor = max(confidence * 3, 1.5)  # Higher confidence = better odds
        improved_odds = int(base_odds[game] / improvement_factor)
        
        return f"1-in-{improved_odds:,}"
    
    def process_batch(self, start_id: int, end_id: int, batch_num: int, total_batches: int):
        """Process a batch of subscribers."""
        print(f"\n📦 BATCH {batch_num}/{total_batches} (TEST{start_id:04d}-TEST{end_id:04d})")
        print("-" * 50)
        print("🚀 Processing predictions...")
        
        batch_results = []
        batch_high_confidence = []
        
        # Run predictions for this batch
        with ThreadPoolExecutor(max_workers=8) as executor:
            subscriber_ids = list(range(start_id, end_id + 1))
            futures = {executor.submit(self.run_single_subscriber, sid): sid for sid in subscriber_ids}
            
            for future in as_completed(futures):
                subscriber_id = futures[future]
                try:
                    result = future.result()
                    batch_results.append(result)
                    
                    if result[1] == "success":
                        print(f"  ✅ TEST{subscriber_id:04d} - Processing complete")
                    else:
                        print(f"  ❌ TEST{subscriber_id:04d} - {result[1]}: {result[2]}")
                        
                except Exception as e:
                    print(f"  ❌ TEST{subscriber_id:04d} - Exception: {e}")
                    batch_results.append((subscriber_id, "exception", str(e)))
        
        # Extract high-confidence predictions from successful runs
        print("🔍 Extracting high-confidence predictions...")
        
        for result in batch_results:
            subscriber_id, status, error = result
            
            if status == "success":
                high_conf_preds = self.extract_high_confidence_predictions(subscriber_id)
                batch_high_confidence.extend(high_conf_preds)
                
                if high_conf_preds:
                    print(f"  🎯 TEST{subscriber_id:04d} - {len(high_conf_preds)} high-confidence predictions!")
        
        # Update stats
        with self.lock:
            self.processing_stats["total_processed"] += len(batch_results)
            self.processing_stats["successful_runs"] += sum(1 for r in batch_results if r[1] == "success")
            self.processing_stats["failed_runs"] += sum(1 for r in batch_results if r[1] != "success")
            self.processing_stats["high_confidence_found"] += len(batch_high_confidence)
            
            self.high_confidence_results.extend(batch_high_confidence)
        
        print(f"   📊 Batch {batch_num} Summary:")
        print(f"      Processed: {len(batch_results)}")
        print(f"      Successful: {sum(1 for r in batch_results if r[1] == 'success')}")
        print(f"      High Confidence: {len(batch_high_confidence)}")
        
        return batch_results, batch_high_confidence
    
    def run_all_subscribers(self, total_count: int = 2000):
        """Run all 2000 test subscribers."""
        
        print("🎯 MY BEST ODDS - DECEMBER HIGH CONFIDENCE ANALYSIS")
        print("=" * 80)
        print(f"📅 Target Date: {self.target_date}")
        print(f"🎮 Target Games: {', '.join(self.target_games)}")
        print(f"📊 Confidence Threshold: {self.confidence_threshold*100:.0f}%+")
        print(f"👥 Total Subscribers: {total_count}")
        print()
        
        # Process in batches of 50
        batch_size = 50
        total_batches = (total_count + batch_size - 1) // batch_size
        
        for batch_num in range(1, total_batches + 1):
            start_id = (batch_num - 1) * batch_size + 1
            end_id = min(batch_num * batch_size, total_count)
            
            batch_results, batch_high_conf = self.process_batch(start_id, end_id, batch_num, total_batches)
            
            # Show running totals
            print(f"\n📈 RUNNING TOTALS:")
            print(f"   Progress: {self.processing_stats['total_processed']}/{total_count}")
            print(f"   Success Rate: {self.processing_stats['successful_runs']}/{self.processing_stats['total_processed']}")
            print(f"   🎯 High Confidence Found: {self.processing_stats['high_confidence_found']}")
        
        return self.high_confidence_results
    
    def generate_final_report(self):
        """Generate final high-confidence report."""
        
        print(f"\n🏆 FINAL HIGH CONFIDENCE REPORT")
        print("=" * 80)
        
        if not self.high_confidence_results:
            print("❌ No high-confidence predictions (75%+) found.")
            print("💡 This is normal - 75%+ confidence is very rare in legitimate lottery predictions.")
            return
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(self.high_confidence_results)
        
        print(f"🎉 FOUND {len(self.high_confidence_results)} HIGH-CONFIDENCE PREDICTIONS!")
        print()
        
        # Summary by game
        print("📊 BREAKDOWN BY GAME:")
        print("-" * 40)
        for game in self.target_games:
            game_preds = df[df['game'] == game] if len(df) > 0 else pd.DataFrame()
            count = len(game_preds)
            if count > 0:
                avg_conf = game_preds['confidence'].mean() * 100
                print(f"  🎲 {game}: {count} predictions (avg {avg_conf:.1f}% confidence)")
            else:
                print(f"  🎲 {game}: 0 predictions")
        
        print()
        
        # Top predictions
        if len(df) > 0:
            print("🏆 TOP HIGH-CONFIDENCE PREDICTIONS:")
            print("=" * 80)
            
            df_sorted = df.sort_values('confidence', ascending=False)
            
            for game in self.target_games:
                game_df = df_sorted[df_sorted['game'] == game]
                if len(game_df) > 0:
                    print(f"\n🎯 {game.upper()} HIGH-CONFIDENCE PREDICTIONS:")
                    print("-" * 50)
                    
                    for idx, row in game_df.head(10).iterrows():
                        print(f"  🔥 {row['subscriber_id']}: {row['numbers']} ({row['confidence_percent']}) - {row['my_odds']}")
        
        # Save report
        self.save_final_report(df if len(df) > 0 else pd.DataFrame())
    
    def save_final_report(self, df):
        """Save final report files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save CSV
        csv_file = self.project_root / f"december_high_confidence_predictions_{timestamp}.csv"
        
        if len(df) > 0:
            df_sorted = df.sort_values('confidence', ascending=False)
            df_sorted.to_csv(csv_file, index=False)
            
            # Save JSON summary
            json_file = self.project_root / f"december_high_confidence_summary_{timestamp}.json"
            
            summary_data = {
                "analysis_date": datetime.now().isoformat(),
                "target_date": self.target_date,
                "confidence_threshold": f"{self.confidence_threshold*100:.0f}%",
                "total_predictions": len(df),
                "processing_stats": self.processing_stats,
                "games_breakdown": {
                    game: len(df[df['game'] == game]) for game in self.target_games
                },
                "top_predictions": df_sorted.head(50).to_dict('records')
            }
            
            with open(json_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            
            print(f"\n📄 CSV Report: {csv_file}")
            print(f"📄 JSON Summary: {json_file}")
        else:
            # Create empty report showing we processed but found no 75%+ predictions
            empty_summary = {
                "analysis_date": datetime.now().isoformat(),
                "target_date": self.target_date,
                "confidence_threshold": f"{self.confidence_threshold*100:.0f}%",
                "total_predictions": 0,
                "processing_stats": self.processing_stats,
                "note": "No predictions found at 75%+ confidence threshold. This is normal for legitimate lottery prediction systems."
            }
            
            json_file = self.project_root / f"december_analysis_no_high_confidence_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(empty_summary, f, indent=2)
            
            print(f"📄 Analysis Report: {json_file}")

def main():
    """Main execution."""
    finder = DecemberHighConfidenceFinder()
    
    # Run all 2000 subscribers
    high_confidence_predictions = finder.run_all_subscribers(2000)
    
    # Generate final report
    finder.generate_final_report()
    
    print("\n" + "=" * 80)
    print("✅ DECEMBER HIGH-CONFIDENCE ANALYSIS COMPLETE!")

if __name__ == "__main__":
    main()