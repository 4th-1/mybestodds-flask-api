"""
MY BEST ODDS - Flask API Server v2.0
=====================================
Connects Python prediction engine (v3.7) + Triple/Quad engines to Base44 app
Includes astronomical overlay integration and peak condition forecasting
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Base44 frontend

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Import Base44 integration
from base44_integration import Base44Client
from twilio_integration import TwilioClient

# Import prediction engines
# TEMPORARILY DISABLED - these files not in GitHub repo yet
# from triple_prediction_engine_v1 import TriplePredictionEngine
# from quad_prediction_engine_v1 import QuadPredictionEngine
# from enrich_with_overlays import calculate_moon_phase, calculate_planetary_hour

# Initialize Base44 client (will use env variables)
base44 = Base44Client()
twilio = TwilioClient()

# Initialize prediction engines
# TEMPORARILY DISABLED - files not in repo
triple_engine = None
quad_engine = None
# try:
#     triple_engine = TriplePredictionEngine()
#     quad_engine = QuadPredictionEngine()
#     logger.info("Triple and Quad engines initialized successfully")
# except Exception as e:
#     logger.error(f"Error initializing prediction engines: {e}")
#     triple_engine = None
#     quad_engine = None

# Configuration
JACKPOT_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "jackpot_system_v3")
SUBSCRIBERS_DIR = os.path.join(JACKPOT_SYSTEM_DIR, "data", "subscribers")

# Detect OS and use correct Python path
import platform
if platform.system() == "Windows":
    PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
else:  # Linux/Unix (Railway)
    PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")

RUN_KIT_SCRIPT = os.path.join(JACKPOT_SYSTEM_DIR, "run_kit_v3.py")


def get_all_subscribers() -> List[Dict]:
    """Load all subscriber configurations from data/subscribers/"""
    subscribers = []
    
    for kit in ["BOOK3", "BOOK", "BOSK"]:
        kit_dir = os.path.join(SUBSCRIBERS_DIR, kit)
        if not os.path.exists(kit_dir):
            continue
            
        for filename in os.listdir(kit_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(kit_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        subscriber = json.load(f)
                        subscriber['kit'] = kit
                        subscriber['config_file'] = filename
                        subscribers.append(subscriber)
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
    
    return subscribers


def get_overlay_conditions(date: datetime) -> Dict:
    """Calculate astronomical overlay conditions for a given date"""
    # TEMPORARILY DISABLED - dependencies not in repo
    return {
        "moon_phase": "BASELINE",
        "moon_illumination": 0.5,
        "moon_modifier": 1.0,
        "midday_planet": "Sun",
        "midday_modifier": 1.0,
        "evening_planet": "Moon", 
        "evening_modifier": 1.0,
        "midday_combined_score": 1.0,
        "evening_combined_score": 1.0
    }
    
    # Original code disabled until triple_prediction_engine_v1 added to repo
    # if triple_engine is None:
    #     return {}
    # 
    # moon_phase, moon_illum = calculate_moon_phase(date)
    # 
    # moon_modifiers = {
    #     "NEW": 1.25, "WAXING_CRESCENT": 1.1, "FIRST_QUARTER": 1.15,
    #     "WAXING_GIBBOUS": 1.1, "FULL": 1.30, "WANING_GIBBOUS": 1.05,
    #     "LAST_QUARTER": 1.1, "WANING_CRESCENT": 1.0
    # }
    # 
    # planetary_modifiers = {
    #     "Sun": 1.20, "Moon": 1.15, "Mercury": 1.10, "Venus": 1.15,
    #     "Mars": 1.10, "Jupiter": 1.40, "Saturn": 0.95
    # }
    # 
    # midday_planet = calculate_planetary_hour(date, "MIDDAY")
    # evening_planet = calculate_planetary_hour(date, "EVENING")
    # 
    # moon_mod = moon_modifiers[moon_phase]
    # midday_mod = planetary_modifiers[midday_planet]
    # evening_mod = planetary_modifiers[evening_planet]
    # 
    # return {
    #     "moon_phase": moon_phase,
    #     "moon_illumination": round(moon_illum, 3),
    #     "moon_modifier": moon_mod,
    #     "midday_planet": midday_planet,
    #     "midday_modifier": midday_mod,
    #     "evening_planet": evening_planet,
    #     "evening_modifier": evening_mod,
    #     "midday_combined_score": round(moon_mod * midday_mod, 3),
    #     "evening_combined_score": round(moon_mod * evening_mod, 3)
    # }


@app.route('/api/triples/predict', methods=['GET'])
def predict_triples():
    """
    Generate Cash3 triple predictions for today or specified date
    
    Query params:
        date (optional): Target date in YYYY-MM-DD format (default: today)
        session (optional): MIDDAY, EVENING, or NIGHT (default: all three)
    
    Returns:
        {
            "success": true,
            "date": "2026-01-14",
            "predictions": [
                {"number": "333", "confidence": 100, "odds": "1-in-1369", "session": "MIDDAY", ...},
                ...
            ],
            "overlay_conditions": {...}
        }
    """
    if not triple_engine:
        return jsonify({
            "success": False,
            "error": "Triple prediction engine not initialized"
        }), 500
    
    try:
        # Get target date
        target_date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        session_filter = request.args.get('session', '').upper()  # MIDDAY, EVENING, NIGHT, or empty for all
        
        # Generate predictions for requested sessions
        all_predictions = []
        if session_filter in ['MIDDAY', 'EVENING', 'NIGHT']:
            # Single session
            all_predictions = triple_engine.predict_all_triples(target_date, session_filter)
        else:
            # All three sessions - generate separately and merge
            midday_preds = triple_engine.predict_all_triples(target_date, 'MIDDAY')
            evening_preds = triple_engine.predict_all_triples(target_date, 'EVENING')
            night_preds = triple_engine.predict_all_triples(target_date, 'NIGHT')
            
            # Combine and deduplicate (keep highest confidence for each triple)
            triple_best = {}
            for pred in midday_preds + evening_preds + night_preds:
                triple = pred['triple']
                if triple not in triple_best or pred['confidence'] > triple_best[triple]['confidence']:
                    triple_best[triple] = pred
            all_predictions = list(triple_best.values())
            all_predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Get overlay conditions
        overlay_conditions = get_overlay_conditions(target_date)
        
        # Convert to API response format
        predictions_formatted = []
        for pred in all_predictions:
            predictions_formatted.append({
                "number": pred['triple'],
                "confidence": round(pred['confidence'], 1),
                "odds": f"1-in-{pred['context']['current_gap']}",
                "session": pred['context']['session_best'].upper(),
                "days_overdue": pred['context']['current_gap'],
                "gap_percentile": round(pred['scores']['percentile'], 1),
                "symbolic_bonus": pred['bonuses']['symbolic'],
                "band": pred['band']
            })
        predictions = predictions_formatted
        
        return jsonify({
            "success": True,
            "date": target_date_str,
            "game": "Cash3",
            "data_quality": "PROFESSIONAL_GRADE (32 years, 244 occurrences)",
            "predictions": predictions,
            "overlay_conditions": overlay_conditions,
            "total_predictions": len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Error generating triple predictions: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/quads/predict', methods=['GET'])
def predict_quads():
    """
    Generate Cash4 quad predictions for today or specified date
    
    Query params:
        date (optional): Target date in YYYY-MM-DD format (default: today)
        session (optional): MIDDAY, EVENING, or NIGHT (default: all three)
    
    Returns:
        {
            "success": true,
            "date": "2026-01-14",
            "predictions": [
                {"number": "2222", "confidence": 100, "odds": "1-in-5920", "session": "MIDDAY", ...},
                ...
            ],
            "overlay_conditions": {...}
        }
    """
    if not quad_engine:
        return jsonify({
            "success": False,
            "error": "Quad prediction engine not initialized"
        }), 500
    
    try:
        # Get target date
        target_date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        session_filter = request.args.get('session', '').upper()  # MIDDAY, EVENING, NIGHT, or empty for all
        
        # Generate predictions for requested sessions
        all_predictions = []
        if session_filter in ['MIDDAY', 'EVENING', 'NIGHT']:
            # Single session
            all_predictions = quad_engine.predict_all_quads(target_date, session_filter)
        else:
            # All three sessions
            midday_preds = quad_engine.predict_all_quads(target_date, 'MIDDAY')
            evening_preds = quad_engine.predict_all_quads(target_date, 'EVENING')
            night_preds = quad_engine.predict_all_quads(target_date, 'NIGHT')
            
            # Combine and deduplicate (keep highest confidence)
            quad_best = {}
            for pred in midday_preds + evening_preds + night_preds:
                quad = pred['quad']
                if quad not in quad_best or pred['confidence'] > quad_best[quad]['confidence']:
                    quad_best[quad] = pred
            all_predictions = list(quad_best.values())
            all_predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Get overlay conditions
        overlay_conditions = get_overlay_conditions(target_date)
        
        # Convert to API response format
        predictions_formatted = []
        for pred in all_predictions:
            # Quad engine uses 'days_since' instead of 'current_gap'
            days_overdue = pred['context'].get('current_gap') or pred['context'].get('days_since', 0)
            # Quad engine might not have session_best
            session_best = pred['context'].get('session_best', session_filter or 'MIDDAY').upper()
            
            predictions_formatted.append({
                "number": pred['quad'],
                "confidence": round(pred['confidence'], 1),
                "odds": f"1-in-{days_overdue}",
                "session": session_best,
                "days_overdue": days_overdue,
                "gap_percentile": round(pred['scores']['percentile'], 1),
                "symbolic_bonus": pred['bonuses'].get('symbolic', 0),
                "band": pred['band']
            })
        predictions = predictions_formatted
        
        return jsonify({
            "success": True,
            "date": target_date_str,
            "game": "Cash4",
            "data_quality": "RELIABLE (29 years, 49 occurrences)",
            "predictions": predictions,
            "overlay_conditions": overlay_conditions,
            "total_predictions": len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Error generating quad predictions: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/overlays/today', methods=['GET'])
def get_todays_overlays():
    """
    Get today's astronomical overlay conditions
    
    Returns:
        {
            "success": true,
            "date": "2026-01-14",
            "moon_phase": "WAXING_GIBBOUS",
            "moon_illumination": 0.856,
            "midday_planet": "Venus",
            "evening_planet": "Mercury",
            "midday_combined_score": 1.265,
            "evening_combined_score": 1.210,
            "interpretation": "GOOD conditions (Venus midday, moderate moon)"
        }
    """
    try:
        today = datetime.now()
        overlay_conditions = get_overlay_conditions(today)
        
        # Add interpretation
        midday_score = overlay_conditions.get('midday_combined_score', 1.0)
        evening_score = overlay_conditions.get('evening_combined_score', 1.0)
        max_score = max(midday_score, evening_score)
        
        if max_score >= 1.7:
            interpretation = "PEAK conditions - highest probability"
        elif max_score >= 1.5:
            interpretation = "EXCELLENT conditions - strong probability"
        elif max_score >= 1.3:
            interpretation = "GOOD conditions - elevated probability"
        elif max_score >= 1.2:
            interpretation = "MODERATE conditions - slightly elevated"
        else:
            interpretation = "BASELINE conditions - standard probability"
        
        overlay_conditions['interpretation'] = interpretation
        overlay_conditions['date'] = today.strftime("%Y-%m-%d")
        overlay_conditions['success'] = True
        
        return jsonify(overlay_conditions)
        
    except Exception as e:
        logger.error(f"Error getting overlay conditions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/overlays/forecast', methods=['GET'])
def forecast_peak_conditions():
    """
    Forecast peak astronomical conditions for next N days
    
    Query params:
        days (optional): Number of days to forecast (default: 30, max: 120)
        min_score (optional): Minimum combined score to include (default: 1.5)
    
    Returns:
        {
            "success": true,
            "forecast_days": 30,
            "peak_dates": [
                {"date": "2026-01-18", "session": "EVENING", "score": 1.75, "conditions": "Jupiter + NEW moon"},
                ...
            ]
        }
    """
    try:
        days = min(int(request.args.get('days', 30)), 120)
        min_score = float(request.args.get('min_score', 1.5))
        
        today = datetime.now()
        peak_dates = []
        
        for day_offset in range(days):
            check_date = today + timedelta(days=day_offset)
            overlay_conditions = get_overlay_conditions(check_date)
            
            midday_score = overlay_conditions.get('midday_combined_score', 0)
            evening_score = overlay_conditions.get('evening_combined_score', 0)
            
            # Check midday
            if midday_score >= min_score:
                peak_dates.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "day": check_date.strftime("%A"),
                    "session": "MIDDAY",
                    "score": midday_score,
                    "moon_phase": overlay_conditions['moon_phase'],
                    "planet": overlay_conditions['midday_planet'],
                    "conditions": f"{overlay_conditions['midday_planet']} + {overlay_conditions['moon_phase'].replace('_', ' ')}"
                })
            
            # Check evening
            if evening_score >= min_score:
                peak_dates.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "day": check_date.strftime("%A"),
                    "session": "EVENING",
                    "score": evening_score,
                    "moon_phase": overlay_conditions['moon_phase'],
                    "planet": overlay_conditions['evening_planet'],
                    "conditions": f"{overlay_conditions['evening_planet']} + {overlay_conditions['moon_phase'].replace('_', ' ')}"
                })
        
        # Sort by score descending
        peak_dates.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            "success": True,
            "forecast_days": days,
            "min_score": min_score,
            "peak_dates": peak_dates,
            "total_peaks": len(peak_dates)
        })
        
    except Exception as e:
        logger.error(f"Error forecasting peak conditions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/rare-patterns/today', methods=['GET'])
def get_todays_rare_patterns():
    """
    Get today's top rare pattern predictions (both triples and quads)
    
    Query params:
        min_confidence (optional): Minimum confidence to include (default: 80)
        session (optional): MIDDAY, EVENING, NIGHT, or all (default: all)
    
    Returns:
        {
            "success": true,
            "date": "2026-01-14",
            "triples": [...],
            "quads": [...],
            "overlay_conditions": {...},
            "recommended_plays": [...]
        }
    """
    try:
        min_confidence = float(request.args.get('min_confidence', 80))
        session_filter = request.args.get('session', '').upper()
        today = datetime.now()
        
        # Get predictions from both engines
        rare_patterns = {
            "success": True,
            "date": today.strftime("%Y-%m-%d"),
            "triples": [],
            "quads": [],
            "overlay_conditions": get_overlay_conditions(today),
            "recommended_plays": []
        }
        
        # Get triple predictions
        if triple_engine:
            if session_filter:
                triple_predictions = triple_engine.predict_all_triples(today, session_filter)
            else:
                # Get all three sessions and merge
                midday = triple_engine.predict_all_triples(today, 'MIDDAY')
                evening = triple_engine.predict_all_triples(today, 'EVENING')
                night = triple_engine.predict_all_triples(today, 'NIGHT')
                triple_best = {}
                for pred in midday + evening + night:
                    triple = pred['triple']
                    if triple not in triple_best or pred['confidence'] > triple_best[triple]['confidence']:
                        triple_best[triple] = pred
                triple_predictions = list(triple_best.values())
            
            # Filter by session and confidence
            for pred in triple_predictions:
                if pred['confidence'] >= min_confidence:
                    session_best = pred['context']['session_best'].upper()
                    if not session_filter or session_best == session_filter:
                        rare_patterns['triples'].append({
                            "number": pred['triple'],
                            "confidence": round(pred['confidence'], 1),
                            "odds": f"1-in-{pred['context']['current_gap']}",
                            "session": session_best,
                            "days_overdue": pred['context']['current_gap'],
                            "band": pred['band']
                        })
        
        # Get quad predictions
        if quad_engine:
            if session_filter:
                quad_predictions = quad_engine.predict_all_quads(today, session_filter)
            else:
                # Get all three sessions and merge
                midday = quad_engine.predict_all_quads(today, 'MIDDAY')
                evening = quad_engine.predict_all_quads(today, 'EVENING')
                night = quad_engine.predict_all_quads(today, 'NIGHT')
                quad_best = {}
                for pred in midday + evening + night:
                    quad = pred['quad']
                    if quad not in quad_best or pred['confidence'] > quad_best[quad]['confidence']:
                        quad_best[quad] = pred
                quad_predictions = list(quad_best.values())
            
            # Filter by session and confidence
            for pred in quad_predictions:
                if pred['confidence'] >= min_confidence:
                    days_overdue = pred['context'].get('current_gap') or pred['context'].get('days_since', 0)
                    session_best = pred['context'].get('session_best', 'MIDDAY').upper()
                    
                    if not session_filter or session_best == session_filter:
                        rare_patterns['quads'].append({
                            "number": pred['quad'],
                            "confidence": round(pred['confidence'], 1),
                            "odds": f"1-in-{days_overdue}",
                            "session": session_best,
                            "days_overdue": days_overdue,
                            "band": pred['band']
                        })
        
        # Build recommended plays list (top patterns combining both)
        all_patterns = []
        for triple in rare_patterns['triples'][:3]:  # Top 3 triples
            all_patterns.append({
                "game": "Cash3",
                "number": triple['number'],
                "confidence": triple['confidence'],
                "session": triple['session']
            })
        for quad in rare_patterns['quads'][:3]:  # Top 3 quads
            all_patterns.append({
                "game": "Cash4",
                "number": quad['number'],
                "confidence": quad['confidence'],
                "session": quad['session']
            })
        
        # Sort by confidence
        all_patterns.sort(key=lambda x: x['confidence'], reverse=True)
        rare_patterns['recommended_plays'] = all_patterns[:5]  # Top 5 overall
        
        return jsonify(rare_patterns)
        
    except Exception as e:
        logger.error(f"Error getting rare patterns: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def generate_predictions_from_inline_data(subscriber_id: str, dob: str, kit: str, target_date: str) -> Dict:
    """
    Generate predictions using inline subscriber data (for Base44 webhook integration)
    
    Args:
        subscriber_id: Base44 subscriber ID
        dob: Date of birth in ISO format (YYYY-MM-DD)
        kit: Kit type (BOOK3, BOOK, BOSK)
        target_date: Target date for predictions (YYYY-MM-DD)
    
    Returns:
        Dict with prediction results
    """
    try:
        import tempfile
        import json
        from datetime import datetime
        
        logger.info(f"Generating predictions from inline data: {subscriber_id}, DOB: {dob}, Kit: {kit}")
        
        # Create temporary subscriber config file
        temp_config = {
            "subscriber_id": subscriber_id,
            "email": "",  # Not needed for prediction generation
            "dob": dob,
            "kit": kit,
            "date_of_birth": dob,
            "full_name": subscriber_id,
            "enabled": True
        }
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir=JACKPOT_SYSTEM_DIR) as f:
            json.dump(temp_config, f, indent=2)
            temp_file_path = f.name
        
        temp_filename = os.path.basename(temp_file_path)
        
        try:
            # Run prediction engine with temp config
            cmd = [
                PYTHON_EXE,
                RUN_KIT_SCRIPT,
                temp_filename,  # Just filename, not full path
                kit
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=JACKPOT_SYSTEM_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Prediction failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr
                }
            
            # Parse predictions from DELIVERY folder
            delivery_dir = os.path.join(PROJECT_ROOT, "DELIVERY")
            
            # Look for recent prediction files
            predictions = {}
            
            # BOOK3 kit: Cash3 + Cash4 + Jackpots (with MMFSN)
            # BOOK kit: Cash3 + Cash4 + Jackpots (NO MMFSN)
            # BOSK kit: Cash3 + Cash4 only (no jackpots)
            
            # Parse daily games (Cash3/Cash4) for ALL kits
            if kit in ["BOOK3", "BOOK", "BOSK"]:
                # Daily games: Cash3 and Cash4
                for game in ["cash3", "cash4"]:
                    pattern = f"*{game}*.csv"
                    files = []
                    for root, dirs, filenames in os.walk(delivery_dir):
                        for filename in filenames:
                            if filename.lower().endswith('.csv') and game in filename.lower():
                                files.append(os.path.join(root, filename))
                    
                    if files:
                        # Get most recent file
                        latest_file = max(files, key=os.path.getmtime)
                        
                        # Parse CSV to extract predictions
                        import csv
                        game_predictions = []
                        with open(latest_file, 'r') as csvfile:
                            reader = csv.DictReader(csvfile)
                            for row in reader:
                                game_predictions.append({
                                    "number": row.get('candidate', row.get('number', '')),
                                    "confidence": float(row.get('confidence', 0)),
                                    "session": row.get('session', 'DAY')
                                })
                        
                        predictions[game.upper()] = game_predictions[:10]  # Top 10 predictions
            
            # Parse jackpot games for BOOK3 and BOOK
            if kit in ["BOOK3", "BOOK"]:
                # Jackpot games: MegaMillions, Powerball, Cash4Life
                jackpot_games = {
                    "megamillions": "MEGAMILLIONS",
                    "powerball": "POWERBALL", 
                    "cash4life": "CASH4LIFE"
                }
                
                for game_key, game_name in jackpot_games.items():
                    files = []
                    for root, dirs, filenames in os.walk(delivery_dir):
                        for filename in filenames:
                            if filename.lower().endswith(('.csv', '.json')) and game_key in filename.lower():
                                files.append(os.path.join(root, filename))
                    
                    if files:
                        # Get most recent file
                        latest_file = max(files, key=os.path.getmtime)
                        
                        # Parse predictions (CSV or JSON format)
                        game_predictions = []
                        if latest_file.endswith('.json'):
                            with open(latest_file, 'r') as f:
                                jackpot_data = json.load(f)
                                # Extract predictions from JSON structure
                                if isinstance(jackpot_data, dict) and 'predictions' in jackpot_data:
                                    game_predictions = jackpot_data['predictions'][:5]  # Top 5 for jackpots
                                elif isinstance(jackpot_data, list):
                                    game_predictions = jackpot_data[:5]
                        else:  # CSV format
                            import csv
                            with open(latest_file, 'r') as csvfile:
                                reader = csv.DictReader(csvfile)
                                for row in reader:
                                    game_predictions.append({
                                        "number": row.get('candidate', row.get('number', '')),
                                        "confidence": float(row.get('confidence', 0)),
                                        "band": row.get('band', 'YELLOW')
                                    })
                        
                        if game_predictions:
                            predictions[game_name] = game_predictions[:5]  # Top 5 jackpot predictions
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return {
                "success": True,
                "predictions": predictions,
                "subscriber_id": subscriber_id,
                "date": target_date
            }
            
        finally:
            # Ensure temp file is cleaned up
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"Error generating predictions from inline data: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def run_prediction_engine(subscriber_file: str, kit: str) -> Dict:
    """
    Run prediction engine for a single subscriber
    
    Args:
        subscriber_file: JSON filename (e.g., "JosephDavidSmithIIIntact.json")
        kit: Kit type (BOOK3, BOOK, BOSK)
    
    Returns:
        Dict with prediction results and output file path
    """
    try:
        # Run prediction engine
        cmd = [
            PYTHON_EXE,
            RUN_KIT_SCRIPT,
            f"{kit}/{subscriber_file}",
            kit
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=JACKPOT_SYSTEM_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"Prediction failed: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr
            }
        
        # Find output file (assumes naming convention)
        subscriber_name = subscriber_file.replace(".json", "").replace("IIIntact", "")
        today = datetime.now().strftime("%b%d").lower()
        year = datetime.now().year
        
        # Try different output patterns
        possible_files = [
            f"{subscriber_name.lower()}_full_left_engine_cash_games_{today}_{year}.json",
            f"{subscriber_name.lower()}_complete_game_suite_{today}_{year}.json",
        ]
        
        output_file = None
        for pattern in possible_files:
            test_path = os.path.join(PROJECT_ROOT, pattern)
            if os.path.exists(test_path):
                output_file = test_path
                break
        
        if not output_file:
            logger.warning(f"Output file not found for {subscriber_file}")
            return {
                "success": True,
                "warning": "Prediction completed but output file not found",
                "stdout": result.stdout
            }
        
        # Load prediction results
        with open(output_file, 'r') as f:
            predictions = json.load(f)
        
        return {
            "success": True,
            "predictions": predictions,
            "output_file": output_file
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Prediction timed out for {subscriber_file}")
        return {
            "success": False,
            "error": "Prediction generation timed out (>2 min)"
        }
    except Exception as e:
        logger.error(f"Error running prediction: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "python_engine": "v3.7_with_triple_quad_overlays",
        "base44_connected": base44.is_connected(),
        "twilio_connected": twilio.is_connected(),
        "engines": {
            "jackpot": "v3.7",
            "triples": "v1.0 (32 years data)" if triple_engine else "not loaded",
            "quads": "v1.0 (29 years data)" if quad_engine else "not loaded",
            "overlays": "active" if triple_engine else "inactive"
        }
    })


@app.route('/api/predictions/generate', methods=['POST', 'GET', 'OPTIONS'])
def generate_predictions():
    """
    Generate predictions for all subscribers and push to Base44
    
    Request body (optional):
        {
            "subscriber_ids": ["sub_123", "sub_456"],  # Optional: specific subscribers
            "date": "2026-01-11"                       # Optional: target date
        }
    
    Returns:
        {
            "success": true,
            "generated": 15,
            "failed": 2,
            "predictions": [...]
        }
    """
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    try:
        logger.info(f"Received {request.method} request to /api/predictions/generate")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.content_type}")
        
        # Accept both GET and POST, handle missing/invalid JSON gracefully
        data = {}
        if request.method == 'POST':
            try:
                if request.content_type and 'json' in request.content_type:
                    data = request.get_json(force=True, silent=True) or {}
                else:
                    # Try to parse as form data or query params
                    data = request.form.to_dict() or request.args.to_dict() or {}
            except Exception as e:
                logger.warning(f"Could not parse request data: {e}")
                data = {}
        
        target_date = data.get('date') or datetime.now().strftime("%Y-%m-%d")
        specific_subscribers = data.get('subscriber_ids')
        
        logger.info(f"Generating predictions for {target_date}")
        
        # Load all subscribers
        all_subscribers = get_all_subscribers()
        
        # Filter if specific subscribers requested
        if specific_subscribers:
            all_subscribers = [
                s for s in all_subscribers 
                if s.get('subscriber_id') in specific_subscribers
            ]
        
        results = {
            "success": True,
            "date": target_date,
            "generated": 0,
            "failed": 0,
            "predictions": [],
            "errors": []
        }
        
        # Generate predictions for each subscriber
        for subscriber in all_subscribers:
            subscriber_id = subscriber.get('subscriber_id', 'unknown')
            config_file = subscriber.get('config_file')
            kit = subscriber.get('kit')
            
            logger.info(f"Processing {subscriber_id} ({kit}/{config_file})")
            
            # Run prediction engine (v3.7 jackpot games)
            prediction_result = run_prediction_engine(config_file, kit)
            
            if not prediction_result.get('success'):
                results['failed'] += 1
                results['errors'].append({
                    "subscriber_id": subscriber_id,
                    "error": prediction_result.get('error')
                })
                continue
            
            # Get jackpot predictions
            predictions_data = prediction_result.get('predictions', {})
            
            # ENHANCEMENT: Add rare pattern predictions (triples + quads)
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            
            # Get overlay conditions for today
            overlay_conditions = get_overlay_conditions(target_date_obj)
            
            # Add triple predictions if engine available
            if triple_engine:
                try:
                    # Get all three sessions and merge
                    midday = triple_engine.predict_all_triples(target_date_obj, 'MIDDAY')
                    evening = triple_engine.predict_all_triples(target_date_obj, 'EVENING')
                    night = triple_engine.predict_all_triples(target_date_obj, 'NIGHT')
                    triple_best = {}
                    for pred in midday + evening + night:
                        triple = pred['triple']
                        if triple not in triple_best or pred['confidence'] > triple_best[triple]['confidence']:
                            triple_best[triple] = pred
                    triple_predictions = list(triple_best.values())
                    triple_predictions.sort(key=lambda x: x['confidence'], reverse=True)
                    
                    # Top 3 triples with confidence >= 80
                    top_triples = [p for p in triple_predictions if p['confidence'] >= 80][:3]
                    
                    predictions_data['rare_patterns'] = predictions_data.get('rare_patterns', {})
                    predictions_data['rare_patterns']['triples'] = []
                    
                    for pred in top_triples:
                        predictions_data['rare_patterns']['triples'].append({
                            "number": pred['triple'],
                            "confidence": round(pred['confidence'], 1),
                            "odds": f"1-in-{pred['context']['current_gap']}",
                            "session": pred['context']['session_best'].upper(),
                            "days_overdue": pred['context']['current_gap'],
                            "band": pred['band']
                        })
                    
                    logger.info(f"Added {len(top_triples)} triple predictions for {subscriber_id}")
                except Exception as e:
                    logger.error(f"Error adding triple predictions: {e}")
            
            # Add quad predictions if engine available
            if quad_engine:
                try:
                    # Get all three sessions and merge
                    midday = quad_engine.predict_all_quads(target_date_obj, 'MIDDAY')
                    evening = quad_engine.predict_all_quads(target_date_obj, 'EVENING')
                    night = quad_engine.predict_all_quads(target_date_obj, 'NIGHT')
                    quad_best = {}
                    for pred in midday + evening + night:
                        quad = pred['quad']
                        if quad not in quad_best or pred['confidence'] > quad_best[quad]['confidence']:
                            quad_best[quad] = pred
                    quad_predictions = list(quad_best.values())
                    quad_predictions.sort(key=lambda x: x['confidence'], reverse=True)
                    
                    # Top 3 quads with confidence >= 80
                    top_quads = [p for p in quad_predictions if p['confidence'] >= 80][:3]
                    
                    if 'rare_patterns' not in predictions_data:
                        predictions_data['rare_patterns'] = {}
                    predictions_data['rare_patterns']['quads'] = []
                    
                    for pred in top_quads:
                        days_overdue = pred['context'].get('current_gap') or pred['context'].get('days_since', 0)
                        session_best = pred['context'].get('session_best', 'MIDDAY').upper()
                        
                        predictions_data['rare_patterns']['quads'].append({
                            "number": pred['quad'],
                            "confidence": round(pred['confidence'], 1),
                            "odds": f"1-in-{days_overdue}",
                            "session": session_best,
                            "days_overdue": days_overdue,
                            "band": pred['band']
                        })
                    
                    logger.info(f"Added {len(top_quads)} quad predictions for {subscriber_id}")
                except Exception as e:
                    logger.error(f"Error adding quad predictions: {e}")
            
            # Add overlay conditions
            predictions_data['overlay_conditions'] = overlay_conditions
            predictions_data['overlay_interpretation'] = overlay_conditions.get('interpretation', 'BASELINE')
            
            # Push to Base44
            if predictions_data:
                push_result = base44.create_prediction(
                    subscriber_id=subscriber_id,
                    date=target_date,
                    predictions=predictions_data
                )
                
                if push_result.get('success'):
                    results['generated'] += 1
                    results['predictions'].append({
                        "subscriber_id": subscriber_id,
                        "prediction_id": push_result.get('prediction_id'),
                        "games": list(predictions_data.keys())
                    })
                    
                    # Send SMS notification if enabled and subscriber has phone
                    if twilio.is_connected() and subscriber.get('phone'):
                        try:
                            # Convert predictions dict to list format for SMS
                            pred_list = []
                            for game, game_predictions in predictions_data.items():
                                if isinstance(game_predictions, list) and game_predictions:
                                    pred_list.append({
                                        'game': game,
                                        'number': game_predictions[0].get('number'),
                                        'confidence': game_predictions[0].get('confidence'),
                                        'band': game_predictions[0].get('band')
                                    })
                            
                            sms_result = twilio.send_prediction_alert(
                                subscriber=subscriber,
                                predictions=pred_list,
                                date=target_date
                            )
                            
                            if sms_result.get('success'):
                                logger.info(f"SMS sent to {subscriber_id}")
                            else:
                                logger.warning(f"SMS failed for {subscriber_id}: {sms_result.get('error')}")
                        except Exception as sms_error:
                            logger.error(f"SMS error for {subscriber_id}: {sms_error}")
                    
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        "subscriber_id": subscriber_id,
                        "error": f"Failed to push to Base44: {push_result.get('error')}"
                    })
            else:
                results['failed'] += 1
                results['errors'].append({
                    "subscriber_id": subscriber_id,
                    "error": "No predictions generated"
                })
        
        logger.info(f"Generation complete: {results['generated']} success, {results['failed']} failed")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in generate_predictions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/predictions/generate/<subscriber_id>', methods=['POST', 'GET'])
def generate_single_prediction(subscriber_id: str):
    """
    Generate prediction for a single subscriber
    
    Args:
        subscriber_id: Base44 subscriber ID
    
    Request body (optional):
        {
            "date": "2026-01-11",
            "date_of_birth": "1985-08-26",  // If subscriber not in local configs
            "kit": "BOOK3",                  // Required for inline generation
            "email": "user@example.com",
            "full_name": "User Name"
        }
    
    Returns:
        {
            "success": true,
            "prediction_id": "pred_xyz",
            "games": ["Cash3", "Cash4", ...]
        }
    """
    try:
        # Handle both POST (JSON body) and GET (query params)
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = {}
        
        target_date = data.get('date') or request.args.get('date') or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Generating prediction for {subscriber_id} on {target_date}")
        
        # Find subscriber config in local files
        all_subscribers = get_all_subscribers()
        subscriber = next((s for s in all_subscribers if s.get('subscriber_id') == subscriber_id), None)
        
        # If not found locally, check if inline subscriber data provided (from Base44 webhook)
        if not subscriber and data.get('date_of_birth') and data.get('kit'):
            logger.info(f"Subscriber {subscriber_id} not in local configs - using inline data from webhook")
            subscriber = {
                'subscriber_id': subscriber_id,
                'dob': data.get('date_of_birth'),
                'kit': data.get('kit'),
                'email': data.get('email'),
                'full_name': data.get('full_name'),
                'inline_data': True  # Flag to skip file-based processing
            }
        
        if not subscriber:
            return jsonify({
                "success": False,
                "error": f"Subscriber {subscriber_id} not found and no inline data provided"
            }), 404
        
        # Generate predictions based on data source
        if subscriber.get('inline_data'):
            # Use inline subscriber data (from Base44 webhook)
            prediction_result = generate_predictions_from_inline_data(
                subscriber_id=subscriber_id,
                dob=subscriber.get('dob'),
                kit=subscriber.get('kit'),
                target_date=target_date
            )
        else:
            # Use traditional file-based approach
            prediction_result = run_prediction_engine(
                subscriber.get('config_file'),
                subscriber.get('kit')
            )
        
        if not prediction_result.get('success'):
            return jsonify({
                "success": False,
                "error": prediction_result.get('error')
            }), 500
        
        # Push to Base44
        predictions_data = prediction_result.get('predictions')
        push_result = base44.create_prediction(
            subscriber_id=subscriber_id,
            date=target_date,
            predictions=predictions_data
        )
        
        if not push_result.get('success'):
            return jsonify({
                "success": False,
                "error": f"Failed to push to Base44: {push_result.get('error')}"
            }), 500
        
        return jsonify({
            "success": True,
            "subscriber_id": subscriber_id,
            "prediction_id": push_result.get('prediction_id'),
            "date": target_date,
            "games": list(predictions_data.keys())
        })
        
    except Exception as e:
        logger.error(f"Error generating single prediction: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting My Best Odds API Server on port {port}")
    logger.info(f"Base44 connected: {base44.is_connected()}")
    logger.info(f"Twilio connected: {twilio.is_connected()}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
