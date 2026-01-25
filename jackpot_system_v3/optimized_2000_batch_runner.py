#!/usr/bin/env python3
"""
Optimized 2000 Test Subscribers Runner
=====================================
Processes 2000 test subscribers efficiently with progress tracking and high confidence filtering.
Targets: Cash3, Cash4, Cash4Life, MegaMillions for December 23, 2025
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import threading

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class OptimizedBatch2000Runner:
    """Optimized batch runner for 2000 test subscribers."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.subscribers_dir = self.project_root / "data" / "subscribers" / "BOOK3_TEST"
        self.outputs_dir = self.project_root / "outputs"
        self.python_exe = "C:/MyBestOdds/.venv/Scripts/python.exe"
        
        # Processing configuration
        self.batch_size = 50  # Process in batches of 50
        self.max_workers = 4  # Parallel workers
        self.confidence_threshold = 0.75  # 75% minimum
        
        # Results tracking
        self.high_confidence_results = {
            "Cash3": [],
            "Cash4": [],
            "Cash4Life": [],
            "MegaMillions": []
        }
        
        self.processing_stats = {
            "total_processed": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "high_confidence_found": 0,
            "batch_number": 0
        }
    
    def run_single_subscriber(self, subscriber_id):
        """Run a single test subscriber and return results."""
        
        subscriber_file = f"data/subscribers/BOOK3_TEST/TEST{subscriber_id:04d}_BOOK3.json"
        
        try:
            # Run the subscriber
            cmd = [
                self.python_exe,
                "run_kit_v3.py",
                subscriber_file,
                "BOOK3_TEST"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout per subscriber
            )
            
            if result.returncode == 0:
                # Check for high confidence predictions
                return self.check_high_confidence_results(subscriber_id)
            else:
                return {"subscriber_id": subscriber_id, "status": "failed", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"subscriber_id": subscriber_id, "status": "timeout", "error": "Process timed out"}
        except Exception as e:
            return {"subscriber_id": subscriber_id, "status": "error", "error": str(e)}
    
    def check_high_confidence_results(self, subscriber_id):
        """Check if subscriber generated high confidence predictions."""
        
        # Look for output files
        output_pattern = f"BOOK3_TEST_{subscriber_id:04d}_*"
        
        try:
            output_files = list(self.outputs_dir.glob(f"*{output_pattern}*"))
            
            if not output_files:
                return {"subscriber_id": subscriber_id, "status": "no_output"}
            
            # Check the most recent output
            latest_output = max(output_files, key=lambda p: p.stat().st_mtime)
            
            # Look for today's JSON file
            today_file = latest_output / "2025-12-23.json"
            
            if not today_file.exists():
                return {"subscriber_id": subscriber_id, "status": "no_predictions"}
            
            # Load and check predictions
            with open(today_file, 'r') as f:
                data = json.load(f)
            
            high_conf_predictions = []
            
            # Check each game for high confidence
            for game_name in ["Cash3", "Cash4", "Cash4Life", "MegaMillions"]:
                if game_name in data.get("predictions", {}):
                    prediction = data["predictions"][game_name]
                    confidence = prediction.get("confidence", 0.0)
                    
                    if confidence >= self.confidence_threshold:
                        high_conf_predictions.append({
                            "game": game_name,
                            "prediction": prediction.get("prediction", ""),
                            "confidence": confidence,
                            "odds": prediction.get("odds", ""),
                            "band": prediction.get("band", "")
                        })
            
            return {
                "subscriber_id": subscriber_id,
                "status": "success",
                "high_confidence_count": len(high_conf_predictions),
                "high_confidence_predictions": high_conf_predictions,
                "output_dir": str(latest_output)
            }
            
        except Exception as e:
            return {"subscriber_id": subscriber_id, "status": "analysis_error", "error": str(e)}
    
    def run_batch(self, batch_start, batch_size):
        """Run a batch of subscribers."""
        
        batch_end = min(batch_start + batch_size, 2000)
        self.processing_stats["batch_number"] += 1
        
        print(f"\n🎯 BATCH {self.processing_stats['batch_number']}: Processing subscribers {batch_start+1}-{batch_end}")
        print("=" * 60)
        
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs in this batch
            futures = {
                executor.submit(self.run_single_subscriber, i + 1): i + 1 
                for i in range(batch_start, batch_end)
            }
            
            # Collect results
            batch_results = []
            for future in as_completed(futures):
                subscriber_id = futures[future]
                try:
                    result = future.result()
                    batch_results.append(result)
                    
                    # Update stats
                    self.processing_stats["total_processed"] += 1
                    
                    if result["status"] == "success":
                        self.processing_stats["successful_runs"] += 1
                        if result["high_confidence_count"] > 0:
                            self.processing_stats["high_confidence_found"] += 1
                            
                            # Store high confidence results
                            for pred in result["high_confidence_predictions"]:
                                self.high_confidence_results[pred["game"]].append({
                                    "subscriber_id": subscriber_id,
                                    "prediction": pred["prediction"],
                                    "confidence": pred["confidence"],
                                    "odds": pred["odds"],
                                    "band": pred["band"]
                                })
                    else:
                        self.processing_stats["failed_runs"] += 1
                    
                    # Progress indicator
                    if self.processing_stats["total_processed"] % 10 == 0:
                        print(f"   ✅ Processed: {self.processing_stats['total_processed']}/2000")
                        
                except Exception as e:
                    print(f"   ❌ Error processing subscriber {subscriber_id}: {e}")
                    self.processing_stats["failed_runs"] += 1
        
        batch_time = time.time() - start_time
        print(f"   ⏱️ Batch completed in {batch_time:.1f} seconds")
        
        return batch_results
    
    def run_all_2000_subscribers(self):
        """Run all 2000 test subscribers."""
        
        print("🚀 STARTING 2000 TEST SUBSCRIBERS HIGH CONFIDENCE ANALYSIS")
        print("=" * 80)
        print(f"📊 Configuration:")
        print(f"   • Total subscribers: 2000")
        print(f"   • Batch size: {self.batch_size}")
        print(f"   • Parallel workers: {self.max_workers}")
        print(f"   • Confidence threshold: {self.confidence_threshold * 100}%")
        print(f"   • Target games: Cash3, Cash4, Cash4Life, MegaMillions")
        print(f"   • Target date: December 23, 2025")
        
        start_time = time.time()
        
        # Process in batches
        for batch_start in range(0, 2000, self.batch_size):
            try:
                self.run_batch(batch_start, self.batch_size)
                
                # Brief pause between batches to prevent system overload
                time.sleep(2)
                
                # Show intermediate summary
                self.show_intermediate_summary()
                
            except KeyboardInterrupt:
                print("\n⚠️ Processing interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error in batch starting at {batch_start}: {e}")
                continue
        
        total_time = time.time() - start_time
        
        # Final summary and save results
        self.show_final_summary(total_time)
        self.save_high_confidence_results()
    
    def show_intermediate_summary(self):
        """Show intermediate processing summary."""
        
        total = self.processing_stats["total_processed"]
        success = self.processing_stats["successful_runs"]
        high_conf = self.processing_stats["high_confidence_found"]
        
        if total > 0:
            success_rate = (success / total) * 100
            high_conf_rate = (high_conf / total) * 100
            
            print(f"   📈 INTERMEDIATE SUMMARY:")
            print(f"      Processed: {total}/2000 ({total/2000*100:.1f}%)")
            print(f"      Success rate: {success_rate:.1f}%")
            print(f"      High confidence found: {high_conf} subscribers ({high_conf_rate:.1f}%)")
            
            # Game breakdown
            for game, predictions in self.high_confidence_results.items():
                if predictions:
                    print(f"      {game}: {len(predictions)} predictions")
    
    def show_final_summary(self, total_time):
        """Show final processing summary."""
        
        print(f"\n{'='*80}")
        print("🏆 FINAL SUMMARY - 2000 TEST SUBSCRIBERS HIGH CONFIDENCE ANALYSIS")
        print(f"{'='*80}")
        
        total = self.processing_stats["total_processed"]
        success = self.processing_stats["successful_runs"]
        failed = self.processing_stats["failed_runs"]
        high_conf = self.processing_stats["high_confidence_found"]
        
        print(f"📊 PROCESSING STATISTICS:")
        print(f"   • Total processed: {total}/2000 ({total/2000*100:.1f}%)")
        print(f"   • Successful runs: {success} ({success/total*100:.1f}%)")
        print(f"   • Failed runs: {failed} ({failed/total*100:.1f}%)")
        print(f"   • High confidence found: {high_conf} subscribers ({high_conf/total*100:.1f}%)")
        print(f"   • Total processing time: {total_time/60:.1f} minutes")
        print(f"   • Average per subscriber: {total_time/total:.2f} seconds")
        
        print(f"\n🎯 HIGH CONFIDENCE PREDICTIONS BY GAME:")
        
        total_predictions = 0
        for game, predictions in self.high_confidence_results.items():
            count = len(predictions)
            total_predictions += count
            print(f"   • {game}: {count} predictions")
            
            if count > 0:
                # Show top 3 predictions by confidence
                sorted_predictions = sorted(predictions, key=lambda x: x["confidence"], reverse=True)
                print(f"      Top predictions:")
                for i, pred in enumerate(sorted_predictions[:3], 1):
                    print(f"         {i}. {pred['prediction']} (conf: {pred['confidence']:.1%}, odds: {pred['odds']})")
        
        print(f"\n🏆 TOTAL HIGH CONFIDENCE PREDICTIONS: {total_predictions}")
        
        if total_predictions > 0:
            print(f"\n🎉 SUCCESS! Found {total_predictions} high confidence predictions from {high_conf} subscribers!")
            print(f"📈 High confidence rate: {high_conf/total*100:.1f}% of processed subscribers")
        else:
            print(f"\n⚠️ No high confidence predictions found. Consider lowering threshold or checking system.")
    
    def save_high_confidence_results(self):
        """Save high confidence results to file."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.project_root / f"high_confidence_results_2000_{timestamp}.json"
        
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "processing_stats": self.processing_stats,
            "confidence_threshold": self.confidence_threshold,
            "high_confidence_predictions": self.high_confidence_results,
            "summary": {
                "total_predictions": sum(len(preds) for preds in self.high_confidence_results.values()),
                "subscribers_with_high_confidence": self.processing_stats["high_confidence_found"],
                "games_covered": [game for game, preds in self.high_confidence_results.items() if preds]
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n💾 Results saved: {results_file.name}")
        
        # Also create a simple CSV for easy analysis
        csv_file = self.project_root / f"high_confidence_summary_2000_{timestamp}.csv"
        
        with open(csv_file, 'w') as f:
            f.write("Game,Subscriber_ID,Prediction,Confidence,Odds,Band\n")
            
            for game, predictions in self.high_confidence_results.items():
                for pred in predictions:
                    f.write(f"{game},{pred['subscriber_id']},{pred['prediction']},{pred['confidence']:.3f},{pred['odds']},{pred['band']}\n")
        
        print(f"📊 CSV summary saved: {csv_file.name}")
        
        return results_file

def main():
    """Main execution function."""
    
    print("🎯 OPTIMIZED 2000 TEST SUBSCRIBERS RUNNER")
    print("=" * 60)
    
    runner = OptimizedBatch2000Runner()
    
    try:
        runner.run_all_2000_subscribers()
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        if runner.processing_stats["total_processed"] > 0:
            print("Saving partial results...")
            runner.save_high_confidence_results()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()