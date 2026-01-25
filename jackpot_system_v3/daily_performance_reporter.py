#!/usr/bin/env python3
"""
DAILY LOTTERY PERFORMANCE REPORT GENERATOR v3.7
===============================================
Generates comprehensive morning reports analyzing previous day's lottery results
against SMART LOGIC System v3.7 predictions across all games and subscribers.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import requests
from collections import defaultdict, Counter

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

class DailyPerformanceReporter:
    def __init__(self):
        self.api_key = "f07e0e4c35msh56c3e81e00978e0p169979jsn5dcb7a92668b"
        self.api_host = "usa-lottery-results.p.rapidapi.com"
        self.base_url = "https://usa-lottery-results.p.rapidapi.com"
        
        self.game_mapping = {
            "Cash3": "georgia-cash-3",
            "Cash4": "georgia-cash-4", 
            "MegaMillions": "mega-millions",
            "Powerball": "powerball",
            "Cash4Life": "cash4life"
        }
        
        self.outputs_dir = Path("outputs")
        self.reports_dir = Path("daily_reports")
        self.reports_dir.mkdir(exist_ok=True)
        
    def fetch_lottery_results(self, game_id, date_str):
        """Fetch lottery results for specific game and date."""
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        
        url = f"{self.base_url}/api/lottery/{game_id}/draw-date/{date_str}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                print(f"⚠️ No results found for {game_id} on {date_str}")
                return []
        except Exception as e:
            print(f"❌ Error fetching {game_id} results: {e}")
            return []
    
    def get_all_predictions_for_date(self, target_date):
        """Get all subscriber predictions for the target date."""
        predictions = {}
        
        # Search all BOOK3 output directories
        for output_dir in self.outputs_dir.glob("BOOK3_*"):
            if output_dir.is_dir():
                prediction_file = output_dir / f"{target_date}.json"
                if prediction_file.exists():
                    try:
                        with open(prediction_file, 'r') as f:
                            data = json.load(f)
                        
                        subscriber_id = output_dir.name.split('_')[1]
                        predictions[subscriber_id] = {
                            "name": data.get("identity", {}).get("full_name", subscriber_id),
                            "confidence": data.get("score", 0),
                            "picks": data.get("picks", {}),
                            "score_components": data.get("score_components", {})
                        }
                    except Exception as e:
                        print(f"⚠️ Error reading {prediction_file}: {e}")
        
        return predictions
    
    def analyze_cash_game_performance(self, game_name, winning_number, predictions):
        """Analyze Cash3/Cash4 performance against winning number."""
        results = {
            "exact_matches": [],
            "close_matches": [],
            "subscribers_played": 0,
            "total_predictions": 0
        }
        
        for subscriber_id, pred_data in predictions.items():
            if game_name not in pred_data["picks"]:
                continue
                
            results["subscribers_played"] += 1
            subscriber_picks = pred_data["picks"][game_name]["lane_system"]
            results["total_predictions"] += len(subscriber_picks)
            
            for pick in subscriber_picks:
                # Exact match
                if pick == winning_number:
                    results["exact_matches"].append({
                        "subscriber": subscriber_id,
                        "name": pred_data["name"],
                        "pick": pick,
                        "confidence": pred_data["confidence"],
                        "match_type": "EXACT"
                    })
                # Close matches (for Cash3/Cash4)
                elif self.is_close_match(pick, winning_number, game_name):
                    results["close_matches"].append({
                        "subscriber": subscriber_id,
                        "name": pred_data["name"], 
                        "pick": pick,
                        "confidence": pred_data["confidence"],
                        "match_type": self.get_match_type(pick, winning_number, game_name)
                    })
        
        return results
    
    def analyze_jackpot_performance(self, game_name, winning_numbers, predictions):
        """Analyze MegaMillions/Powerball/Cash4Life performance."""
        results = {
            "exact_matches": [],
            "partial_matches": [],
            "subscribers_played": 0,
            "total_predictions": 0,
            "number_frequency": Counter()
        }
        
        # Parse winning numbers
        winning_main, winning_special = self.parse_jackpot_numbers(winning_numbers, game_name)
        
        for subscriber_id, pred_data in predictions.items():
            if game_name not in pred_data["picks"]:
                continue
                
            results["subscribers_played"] += 1
            subscriber_picks = pred_data["picks"][game_name]["lane_system"]
            results["total_predictions"] += len(subscriber_picks)
            
            for pick in subscriber_picks:
                pred_main, pred_special = self.parse_jackpot_numbers(pick, game_name)
                
                # Count predicted numbers for frequency analysis
                if pred_main:
                    results["number_frequency"].update(pred_main)
                if pred_special:
                    results["number_frequency"].update([pred_special])
                
                # Check matches
                main_matches = len(set(pred_main) & set(winning_main)) if pred_main and winning_main else 0
                special_match = pred_special == winning_special if pred_special and winning_special else False
                
                if main_matches >= 2 or special_match:  # Significant match
                    match_data = {
                        "subscriber": subscriber_id,
                        "name": pred_data["name"],
                        "pick": pick,
                        "confidence": pred_data["confidence"],
                        "main_matches": main_matches,
                        "special_match": special_match,
                        "total_main": len(winning_main) if winning_main else 0
                    }
                    
                    if main_matches == len(winning_main) and special_match:
                        results["exact_matches"].append(match_data)
                    else:
                        results["partial_matches"].append(match_data)
        
        return results
    
    def is_close_match(self, prediction, winning, game_name):
        """Check if prediction is a close match to winning number."""
        if game_name in ["Cash3", "Cash4"]:
            pred_digits = list(prediction)
            win_digits = list(winning)
            
            # Box match (same digits, different order)
            if sorted(pred_digits) == sorted(win_digits):
                return True
            
            # One digit off
            matches = sum(1 for p, w in zip(pred_digits, win_digits) if p == w)
            return matches >= len(win_digits) - 1
        
        return False
    
    def get_match_type(self, prediction, winning, game_name):
        """Determine the type of match."""
        if game_name in ["Cash3", "Cash4"]:
            pred_digits = list(prediction)
            win_digits = list(winning)
            
            if sorted(pred_digits) == sorted(win_digits):
                return "BOX"
            
            matches = sum(1 for p, w in zip(pred_digits, win_digits) if p == w)
            return f"{matches}_DIGIT_MATCH"
        
        return "PARTIAL"
    
    def parse_jackpot_numbers(self, number_string, game_name):
        """Parse jackpot number string into main numbers and special ball."""
        if not number_string or '+' not in number_string:
            return [], None
        
        try:
            parts = number_string.split('+')
            main_numbers = [int(x.strip()) for x in parts[0].split()]
            special_number = int(parts[1].strip())
            return main_numbers, special_number
        except:
            return [], None
    
    def generate_daily_report(self, report_date=None):
        """Generate comprehensive daily performance report."""
        if report_date is None:
            report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"🎯 GENERATING DAILY REPORT FOR {report_date}")
        print("=" * 60)
        
        # Get all predictions for the date
        predictions = self.get_all_predictions_for_date(report_date)
        if not predictions:
            print(f"❌ No predictions found for {report_date}")
            return
        
        print(f"📊 Found predictions from {len(predictions)} subscribers")
        
        # Initialize report data
        report_data = {
            "date": report_date,
            "generated_at": datetime.now().isoformat(),
            "subscribers_analyzed": len(predictions),
            "game_results": {},
            "summary": {
                "total_exact_wins": 0,
                "total_close_wins": 0,
                "best_performing_subscribers": [],
                "trending_numbers": {}
            }
        }
        
        # Analyze each game
        for game_name, game_id in self.game_mapping.items():
            print(f"\n🎲 Analyzing {game_name}...")
            
            # Fetch actual results
            results = self.fetch_lottery_results(game_id, report_date)
            if not results:
                continue
            
            # Process results based on game type
            if game_name in ["Cash3", "Cash4"]:
                # Cash games - usually evening draws
                evening_result = None
                for result in results:
                    if 'evening' in result.get('draw_type', '').lower():
                        evening_result = result.get('winning_numbers', '')
                        break
                
                if evening_result:
                    analysis = self.analyze_cash_game_performance(game_name, evening_result, predictions)
                    report_data["game_results"][game_name] = {
                        "winning_number": evening_result,
                        "draw_type": "Evening",
                        "analysis": analysis
                    }
                    report_data["summary"]["total_exact_wins"] += len(analysis["exact_matches"])
                    report_data["summary"]["total_close_wins"] += len(analysis["close_matches"])
            
            else:
                # Jackpot games
                if results:
                    latest_result = results[0]  # Most recent draw
                    winning_numbers = latest_result.get('winning_numbers', '')
                    
                    analysis = self.analyze_jackpot_performance(game_name, winning_numbers, predictions)
                    report_data["game_results"][game_name] = {
                        "winning_numbers": winning_numbers,
                        "draw_date": latest_result.get('draw_date', report_date),
                        "analysis": analysis
                    }
                    report_data["summary"]["total_exact_wins"] += len(analysis["exact_matches"])
                    report_data["summary"]["total_close_wins"] += len(analysis["partial_matches"])
        
        # Generate formatted report
        self.create_formatted_report(report_data)
        
        # Save raw data
        report_file = self.reports_dir / f"daily_report_{report_date.replace('-', '_')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n✅ Report saved to: {report_file}")
        return report_data
    
    def create_formatted_report(self, report_data):
        """Create human-readable formatted report."""
        report_date = report_data["date"]
        formatted_file = self.reports_dir / f"DAILY_REPORT_{report_date.replace('-', '_')}.txt"
        
        with open(formatted_file, 'w', encoding='utf-8') as f:
            f.write("🎯 DAILY LOTTERY PERFORMANCE REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"📅 Report Date: {report_date}\n")
            f.write(f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"👥 Subscribers Analyzed: {report_data['subscribers_analyzed']}\n")
            f.write(f"🎯 Total Exact Wins: {report_data['summary']['total_exact_wins']}\n")
            f.write(f"📊 Total Close Wins: {report_data['summary']['total_close_wins']}\n\n")
            
            # Game by game results
            for game_name, game_data in report_data["game_results"].items():
                f.write(f"{'='*20} {game_name.upper()} {'='*20}\n")
                
                if game_name in ["Cash3", "Cash4"]:
                    f.write(f"🏆 Winning Number: {game_data['winning_number']} ({game_data['draw_type']})\n")
                    
                    analysis = game_data["analysis"]
                    f.write(f"📈 Subscribers Played: {analysis['subscribers_played']}\n")
                    f.write(f"🎲 Total Predictions: {analysis['total_predictions']}\n\n")
                    
                    if analysis["exact_matches"]:
                        f.write("🔥 EXACT WINS:\n")
                        for match in analysis["exact_matches"]:
                            f.write(f"   ✅ {match['name']} ({match['subscriber']}) - Pick: {match['pick']} - Confidence: {match['confidence']:.1f}%\n")
                        f.write("\n")
                    
                    if analysis["close_matches"]:
                        f.write("⚡ CLOSE MATCHES:\n")
                        for match in analysis["close_matches"]:
                            f.write(f"   📊 {match['name']} ({match['subscriber']}) - Pick: {match['pick']} - Type: {match['match_type']} - Confidence: {match['confidence']:.1f}%\n")
                        f.write("\n")
                
                else:  # Jackpot games
                    f.write(f"🏆 Winning Numbers: {game_data['winning_numbers']}\n")
                    f.write(f"📅 Draw Date: {game_data['draw_date']}\n")
                    
                    analysis = game_data["analysis"]
                    f.write(f"📈 Subscribers Played: {analysis['subscribers_played']}\n")
                    f.write(f"🎲 Total Predictions: {analysis['total_predictions']}\n\n")
                    
                    if analysis["exact_matches"]:
                        f.write("🔥 JACKPOT WINS:\n")
                        for match in analysis["exact_matches"]:
                            f.write(f"   🎊 {match['name']} ({match['subscriber']}) - Pick: {match['pick']} - Confidence: {match['confidence']:.1f}%\n")
                        f.write("\n")
                    
                    if analysis["partial_matches"]:
                        f.write("⚡ PARTIAL MATCHES:\n")
                        for match in analysis["partial_matches"]:
                            f.write(f"   📊 {match['name']} ({match['subscriber']}) - Pick: {match['pick']} - Main: {match['main_matches']}/{match['total_main']} + Special: {'✅' if match['special_match'] else '❌'}\n")
                        f.write("\n")
                
                f.write("\n")
        
        print(f"📄 Formatted report saved to: {formatted_file}")

def main():
    """Main execution function."""
    reporter = DailyPerformanceReporter()
    
    # Generate report for yesterday by default
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Allow command line date override
    if len(sys.argv) > 1:
        report_date = sys.argv[1]  # Format: YYYY-MM-DD
    else:
        report_date = yesterday
    
    try:
        report_data = reporter.generate_daily_report(report_date)
        
        if report_data:
            print(f"\n🎯 DAILY REPORT SUMMARY FOR {report_date}:")
            print(f"   📊 Subscribers: {report_data['subscribers_analyzed']}")
            print(f"   🏆 Exact Wins: {report_data['summary']['total_exact_wins']}")
            print(f"   📈 Close Wins: {report_data['summary']['total_close_wins']}")
            print(f"   🎲 Games Analyzed: {len(report_data['game_results'])}")
            
            # Show any big wins
            for game_name, game_data in report_data["game_results"].items():
                exact_wins = len(game_data["analysis"].get("exact_matches", []))
                if exact_wins > 0:
                    print(f"   🔥 {game_name}: {exact_wins} EXACT WIN(S)!")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())