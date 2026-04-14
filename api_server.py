"""MY BEST ODDS - Flask API Server v3.0
=====================================
Connects Python prediction engine (v3.7) to Lovable frontend
Fixed entry point with proper prediction routing
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
import platform

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Configuration
JACKPOT_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "jackpot_system_v3")
SUBSCRIBERS_DIR = os.path.join(JACKPOT_SYSTEM_DIR, "subscribers")

# Detect OS and use correct Python path
if platform.system() == "Windows":
    PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
else:  # Linux/Unix (Railway)
    PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")

RUN_KIT_SCRIPT = os.path.join(JACKPOT_SYSTEM_DIR, "run_kit_v3.py")


def run_prediction_engine(subscriber_file: str, kit: str, start_date: str = None, num_days: int = 1) -> Dict:
    """Execute the prediction engine via run_kit_v3.py and parse results"""
    try:
        output_dir = "/tmp/mbo_predictions" if platform.system() != "Windows" else "C:\\temp\\mbo_predictions"
        os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            PYTHON_EXE,
            RUN_KIT_SCRIPT,
            "--subscriber", subscriber_file,
            "--kit", kit,
            "--output", output_dir,
            "--days", str(num_days)
        ]
        
        if start_date:
            cmd.extend(["--start-date", start_date])
        
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"Engine error: {result.stderr}")
            return {"error": result.stderr}
        
        # Find and parse summary.json
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f == "summary.json":
                    with open(os.path.join(root, f)) as fh:
                        return json.load(fh)
        
        return {"error": "No results generated"}
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"error": str(e)}


def get_predictions_for_date(date_str: str, kit: str) -> List[Dict]:
    """Get predictions for a specific date and kit"""
    try:
        # Map kit names to actual JSON config files
        kit_file_map = {
            "BOOK3": os.path.join(JACKPOT_SYSTEM_DIR, "kits", "3Base44ReadyBOOK3.json"),
            "BOOK":  os.path.join(JACKPOT_SYSTEM_DIR, "kits", "Base44ReadyBOOK.json"),
            "BOSK":  os.path.join(JACKPOT_SYSTEM_DIR, "kits", "BASE44_BOSK_ready_.json"),
        }
        subscriber_file = kit_file_map.get(kit, os.path.join(SUBSCRIBERS_DIR, kit, "subscriber_1.json"))
        if not os.path.exists(subscriber_file):
            logger.warning(f"Subscriber file not found: {subscriber_file}")
            return []
        
        # Run engine
        results = run_prediction_engine(subscriber_file, kit, date_str, 1)
        
        if "error" in results:
            logger.error(f"Engine failed: {results['error']}")
            return []
        
        # Extract predictions for requested date
        predictions = []
        for day in results.get("days", []):
            if day.get("date") == date_str:
                picks = day.get("picks", {})
                for game, picks_list in picks.items():
                    for pick in picks_list:
                        predictions.append({
                            "game": game,
                            "number": pick,
                            "date": date_str
                        })
        
        return predictions
        
    except Exception as e:
        logger.error(f"Get predictions error: {e}")
        return []


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "api_version": "v3.0-CLEAN",
        "frontend": "Lovable",
        "engine": "jackpot_system_v3",
        "randomization": "enabled",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/triples/predict', methods=['GET'])
def predict_triples():
    """Get Cash3 (triple) predictions"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        triple_preds = [p for p in predictions if p.get("game") in ["Cash3", "Triples"]]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Cash3",
            "predictions": triple_preds[:31],
            "total_predictions": len(triple_preds)
        }), 200
        
    except Exception as e:
        logger.error(f"Triples error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/quads/predict', methods=['GET'])
def predict_quads():
    """Get Cash4 (quad) predictions"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK")
        quad_preds = [p for p in predictions if p.get("game") in ["Cash4", "Quads"]]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Cash4",
            "predictions": quad_preds[:31],
            "total_predictions": len(quad_preds)
        }), 200
        
    except Exception as e:
        logger.error(f"Quads error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/powerball/predict', methods=['GET'])
def predict_powerball():
    """Get Powerball predictions"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        pb_preds = [p for p in predictions if p.get("game") == "Powerball"]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Powerball",
            "predictions": pb_preds[:1] if pb_preds else [],
            "total_predictions": len(pb_preds)
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/megamillions/predict', methods=['GET'])
def predict_megamillions():
    """Get Mega Millions predictions"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        mm_preds = [p for p in predictions if p.get("game") == "Mega Millions"]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Mega Millions",
            "predictions": mm_preds[:1] if mm_preds else [],
            "total_predictions": len(mm_preds)
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/millionaire-for-life/predict', methods=['GET'])
def predict_millionaire():
    """Get Millionaire For Life predictions"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        mfl_preds = [p for p in predictions if p.get("game") == "Millionaire_For_Life"]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Millionaire_For_Life",
            "predictions": mfl_preds[:1] if mfl_preds else [],
            "total_predictions": len(mfl_preds)
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
