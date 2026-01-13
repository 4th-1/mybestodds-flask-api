"""
MY BEST ODDS - Flask API Server
================================
Connects Python prediction engine (v3.7) to Base44 app
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
import subprocess
from datetime import datetime
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

# Import Base44 integration
from base44_integration import Base44Client
from twilio_integration import TwilioClient

# Initialize Base44 client (will use env variables)
base44 = Base44Client()
twilio = TwilioClient()

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SUBSCRIBERS_DIR = os.path.join(PROJECT_ROOT, "data", "subscribers")
PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")


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
            "run_kit_v3.py",
            f"{kit}/{subscriber_file}",
            kit
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
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
        "python_engine": "v3.7_recalibrated",
        "base44_connected": base44.is_connected(),
        "twilio_connected": twilio.is_connected()
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
            
            # Run prediction engine
            prediction_result = run_prediction_engine(config_file, kit)
            
            if not prediction_result.get('success'):
                results['failed'] += 1
                results['errors'].append({
                    "subscriber_id": subscriber_id,
                    "error": prediction_result.get('error')
                })
                continue
            
            # Push to Base44
            predictions_data = prediction_result.get('predictions')
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


@app.route('/api/predictions/generate/<subscriber_id>', methods=['POST'])
def generate_single_prediction(subscriber_id: str):
    """
    Generate prediction for a single subscriber
    
    Args:
        subscriber_id: Base44 subscriber ID
    
    Request body (optional):
        {
            "date": "2026-01-11"
        }
    
    Returns:
        {
            "success": true,
            "prediction_id": "pred_xyz",
            "games": ["Cash3", "Cash4", ...]
        }
    """
    try:
        data = request.get_json() or {}
        target_date = data.get('date') or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Generating prediction for {subscriber_id} on {target_date}")
        
        # Find subscriber config
        all_subscribers = get_all_subscribers()
        subscriber = next((s for s in all_subscribers if s.get('subscriber_id') == subscriber_id), None)
        
        if not subscriber:
            return jsonify({
                "success": False,
                "error": f"Subscriber {subscriber_id} not found"
            }), 404
        
        # Run prediction engine
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
