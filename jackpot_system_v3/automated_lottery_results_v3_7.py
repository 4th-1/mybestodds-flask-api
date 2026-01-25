#!/usr/bin/env python3
"""
Automated Lottery Results Fetcher v3.7
=======================================

Automatically fetches lottery results from RapidAPI and other sources
for SMART LOGIC performance monitoring and MMFSN course correction.

INTEGRATES WITH: mmfsn_course_corrector_v3_7.py and smart_logic_tracker_v3_7.py
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

class LotteryResultsFetcher:
    """Automated lottery results fetching for SMART LOGIC system"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Use your working API key
        self.api_key = api_key or "a0a23c4713msh72afb05b0e7b414p18e883jsn6452579f960a"
        self.base_url = "https://usa-lottery-result-all-state-api.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "usa-lottery-result-all-state-api.p.rapidapi.com"
        }
        
        # Game mapping for API calls - COMPLETE with WINNING NUMBERS endpoint
        self.game_mappings = {
            "cash3_midday": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "100"
            },
            "cash3_evening": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "101"
            },  
            "cash4_night": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "105"
            },
            "megamillions": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "24"   # National ID (correct)
            },
            "powerball": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "23"   # National ID (correct)
            },
            "cash4life": {
                "dates_endpoint": "lottery-results/past-draws-dates", 
                "results_endpoint": "lottery-results/game-result",
                "gameID": "117"  # Georgia Cash4Life
            }
        }
        
        self.results_file = os.path.join(PROJECT_ROOT, "data", "actual_results_december_2025.json")
        self.ensure_data_directory()
    
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.results_file)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def fetch_georgia_lottery_results(self, date: str, games: List[str]) -> Dict[str, str]:
        """Fetch Georgia lottery results for specific date and games"""
        
        results = {}
        
        if not self.api_key:
            print("⚠️ No RapidAPI key provided - using fallback method")
            return self._fetch_fallback_results(date, games)
        
        for game in games:
            if game not in self.game_mappings:
                continue
                
            game_config = self.game_mappings[game]
            
            try:
                # Build API endpoint
                if "state" in game_config:
                    # State-specific games (Cash3, Cash4)
                    url = f"{self.base_url}/{game_config['state']}/{game_config['game']}"
                    params = {
                        "date": date,
                        "session": game_config.get("session", "all")
                    }
                else:
                    # National games (MegaMillions, Powerball, Cash4Life)
                    url = f"{self.base_url}/{game_config['game']}"
                    params = {"date": date}
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                winning_number = self._extract_winning_number(data, game)
                
                if winning_number:
                    results[game] = winning_number
                    print(f"✅ {game}: {winning_number}")
                else:
                    print(f"⚠️ {game}: No winning number found")
                
                # Rate limiting - be respectful to API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error fetching {game}: {e}")
                # Try fallback for this game
                fallback_result = self._fetch_fallback_single_game(date, game)
                if fallback_result:
                    results[game] = fallback_result
        
        return results
    
    def fetch_draw_dates_and_results(self, game: str, days_back: int = 7) -> List[Dict]:
        """
        Fetch draw dates using your working API format, then get winning numbers
        Based on your successful API response format
        """
        print(f"🎯 Fetching {game} draw dates and results for last {days_back} days...")
        
        if game not in self.game_mappings:
            print(f"❌ Game {game} not supported")
            return []
            
        game_config = self.game_mappings[game]
        
        try:
            # Use the working endpoint format from your API response
            url = f"{self.base_url}/{game_config['dates_endpoint']}"
            
            # Parameters based on your successful test
            params = {}
            if "gameID" in game_config:
                params = {"gameID": game_config["gameID"]}  # Use uppercase gameID
            
            print(f"📡 API Call: {url} with params: {params}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse using your actual response format
            results = self.parse_rapidapi_response(data, game)
            
            # Filter to recent dates
            if results:
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=days_back)
                recent_results = []
                
                for result in results:
                    try:
                        result_date = datetime.strptime(result["date"], "%Y-%m-%d")
                        if result_date >= cutoff_date:
                            recent_results.append(result)
                    except ValueError:
                        continue
                        
                print(f"✅ Found {len(recent_results)} recent draws for {game}")
                return recent_results
            
        except Exception as e:
            print(f"❌ Error fetching {game} dates: {e}")
            return []
        
        return []
    
    def parse_rapidapi_response(self, response_data: Dict, game_type: str) -> List[Dict]:
        """Parse RapidAPI response format based on your successful test data"""
        results = []
        
        if "data" not in response_data or "date" not in response_data["data"]:
            print(f"❌ Invalid response format for {game_type}")
            return results
        
        game_details = response_data["data"].get("gameDetails", {})
        draws = response_data["data"]["date"]
        
        print(f"📊 Processing {len(draws)} draws for {game_details.get('gameName', game_type)}")
        
        for draw in draws:
            try:
                # Extract date in YYYY-MM-DD format
                draw_date = draw["drawDate"]
                
                # For now, we'll store the API data and wait for actual winning numbers
                result_entry = {
                    "date": draw_date,
                    "game": self._map_api_game_to_internal(game_type, game_details.get("gameName")),
                    "session": self._determine_session(draw["drawTime"]) if game_type in ["cash3_midday", "cash3_evening"] else "main",
                    "draw_id": draw["drawID"],
                    "draw_number": draw["drawNumber"],
                    "draw_time": draw["drawTime"],
                    "status": "date_available",  # Indicates we have draw date but need winning numbers
                    "api_source": "rapidapi_usa_lottery",
                    "game_details": {
                        "game_name": game_details.get("gameName"),
                        "state": game_details.get("state", {}).get("state"),
                        "draw_timezone": game_details.get("drawTimezone")
                    }
                }
                
                results.append(result_entry)
                
            except (KeyError, ValueError) as e:
                print(f"⚠️ Error parsing draw data: {e}")
                continue
                
        return results
    
    def _map_api_game_to_internal(self, api_game_type: str, game_name: str) -> str:
        """Map API game names to internal game identifiers"""
        game_name_lower = (game_name or "").lower()
        
        if "lucky for life" in game_name_lower or "cash4life" in game_name_lower:
            return "cash4life"
        elif "mega" in game_name_lower:
            return "megamillions"
        elif "powerball" in game_name_lower:
            return "powerball"
        elif api_game_type.startswith("cash3"):
            return "cash3"
        elif api_game_type.startswith("cash4"):
            return "cash4"
        else:
            return api_game_type
            
    def _determine_session(self, draw_time: str) -> str:
        """Determine session based on draw time"""
        try:
            # Parse time (format: "14:38:00")
            hour = int(draw_time.split(":")[0])
            if hour < 15:  # 3 PM cutoff
                return "midday"
            else:
                return "evening"
        except:
            return "unknown"
    
    def fetch_all_supported_games(self, days_back: int = 3) -> Dict[str, List[Dict]]:
        """
        Fetch results for ALL supported SMART LOGIC games
        Returns complete dataset for MMFSN course correction and performance analysis
        """
        print(f"🎯 FETCHING ALL SMART LOGIC SUPPORTED GAMES - Last {days_back} days")
        print("=" * 65)
        
        all_results = {}
        total_draws = 0
        
        for game_name, config in self.game_mappings.items():
            print(f"\n🎲 Processing {game_name.upper()}...")
            
            try:
                game_results = self.fetch_draw_dates_and_results(game_name, days_back)
                
                if game_results:
                    all_results[game_name] = game_results
                    total_draws += len(game_results)
                    
                    # Show summary for this game
                    latest_date = game_results[0]["date"] if game_results else "N/A"
                    game_display_name = game_results[0]["game_details"]["game_name"] if game_results else game_name
                    
                    print(f"   ✅ {game_display_name}: {len(game_results)} draws (latest: {latest_date})")
                else:
                    print(f"   ❌ {game_name}: No recent draws found")
                    
                # Rate limiting between games
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ {game_name}: Error - {e}")
                all_results[game_name] = []
        
        print(f"\n📊 SUMMARY:")
        print(f"   Games processed: {len(self.game_mappings)}")
        print(f"   Total draws retrieved: {total_draws}")
        print(f"   Successful games: {len([r for r in all_results.values() if r])}")
        
        # Save complete results for MMFSN system
        self._save_complete_results(all_results)
        
        return all_results
    
    def _save_complete_results(self, all_results: Dict[str, List[Dict]]):
        """Save complete results for integration with MMFSN and tracking systems"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(PROJECT_ROOT, "data", f"lottery_results_{timestamp}.json")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        try:
            # Create comprehensive results structure
            complete_data = {
                "timestamp": datetime.now().isoformat(),
                "api_source": "rapidapi_usa_lottery",
                "total_games": len(all_results),
                "total_draws": sum(len(draws) for draws in all_results.values()),
                "games": all_results,
                "metadata": {
                    "fetched_by": "automated_lottery_results_v3_7",
                    "smart_logic_compatible": True,
                    "mmfsn_ready": True
                }
            }
            
            with open(results_file, 'w') as f:
                json.dump(complete_data, f, indent=2)
                
            print(f"💾 Complete results saved: {os.path.basename(results_file)}")
            
            # Also save as latest for easy access by other systems
            latest_file = os.path.join(PROJECT_ROOT, "data", "latest_lottery_results.json")
            with open(latest_file, 'w') as f:
                json.dump(complete_data, f, indent=2)
                
            return results_file
            
        except Exception as e:
            print(f"⚠️ Error saving results: {e}")
            return None
    
    def fetch_complete_lottery_data(self, game: str, days_back: int = 7) -> List[Dict]:
        """
        🚀 BREAKTHROUGH METHOD: Fetch COMPLETE lottery data - both draw dates AND actual winning numbers!
        This is the FINAL SOLUTION for MMFSN course correction system using your API discovery!
        
        Returns complete dataset ready for SMART LOGIC performance analysis and weight adjustments.
        """
        print(f"🎯 FETCHING COMPLETE DATA: {game.upper()} (last {days_back} days)")
        print("=" * 60)
        print("📊 Using DUAL-ENDPOINT architecture:")
        print("   1️⃣  past-draws-dates → Get draw schedule")
        print("   2️⃣  game-result → Get actual winning numbers")
        print("-" * 60)
        
        # Step 1: Get draw dates using existing method
        draw_dates = self.fetch_draw_dates_and_results(game, days_back)
        
        if not draw_dates:
            print(f"❌ No draw dates found for {game}")
            return []
        
        complete_results = []
        successful_fetches = 0
        
        # Step 2: Get winning numbers for each draw using YOUR breakthrough discovery!
        for i, draw_info in enumerate(draw_dates[:5], 1):  # Limit to 5 most recent for API efficiency
            draw_id = draw_info["draw_id"]
            draw_date = draw_info["date"]
            
            print(f"\n   🎲 [{i}/5] Fetching {draw_date} (ID: {draw_id})")
            
            # Fetch actual winning numbers using the lottery-results/game-result endpoint
            winning_numbers = self.fetch_winning_numbers_for_draw(game, str(draw_id), draw_date)
            
            if winning_numbers:
                # SUCCESS! Complete dataset achieved
                complete_result = {
                    **draw_info,  # Include original draw info (date, draw_id, session)
                    "winning_numbers": winning_numbers["winning_numbers"],
                    "additional_numbers": winning_numbers["additional_numbers"], 
                    "formatted_winning_number": winning_numbers["formatted_number"],
                    "jackpot": winning_numbers["jackpot"],
                    "total_winners": winning_numbers["total_winners"],
                    "prize_structure": winning_numbers.get("prize_structure", {}),
                    "status": "complete_with_numbers",
                    "mmfsn_ready": True
                }
                complete_results.append(complete_result)
                successful_fetches += 1
                print(f"   ✅ SUCCESS: {winning_numbers['formatted_number']} | ${winning_numbers.get('jackpot', 'N/A')}")
            else:
                # Keep draw info even without winning numbers
                draw_info["status"] = "date_only" 
                draw_info["mmfsn_ready"] = False
                complete_results.append(draw_info)
                print(f"   ⚠️  Numbers unavailable (may be future draw)")
            
            # Rate limiting - respect API limits
            if i < 5:  # Don't sleep after last request
                time.sleep(1.2)
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"🏆 COMPLETE DATA SUMMARY for {game.upper()}:")
        print(f"   📊 Total draws processed: {len(complete_results)}")
        print(f"   ✅ With winning numbers: {successful_fetches}/{len(complete_results)}")
        
        if successful_fetches > 0:
            success_rate = (successful_fetches / len(complete_results)) * 100
            print(f"   📈 Success rate: {success_rate:.1f}%")
            
            # Show sample for verification
            sample = next(r for r in complete_results if "formatted_winning_number" in r)
            print(f"   🎲 Sample result: {sample['date']} → {sample['formatted_winning_number']}")
            print(f"   💰 Sample jackpot: {sample.get('jackpot', 'Unknown')}")
            print(f"   🎯 MMFSN ready: {sample['mmfsn_ready']}")
        
        print(f"{'='*60}")
        
        return complete_results
    
    def fetch_winning_numbers_for_draw(self, game: str, draw_id: str, draw_date: str) -> Optional[Dict]:
        """
        Fetch actual winning numbers for a specific draw
        Uses the lottery-results/game-result endpoint discovered by the user
        """
        
        if game not in self.game_mappings:
            print(f"❌ Game {game} not supported")
            return None
        
        game_config = self.game_mappings[game]
        
        try:
            # Use the winning numbers endpoint
            url = f"{self.base_url}/{game_config['results_endpoint']}"
            
            # Parameters for specific draw
            params = {
                "gameID": game_config["gameID"],
                "drawID": draw_id
            }
            
            print(f"🎯 Fetching winning numbers: {game} draw {draw_id} ({draw_date})")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse winning numbers from API response
            if "data" in data and "winningNumbers" in data["data"]:
                winning_data = data["data"]
                
                # Extract numbers based on game type
                result = {
                    "date": draw_date,
                    "draw_id": draw_id,
                    "game": game,
                    "winning_numbers": winning_data["winningNumbers"],
                    "additional_numbers": winning_data.get("additionalNumbers", []),
                    "formatted_number": self._format_winning_number(game, winning_data),
                    "jackpot": winning_data.get("jackpot", "0"),
                    "total_winners": winning_data.get("overallWinners", 0),
                    "api_source": "rapidapi_usa_lottery",
                    "status": "complete"
                }
                
                print(f"✅ Got winning numbers: {result['formatted_number']}")
                return result
            else:
                print(f"⚠️ No winning numbers in API response")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching winning numbers for {game}: {e}")
            return None
    
    def _format_winning_number(self, game: str, winning_data: Dict) -> str:
        """Format winning numbers according to SMART LOGIC system format"""
        
        main_numbers = winning_data["winningNumbers"]
        additional = winning_data.get("additionalNumbers", [])
        
        # Handle both string and integer numbers from API
        def format_number(n):
            try:
                return f"{int(n):02d}"
            except (ValueError, TypeError):
                return str(n).zfill(2)
        
        if game in ["cash3_midday", "cash3_evening"]:
            # Cash3 format: "123"
            return "".join(str(int(n) if str(n).isdigit() else n) for n in main_numbers[:3])
            
        elif game == "cash4_night":
            # Cash4 format: "1234"  
            return "".join(str(int(n) if str(n).isdigit() else n) for n in main_numbers[:4])
            
        elif game == "megamillions":
            # MegaMillions format: "04-11-23-33-49-23" (5 main + Mega Ball)
            main = "-".join(format_number(n) for n in main_numbers)
            mega_ball = format_number(additional[0]) if additional else "00"
            return f"{main}-{mega_ball}"
            
        elif game == "powerball":
            # Powerball format: "04-11-23-33-49-23" (5 main + Powerball)
            main = "-".join(format_number(n) for n in main_numbers)
            powerball = format_number(additional[0]) if additional else "00"
            return f"{main}-{powerball}"
            
        elif game == "cash4life":
            # Cash4Life format: "04-11-23-33-49-03" (5 main + Cash Ball)
            main = "-".join(format_number(n) for n in main_numbers)
            cash_ball = format_number(additional[0]) if additional else "00"
            return f"{main}-{cash_ball}"
        
        else:
            # Fallback - just join main numbers
            return "-".join(str(n) for n in main_numbers)
    
    def _extract_winning_number(self, api_data: Dict, game: str) -> Optional[str]:
        """Extract winning number from API response"""
        
        try:
            if game in ["cash3_midday", "cash3_evening"]:
                # Cash3 format: "123"
                if "numbers" in api_data and api_data["numbers"]:
                    return "".join(str(n) for n in api_data["numbers"][:3])
                    
            elif game == "cash4_night":
                # Cash4 format: "1234"
                if "numbers" in api_data and api_data["numbers"]:
                    return "".join(str(n) for n in api_data["numbers"][:4])
                    
            elif game in ["megamillions", "powerball"]:
                # Format: "12-25-34-45-67-15"
                if "main_numbers" in api_data and "bonus_number" in api_data:
                    main_nums = "-".join(str(n) for n in api_data["main_numbers"])
                    bonus = str(api_data["bonus_number"])
                    return f"{main_nums}-{bonus}"
                    
            elif game == "cash4life":
                # Format: "05-12-28-35-47-03" 
                if "main_numbers" in api_data and "cash_ball" in api_data:
                    main_nums = "-".join(f"{n:02d}" for n in api_data["main_numbers"])
                    cash_ball = f"{api_data['cash_ball']:02d}"
                    return f"{main_nums}-{cash_ball}"
        
        except Exception as e:
            print(f"⚠️ Error extracting number for {game}: {e}")
        
        return None
    
    def _fetch_fallback_results(self, date: str, games: List[str]) -> Dict[str, str]:
        """Fallback method when API is unavailable"""
        
        print("🔄 Using fallback lottery results fetching...")
        
        # Try alternative sources or manual entry prompt
        fallback_results = {}
        
        for game in games:
            # You could add other API sources here as fallbacks
            # Or implement web scraping from official lottery sites
            # For now, return empty to prompt manual entry
            pass
        
        return fallback_results
    
    def _fetch_fallback_single_game(self, date: str, game: str) -> Optional[str]:
        """Fallback for single game when main API fails"""
        
        # Alternative API sources could go here
        # Georgia Lottery official API, other providers, etc.
        return None
    
    def update_results_file(self, date: str, results: Dict[str, str]):
        """Update the actual results file with new lottery numbers"""
        
        try:
            # Load existing results
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r') as f:
                    all_results = json.load(f)
            else:
                all_results = {}
            
            # Add new results for this date
            if date not in all_results:
                all_results[date] = {}
            
            all_results[date].update(results)
            
            # Save updated results
            with open(self.results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            print(f"💾 Results updated for {date}: {len(results)} games")
            
        except Exception as e:
            print(f"❌ Error updating results file: {e}")
    
    def fetch_recent_results(self, days_back: int = 7) -> Dict[str, Dict[str, str]]:
        """Fetch lottery results for the last N days"""
        
        all_results = {}
        
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            print(f"🔍 Fetching results for {date}...")
            
            # All games we support
            games = list(self.game_mappings.keys())
            
            day_results = self.fetch_georgia_lottery_results(date, games)
            
            if day_results:
                all_results[date] = day_results
                self.update_results_file(date, day_results)
            else:
                print(f"⚠️ No results found for {date}")
        
        return all_results
    
    def auto_update_and_run_analysis(self, days_back: int = 3):
        """
        Complete automation: Fetch results and run MMFSN course correction
        """
        
        print("🚀 SMART LOGIC AUTOMATED PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        # Fetch recent results
        recent_results = self.fetch_recent_results(days_back)
        
        if not recent_results:
            print("❌ No recent results fetched - analysis aborted")
            return
        
        print(f"✅ Fetched results for {len(recent_results)} days")
        
        # Run MMFSN course correction with updated results
        try:
            from mmfsn_course_corrector_v3_7 import MMFSNCourseCorrector
            
            corrector = MMFSNCourseCorrector()
            corrector.run_course_correction(
                outputs_dir="outputs",
                results_file=self.results_file,
                config_file="config_v3_5.json"
            )
            
            print("✅ Automated analysis complete!")
            
        except ImportError as e:
            print(f"⚠️ MMFSN course corrector not available: {e}")
        except Exception as e:
            print(f"❌ Error running automated analysis: {e}")

def setup_api_integration():
    """Setup wizard for API key configuration"""
    
    print("🔧 SMART LOGIC API INTEGRATION SETUP")
    print("=" * 50)
    
    api_key = input("Enter your RapidAPI key (or press Enter to skip): ").strip()
    
    if api_key:
        # Save to environment file
        env_file = os.path.join(PROJECT_ROOT, ".env")
        with open(env_file, "w") as f:
            f.write(f"RAPIDAPI_KEY={api_key}\n")
        
        print("✅ API key saved to .env file")
        
        # Test the API connection
        fetcher = LotteryResultsFetcher(api_key)
        print("🧪 Testing API connection...")
        
        test_date = datetime.now().strftime('%Y-%m-%d')
        test_results = fetcher.fetch_georgia_lottery_results(test_date, ["cash3_midday"])
        
        if test_results:
            print("✅ API connection successful!")
        else:
            print("⚠️ API test failed - check your key and try again")
    
    else:
        print("⚠️ No API key provided - manual entry mode will be used")
    
    print("\n🎯 Setup complete! Your SMART LOGIC system can now:")
    print("   • Automatically fetch lottery results")
    print("   • Run performance analysis")
    print("   • Adjust MMFSN weights automatically") 
    print("   • Generate comprehensive reports")

def main():
    """Main execution function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_api_integration()
        return
    
    # Default: fetch recent results and run analysis
    fetcher = LotteryResultsFetcher()
    fetcher.auto_update_and_run_analysis()

if __name__ == "__main__":
    main()