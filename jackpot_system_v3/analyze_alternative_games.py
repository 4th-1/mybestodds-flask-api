#!/usr/bin/env python3
"""
ALTERNATIVE GAMES ANALYSIS - December 23, 2025
============================================
Analyzing Cash3, Cash4, and Cash4Life opportunities from VIP BOOK3 subscribers
"""

import json
from pathlib import Path

def analyze_alternative_games():
    """Analyze Cash3, Cash4, and Cash4Life predictions from VIP subscribers."""
    
    print("🎯 ALTERNATIVE GAMES ANALYSIS - DECEMBER 23, 2025")
    print("=" * 55)
    print("🔍 Searching for stronger opportunities beyond MegaMillions...")
    
    outputs_dir = Path("outputs")
    
    subscribers = {
        "JDS": {
            "name": "Joseph David Smith", 
            "dir": "BOOK3_JDS_BOOK3_2025-12-22_to_2025-12-31"
        },
        "AJS": {
            "name": "Adonna Janay Smith", 
            "dir": "BOOK3_AJS_2025-12-22_to_2025-12-31"
        },
        "YRS": {
            "name": "Yolanda Renee Smith", 
            "dir": "BOOK3_YRS_BOOK3_2025-12-22_to_2025-12-31"
        }
    }
    
    game_analysis = {
        "Cash3": {"predictions": [], "confidence_scores": []},
        "Cash4": {"predictions": [], "confidence_scores": []},
        "Cash4Life": {"predictions": [], "confidence_scores": []},
        "Powerball": {"predictions": [], "confidence_scores": []}
    }
    
    print(f"\n📊 DETAILED GAME ANALYSIS:")
    print("-" * 55)
    
    for code, info in subscribers.items():
        subscriber_dir = outputs_dir / info["dir"]
        today_file = subscriber_dir / "2025-12-23.json"
        
        if today_file.exists():
            try:
                with open(today_file, 'r') as f:
                    data = json.load(f)
                
                overall_score = data.get("score", 0)
                score_components = data.get("score_components", {})
                
                print(f"\n👤 {code} - {info['name']} (Overall: {overall_score:.1f}%)")
                
                if "picks" in data:
                    # Analyze each game
                    for game_name in ["Cash3", "Cash4", "Cash4Life", "Powerball"]:
                        if game_name in data["picks"]:
                            picks = data["picks"][game_name]["lane_system"]
                            
                            # Store for analysis
                            game_analysis[game_name]["predictions"].extend([
                                {"subscriber": code, "pick": pick, "confidence": overall_score}
                                for pick in picks
                            ])
                            game_analysis[game_name]["confidence_scores"].append(overall_score)
                            
                            # Calculate game-specific strength
                            if game_name == "Cash3":
                                # Cash3 typically has better odds
                                game_strength = overall_score * 1.2  # Boost for better odds
                                strength_emoji = "💰" if game_strength >= 65 else "💵" if game_strength >= 55 else "📊"
                            elif game_name == "Cash4":
                                game_strength = overall_score * 1.1  # Slight boost
                                strength_emoji = "💰" if game_strength >= 65 else "💵" if game_strength >= 55 else "📊"
                            elif game_name == "Cash4Life":
                                game_strength = overall_score * 0.95  # Slight reduction (harder odds)
                                strength_emoji = "🌟" if game_strength >= 65 else "⭐" if game_strength >= 55 else "📊"
                            else:  # Powerball
                                game_strength = overall_score * 0.9  # Harder odds
                                strength_emoji = "⚡" if game_strength >= 65 else "🔋" if game_strength >= 55 else "📊"
                            
                            print(f"   {strength_emoji} {game_name}: {picks[0]} (Adj. Strength: {game_strength:.1f}%)")
                            if len(picks) > 1:
                                print(f"      Secondary: {picks[1]}")
                
            except Exception as e:
                print(f"❌ Error reading {code} predictions: {e}")
    
    # Game-by-game opportunity analysis
    print(f"\n{'='*55}")
    print("🏆 GAME OPPORTUNITY RANKINGS")
    print(f"{'='*55}")
    
    game_opportunities = []
    
    for game_name, data in game_analysis.items():
        if data["confidence_scores"]:
            avg_confidence = sum(data["confidence_scores"]) / len(data["confidence_scores"])
            max_confidence = max(data["confidence_scores"])
            
            # Apply game-specific multipliers for realistic assessment
            if game_name == "Cash3":
                adjusted_strength = avg_confidence * 1.2
                odds_info = "1:1,000 odds"
            elif game_name == "Cash4":
                adjusted_strength = avg_confidence * 1.1
                odds_info = "1:10,000 odds"
            elif game_name == "Cash4Life":
                adjusted_strength = avg_confidence * 0.95
                odds_info = "1:21M+ odds"
            elif game_name == "Powerball":
                adjusted_strength = avg_confidence * 0.9
                odds_info = "1:292M+ odds"
            else:
                adjusted_strength = avg_confidence
                odds_info = "Variable odds"
            
            game_opportunities.append({
                "game": game_name,
                "avg_confidence": avg_confidence,
                "max_confidence": max_confidence,
                "adjusted_strength": adjusted_strength,
                "odds_info": odds_info,
                "predictions": data["predictions"]
            })
    
    # Sort by adjusted strength
    game_opportunities.sort(key=lambda x: x["adjusted_strength"], reverse=True)
    
    print(f"\n🎯 TONIGHT'S BEST OPPORTUNITIES:")
    
    for i, opp in enumerate(game_opportunities, 1):
        game = opp["game"]
        adj_strength = opp["adjusted_strength"]
        
        if adj_strength >= 65.0:
            strength_level = "🔥 STRONG"
        elif adj_strength >= 55.0:
            strength_level = "⚡ MODERATE"
        else:
            strength_level = "📊 WEAK"
        
        print(f"\n{i}. {game} - {strength_level}")
        print(f"   📈 Adjusted Strength: {adj_strength:.1f}%")
        print(f"   📊 Raw Confidence: {opp['avg_confidence']:.1f}% (Max: {opp['max_confidence']:.1f}%)")
        print(f"   🎲 {opp['odds_info']}")
        
        # Show top predictions
        best_predictions = sorted(opp["predictions"], key=lambda x: x["confidence"], reverse=True)[:3]
        print(f"   🎯 Top Picks:")
        for j, pred in enumerate(best_predictions, 1):
            print(f"      {j}. {pred['pick']} ({pred['subscriber']})")
    
    # Best opportunity recommendation
    if game_opportunities:
        best_game = game_opportunities[0]
        print(f"\n{'='*55}")
        print("🏆 TONIGHT'S BEST ALTERNATIVE OPPORTUNITY")
        print(f"{'='*55}")
        
        print(f"🎯 Game: {best_game['game']}")
        print(f"📈 Adjusted Strength: {best_game['adjusted_strength']:.1f}%")
        print(f"🎲 {best_game['odds_info']}")
        
        best_pick = max(best_game["predictions"], key=lambda x: x["confidence"])
        print(f"🏅 Best Pick: {best_pick['pick']} (from {best_pick['subscriber']})")
        
        if best_game["adjusted_strength"] >= 65.0:
            print(f"✅ RECOMMENDATION: STRONG PLAY - Good opportunity!")
        elif best_game["adjusted_strength"] >= 55.0:
            print(f"⚡ RECOMMENDATION: MODERATE PLAY - Consider this game")
        else:
            print(f"⚠️ RECOMMENDATION: WEAK NIGHT - All games below optimal thresholds")
        
        # Compare to MegaMillions baseline
        print(f"\n📊 COMPARISON TO MEGAMILLIONS:")
        mm_baseline = 54.3  # AJS was the best MM performer
        if best_game["adjusted_strength"] > mm_baseline + 5:
            print(f"🔥 {best_game['game']} shows {best_game['adjusted_strength'] - mm_baseline:.1f}% better opportunity than MegaMillions!")
        elif best_game["adjusted_strength"] > mm_baseline:
            print(f"⚡ {best_game['game']} slightly better than MegaMillions (+{best_game['adjusted_strength'] - mm_baseline:.1f}%)")
        else:
            print(f"📊 {best_game['game']} similar to MegaMillions baseline")

if __name__ == "__main__":
    analyze_alternative_games()