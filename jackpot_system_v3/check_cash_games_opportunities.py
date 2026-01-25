#!/usr/bin/env python3
"""
Cash Games Opportunity Scanner
==============================
Checks for strong Cash3, Cash4, and Cash4Life opportunities tonight
"""

import json
from pathlib import Path

def check_cash_games_opportunities():
    """Check existing test subscriber outputs for Cash3, Cash4, and Cash4Life opportunities."""
    
    print("🎯 SCANNING FOR STRONG CASH GAMES OPPORTUNITIES")
    print("=" * 55)
    
    outputs_dir = Path("outputs")
    opportunities = {
        "Cash3": [],
        "Cash4": [],
        "Cash4Life": []
    }
    
    # Check all existing test outputs
    for output_dir in outputs_dir.iterdir():
        if output_dir.is_dir() and "BOOK3_TEST" in output_dir.name:
            
            # Extract subscriber ID
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
                    
                    overall_score = data.get("score", 0)
                    score_components = data.get("score_components", {})
                    
                    # Check each cash game
                    if "picks" in data:
                        for game in ["Cash3", "Cash4", "Cash4Life"]:
                            if game in data["picks"] and "lane_system" in data["picks"][game]:
                                picks = data["picks"][game]["lane_system"]
                                
                                opportunities[game].append({
                                    "subscriber_id": subscriber_id,
                                    "confidence": overall_score,
                                    "predictions": picks,
                                    "score_components": score_components,
                                    "astro_score": score_components.get("astro", 0),
                                    "mmfsn_score": score_components.get("mmfsn", 0),
                                    "stats_score": score_components.get("stats", 0),
                                    "numerology_score": score_components.get("numerology", 0)
                                })
                        
                except Exception as e:
                    print(f"   ❌ Error reading {subscriber_id}: {e}")
                    continue
    
    # Analyze each game
    all_strong_opportunities = []
    
    for game_name, game_opportunities in opportunities.items():
        if not game_opportunities:
            continue
            
        # Sort by confidence score
        game_opportunities.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"\n🎲 {game_name.upper()} ANALYSIS:")
        print("-" * 30)
        
        strong_ops = []
        moderate_ops = []
        
        for i, opp in enumerate(game_opportunities, 1):
            confidence = opp["confidence"]
            
            if confidence >= 75.0:
                strong_ops.append(opp)
                strength = "🔥 STRONG"
                all_strong_opportunities.append((game_name, opp))
            elif confidence >= 60.0:
                moderate_ops.append(opp)
                strength = "⚡ MODERATE"
            else:
                strength = "📊 WEAK"
            
            print(f"{i:2}. {opp['subscriber_id']} - {strength}")
            print(f"    Confidence: {confidence:.1f}/100")
            print(f"    Predictions: {opp['predictions']}")
            print(f"    Astro: {opp['astro_score']:.1f} | MMFSN: {opp['mmfsn_score']:.1f} | Stats: {opp['stats_score']:.1f}")
        
        print(f"\n   Summary: {len(strong_ops)} Strong | {len(moderate_ops)} Moderate | {len(game_opportunities)} Total")
    
    # Overall summary
    print("\n" + "=" * 55)
    print("🏆 TONIGHT'S CASH GAMES SUMMARY:")
    
    total_strong = len(all_strong_opportunities)
    print(f"   🔥 Total strong opportunities (75-100%): {total_strong}")
    
    if total_strong > 0:
        print(f"\n✨ BEST CASH GAME OPPORTUNITIES:")
        
        # Sort all strong opportunities by confidence
        all_strong_opportunities.sort(key=lambda x: x[1]["confidence"], reverse=True)
        
        for i, (game, opp) in enumerate(all_strong_opportunities, 1):
            print(f"   {i}. {game} - {opp['subscriber_id']} ({opp['confidence']:.1f}%)")
            print(f"      Top pick: {opp['predictions'][0]}")
            
    else:
        print(f"   ⚠️  NO STRONG OPPORTUNITIES (75-100%) found for any cash games tonight")
        
        # Find best moderate opportunities across all games
        all_moderate = []
        for game_name, game_opportunities in opportunities.items():
            for opp in game_opportunities:
                if 60.0 <= opp["confidence"] < 75.0:
                    all_moderate.append((game_name, opp))
        
        if all_moderate:
            all_moderate.sort(key=lambda x: x[1]["confidence"], reverse=True)
            best_game, best_opp = all_moderate[0]
            print(f"   Best moderate option: {best_game} - {best_opp['subscriber_id']} ({best_opp['confidence']:.1f}%)")
            print(f"   Pick: {best_opp['predictions'][0]}")
        else:
            print(f"   All cash game opportunities are below 60% confidence")
    
    return all_strong_opportunities

def check_specific_game_details():
    """Show detailed breakdown for the best opportunities in each cash game."""
    
    print(f"\n🔍 DETAILED CASH GAME BREAKDOWN:")
    print("=" * 40)
    
    # Check TEST0001 (Katherine) details
    outputs_dir = Path("outputs")
    test_dir = outputs_dir / "BOOK3_TEST_TEST0001_2025-12-22_to_2025-12-31"
    
    if test_dir.exists():
        today_file = test_dir / "2025-12-23.json"
        if today_file.exists():
            with open(today_file, 'r') as f:
                data = json.load(f)
            
            print(f"📊 TEST0001 (Katherine) - Overall Score: {data['score']:.1f}")
            print(f"   🎯 Cash3: {data['picks']['Cash3']['lane_system']}")
            print(f"   🎯 Cash4: {data['picks']['Cash4']['lane_system']}")
            print(f"   🎯 Cash4Life: {data['picks']['Cash4Life']['lane_system']}")
            
            components = data['score_components']
            print(f"   📈 Key Scores: Astro({components['astro']:.1f}) | Stats({components['stats']:.1f}) | MMFSN({components['mmfsn']:.1f})")
    
    # Check TEST0050 (Catherine) details  
    test_dir2 = outputs_dir / "BOOK3_TEST_TEST0050_2025-12-22_to_2025-12-31"
    if test_dir2.exists():
        today_file = test_dir2 / "2025-12-23.json"
        if today_file.exists():
            with open(today_file, 'r') as f:
                data = json.load(f)
            
            print(f"\n📊 TEST0050 (Catherine) - Overall Score: {data['score']:.1f}")
            print(f"   🎯 Cash3: {data['picks']['Cash3']['lane_system']}")
            print(f"   🎯 Cash4: {data['picks']['Cash4']['lane_system']}")
            print(f"   🎯 Cash4Life: {data['picks']['Cash4Life']['lane_system']}")

if __name__ == "__main__":
    strong_opportunities = check_cash_games_opportunities()
    check_specific_game_details()