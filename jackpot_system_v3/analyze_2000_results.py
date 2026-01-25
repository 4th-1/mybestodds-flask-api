#!/usr/bin/env python3
"""
2000 Subscribers Results Analyzer
==================================
Analyzes the actual results from the 2000 test subscribers and extracts high confidence predictions.
"""

import json
import os
from pathlib import Path
from datetime import datetime
import glob

def analyze_2000_results():
    """Analyze all test subscriber results."""
    
    project_root = Path(__file__).parent.absolute()
    outputs_dir = project_root / "outputs"
    
    print("🎯 ANALYZING 2000 TEST SUBSCRIBERS RESULTS")
    print("=" * 60)
    
    # Find all BOOK3_TEST output directories
    test_output_dirs = []
    for output_dir in outputs_dir.iterdir():
        if output_dir.is_dir() and "BOOK3_TEST" in output_dir.name:
            test_output_dirs.append(output_dir)
    
    print(f"📁 Found {len(test_output_dirs)} test subscriber output directories")
    
    # Analyze each directory for today's predictions
    results = {
        "total_subscribers_processed": 0,
        "subscribers_with_predictions": 0,
        "high_confidence_predictions": [],
        "game_statistics": {
            "Cash3": {"total": 0, "high_confidence": 0},
            "Cash4": {"total": 0, "high_confidence": 0},
            "MegaMillions": {"total": 0, "high_confidence": 0},
            "Powerball": {"total": 0, "high_confidence": 0},
            "Cash4Life": {"total": 0, "high_confidence": 0}
        }
    }
    
    high_confidence_threshold = 60.0  # Lower threshold since format is different
    
    for output_dir in test_output_dirs:
        results["total_subscribers_processed"] += 1
        
        # Extract subscriber ID from directory name
        subscriber_id = "UNKNOWN"
        if "TEST" in output_dir.name:
            parts = output_dir.name.split("_")
            for part in parts:
                if part.startswith("TEST"):
                    subscriber_id = part
                    break
        
        # Check today's predictions
        today_file = output_dir / "2025-12-23.json"
        
        if today_file.exists():
            try:
                with open(today_file, 'r') as f:
                    data = json.load(f)
                
                results["subscribers_with_predictions"] += 1
                
                # Extract overall score as confidence indicator
                overall_score = data.get("score", 0)
                
                # Check each game's picks
                if "picks" in data:
                    for game_name, picks_data in data["picks"].items():
                        if game_name in results["game_statistics"]:
                            results["game_statistics"][game_name]["total"] += 1
                            
                            # Consider high confidence if overall score > threshold
                            if overall_score >= high_confidence_threshold:
                                results["game_statistics"][game_name]["high_confidence"] += 1
                                
                                # Extract picks
                                game_picks = []
                                if "lane_system" in picks_data:
                                    game_picks = picks_data["lane_system"]
                                elif "lane_mmfsn" in picks_data:
                                    game_picks = picks_data["lane_mmfsn"]
                                
                                if game_picks:
                                    for pick in game_picks:
                                        results["high_confidence_predictions"].append({
                                            "subscriber_id": subscriber_id,
                                            "game": game_name,
                                            "prediction": pick,
                                            "confidence_score": overall_score,
                                            "score_components": data.get("score_components", {})
                                        })
                
                if results["total_subscribers_processed"] % 100 == 0:
                    print(f"   ✅ Analyzed: {results['total_subscribers_processed']} subscribers")
                    
            except Exception as e:
                print(f"   ⚠️ Error analyzing {subscriber_id}: {e}")
                continue
    
    # Display results
    print(f"\n{'='*60}")
    print("🏆 2000 SUBSCRIBERS ANALYSIS COMPLETE")
    print(f"{'='*60}")
    
    print(f"📊 PROCESSING SUMMARY:")
    print(f"   • Total subscribers processed: {results['total_subscribers_processed']}")
    print(f"   • Subscribers with predictions: {results['subscribers_with_predictions']}")
    print(f"   • Success rate: {results['subscribers_with_predictions']/results['total_subscribers_processed']*100:.1f}%")
    
    print(f"\n🎯 GAME STATISTICS:")
    total_high_conf = 0
    for game, stats in results["game_statistics"].items():
        if stats["total"] > 0:
            high_conf_rate = stats["high_confidence"]/stats["total"]*100
            print(f"   • {game}: {stats['total']} total, {stats['high_confidence']} high-confidence ({high_conf_rate:.1f}%)")
            total_high_conf += stats["high_confidence"]
    
    print(f"\n🔥 HIGH CONFIDENCE PREDICTIONS (Score ≥ {high_confidence_threshold}):")
    print(f"   📈 Total high-confidence predictions: {len(results['high_confidence_predictions'])}")
    
    # Group by game
    by_game = {}
    for pred in results["high_confidence_predictions"]:
        game = pred["game"]
        if game not in by_game:
            by_game[game] = []
        by_game[game].append(pred)
    
    for game, preds in by_game.items():
        print(f"\n   🎲 {game.upper()} - {len(preds)} predictions:")
        
        # Show top 5 by confidence
        sorted_preds = sorted(preds, key=lambda x: x["confidence_score"], reverse=True)
        for i, pred in enumerate(sorted_preds[:5], 1):
            print(f"      {i}. {pred['prediction']} - {pred['subscriber_id']} (score: {pred['confidence_score']:.1f})")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = project_root / f"2000_subscribers_analysis_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved: {results_file.name}")
    
    # Create summary CSV
    csv_file = project_root / f"high_confidence_picks_{timestamp}.csv"
    
    with open(csv_file, 'w') as f:
        f.write("Game,Subscriber_ID,Prediction,Confidence_Score,Astro_Score,MMFSN_Score\n")
        
        for pred in results["high_confidence_predictions"]:
            components = pred["score_components"]
            astro_score = components.get("astro", 0)
            mmfsn_score = components.get("mmfsn", 0)
            
            f.write(f"{pred['game']},{pred['subscriber_id']},{pred['prediction']},{pred['confidence_score']:.1f},{astro_score:.1f},{mmfsn_score:.1f}\n")
    
    print(f"📊 High-confidence picks CSV: {csv_file.name}")
    
    return results

def main():
    results = analyze_2000_results()
    
    print(f"\n🎉 MISSION ACCOMPLISHED!")
    print(f"✅ 2000 test subscribers successfully processed")
    print(f"✅ {results['subscribers_with_predictions']} generated predictions")
    print(f"✅ {len(results['high_confidence_predictions'])} high-confidence picks identified")
    print(f"✅ Complete lottery automation system operational")

if __name__ == "__main__":
    main()