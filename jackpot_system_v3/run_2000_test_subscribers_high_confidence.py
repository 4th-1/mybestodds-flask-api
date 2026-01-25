#!/usr/bin/env python3
"""
run_2000_test_subscribers_high_confidence.py

Process 2000 test subscribers and filter for high-confidence predictions (75-100%)
Targets: Cash 3, Cash 4, Cash4Life, Mega Millions for December 22, 2025
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

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
TEST_SUBSCRIBER_COUNT = 2000
TARGET_GAMES = ["Cash3", "Cash4", "Cash4Life", "MegaMillions"]
CONFIDENCE_THRESHOLD = 0.75  # 75% minimum confidence
MAX_CONCURRENT_JOBS = 8  # Parallel processing limit

class HighConfidenceFinder:
    """Find and analyze high-confidence predictions from test subscribers."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.subscribers_dir = self.project_root / "data" / "subscribers" / "BOOK3_TEST"
        self.outputs_dir = self.project_root / "outputs"
        self.high_confidence_results = {
            "Cash3": [],
            "Cash4": [], 
            "Cash4Life": [],
            "MegaMillions": []
        }
        self.processing_stats = {
            "total_subscribers": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "high_confidence_found": 0
        }
        self.lock = threading.Lock()
    
    def run_single_subscriber(self, subscriber_id: int) -> tuple:
        """Run processing for a single test subscriber."""
        subscriber_file = f"TEST{subscriber_id:04d}_BOOK3.json"
        
        try:
            # Run the prediction system
            cmd = ["python", "run_kit_v3.py", f"BOOK3_TEST/{subscriber_file}", "BOOK3_TEST"]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout per subscriber
            )
            
            if result.returncode == 0:
                return (subscriber_id, "success", None)
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                return (subscriber_id, "failed", error_msg)
                
        except subprocess.TimeoutExpired:
            return (subscriber_id, "timeout", "Processing timeout (>3 minutes)")
        except Exception as e:
            return (subscriber_id, "error", str(e))
    
    def extract_high_confidence_predictions(self, subscriber_id: int) -> dict:
        """Extract high-confidence predictions from subscriber output."""
        # Find the output directory for this subscriber
        test_id = f"TEST{subscriber_id:04d}"
        
        # Look for output directory pattern
        output_pattern = f"BOOK3_TEST_{test_id}_2025-12-22_to_2025-12-31"
        output_dir = None
        
        for d in self.outputs_dir.iterdir():
            if d.is_dir() and output_pattern in d.name:
                output_dir = d
                break
        
        if not output_dir:
            return {}
        
        # Read today's predictions (2025-12-22.json)
        today_file = output_dir / "2025-12-22.json"
        if not today_file.exists():
            return {}
        
        try:
            with open(today_file, 'r') as f:
                daily_data = json.load(f)
            
            high_confidence_picks = {}
            picks = daily_data.get("picks", {})
            
            for game, game_picks in picks.items():
                if game not in TARGET_GAMES:
                    continue
                
                # Get all predictions for this game
                lane_system = game_picks.get("lane_system", [])
                lane_mmfsn = game_picks.get("lane_mmfsn", [])
                
                all_picks = lane_system + lane_mmfsn
                
                for pick in all_picks:
                    # For test subscribers, we'll use a mock confidence calculation
                    # based on score components (in real system this would come from the prediction engine)
                    base_score = daily_data.get("score", 50)
                    
                    # Convert score to confidence (normalized)
                    confidence = min(base_score / 100.0, 1.0)
                    
                    if confidence >= CONFIDENCE_THRESHOLD:
                        if game not in high_confidence_picks:
                            high_confidence_picks[game] = []
                        
                        high_confidence_picks[game].append({
                            "subscriber_id": test_id,
                            "numbers": pick,
                            "confidence": confidence,
                            "confidence_percent": f"{confidence*100:.1f}%",
                            "my_odds": self._calculate_my_odds(game, confidence),
                            "score_components": daily_data.get("score_components", {}),
                            "date": "2025-12-22"
                        })
            
            return high_confidence_picks
            
        except Exception as e:
            print(f"Error extracting predictions for {test_id}: {e}")
            return {}
    
    def _calculate_my_odds(self, game: str, confidence: float) -> str:
        """Calculate 'My Best Odds' based on game and confidence."""
        base_odds = {
            "Cash3": 1000,
            "Cash4": 10000,
            "Cash4Life": 21846048,
            "MegaMillions": 302575350
        }
        
        if game not in base_odds:
            return "Unknown"
        
        # Improve odds based on confidence
        improved_odds = int(base_odds[game] * (1.0 - confidence * 0.8))
        return f"1 in {improved_odds:,}"
    
    def process_batch(self, subscriber_ids: list) -> None:
        """Process a batch of subscribers in parallel."""
        
        print(f"🚀 Processing batch of {len(subscriber_ids)} subscribers...")
        
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS) as executor:
            # Submit all jobs
            future_to_id = {
                executor.submit(self.run_single_subscriber, sub_id): sub_id 
                for sub_id in subscriber_ids
            }
            
            # Process completed jobs
            for future in as_completed(future_to_id):
                subscriber_id = future_to_id[future]
                
                try:
                    sub_id, status, error = future.result()
                    
                    with self.lock:
                        self.processing_stats["total_subscribers"] += 1
                        
                        if status == "success":
                            self.processing_stats["successful_runs"] += 1
                            
                            # Extract high-confidence predictions
                            high_conf_picks = self.extract_high_confidence_predictions(sub_id)
                            
                            if high_conf_picks:
                                self.processing_stats["high_confidence_found"] += 1
                                
                                # Add to results
                                for game, picks in high_conf_picks.items():
                                    self.high_confidence_results[game].extend(picks)
                            
                            print(f"  ✅ TEST{sub_id:04d} - High confidence picks: {len(high_conf_picks)}")
                        else:
                            self.processing_stats["failed_runs"] += 1
                            print(f"  ❌ TEST{sub_id:04d} - {status}: {error}")
                
                except Exception as e:
                    with self.lock:
                        self.processing_stats["failed_runs"] += 1
                    print(f"  💥 TEST{subscriber_id:04d} - Exception: {e}")
    
    def run_full_analysis(self):
        """Run the complete 2000 subscriber analysis."""
        
        print("🎯 MY BEST ODDS - 2000 TEST SUBSCRIBER HIGH CONFIDENCE ANALYSIS")
        print("=" * 80)
        print(f"📅 Date: December 22, 2025")
        print(f"🎮 Target Games: {', '.join(TARGET_GAMES)}")
        print(f"📊 Confidence Threshold: {CONFIDENCE_THRESHOLD*100}%+")
        print(f"👥 Total Subscribers: {TEST_SUBSCRIBER_COUNT}")
        print()
        
        start_time = time.time()
        
        # Process in batches to manage system resources
        batch_size = 50
        all_subscriber_ids = list(range(1, TEST_SUBSCRIBER_COUNT + 1))
        
        for i in range(0, len(all_subscriber_ids), batch_size):
            batch = all_subscriber_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_subscriber_ids) + batch_size - 1) // batch_size
            
            print(f"\n📦 BATCH {batch_num}/{total_batches} (TEST{batch[0]:04d}-TEST{batch[-1]:04d})")
            print("-" * 50)
            
            self.process_batch(batch)
            
            # Progress update
            print(f"   Progress: {self.processing_stats['total_subscribers']}/{TEST_SUBSCRIBER_COUNT}")
            print(f"   Success Rate: {self.processing_stats['successful_runs']}/{self.processing_stats['total_subscribers']}")
            print(f"   High Confidence Found: {self.processing_stats['high_confidence_found']}")
        
        elapsed_time = time.time() - start_time
        
        # Generate final report
        self.generate_final_report(elapsed_time)
    
    def generate_final_report(self, elapsed_time: float):
        """Generate comprehensive high-confidence results report."""
        
        print("\n" + "=" * 80)
        print("🏆 FINAL HIGH CONFIDENCE RESULTS - SMART LOGIC SYSTEM")
        print("=" * 80)
        
        # Processing Summary
        print(f"⏱️  Total Processing Time: {elapsed_time/60:.1f} minutes")
        print(f"📊 Processing Success Rate: {self.processing_stats['successful_runs']}/{self.processing_stats['total_subscribers']} ({self.processing_stats['successful_runs']/max(self.processing_stats['total_subscribers'],1)*100:.1f}%)")
        print(f"🎯 High Confidence Subscribers: {self.processing_stats['high_confidence_found']}")
        print()
        
        # Results by game
        for game in TARGET_GAMES:
            picks = self.high_confidence_results[game]
            
            if not picks:
                print(f"🔴 {game}: No high confidence predictions found")
                continue
            
            print(f"🟢 {game}: {len(picks)} high confidence predictions")
            print("-" * 40)
            
            # Sort by confidence
            sorted_picks = sorted(picks, key=lambda x: x['confidence'], reverse=True)
            
            # Show top 10
            for i, pick in enumerate(sorted_picks[:10], 1):
                print(f"  #{i:2d}. {pick['subscriber_id']} | {pick['numbers']} | {pick['confidence_percent']} | {pick['my_odds']}")
            
            if len(sorted_picks) > 10:
                print(f"       ... and {len(sorted_picks) - 10} more predictions")
            print()
        
        # Save detailed results
        self.save_detailed_results()
        
        print("📁 Detailed results saved to: high_confidence_results_2025-12-22.json")
        print("🎉 Analysis Complete!")
    
    def save_detailed_results(self):
        """Save detailed results to JSON file."""
        
        output_data = {
            "analysis_date": "2025-12-22",
            "confidence_threshold": f"{CONFIDENCE_THRESHOLD*100}%",
            "processing_stats": self.processing_stats,
            "target_games": TARGET_GAMES,
            "high_confidence_predictions": self.high_confidence_results,
            "summary": {
                game: {
                    "total_predictions": len(picks),
                    "top_confidence": max([p['confidence'] for p in picks]) if picks else 0,
                    "avg_confidence": sum([p['confidence'] for p in picks]) / len(picks) if picks else 0
                }
                for game, picks in self.high_confidence_results.items()
            }
        }
        
        output_file = self.project_root / "high_confidence_results_2025-12-22.json"
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

def main():
    """Main execution function."""
    
    finder = HighConfidenceFinder()
    
    try:
        finder.run_full_analysis()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        print(f"📊 Partial results: {finder.processing_stats}")
    except Exception as e:
        print(f"\n💥 Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()