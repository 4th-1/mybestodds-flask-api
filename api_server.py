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

# Add jackpot_system_v3 to path so core modules can be imported directly
if JACKPOT_SYSTEM_DIR not in sys.path:
    sys.path.insert(0, JACKPOT_SYSTEM_DIR)

# Detect OS and use correct Python path
if platform.system() == "Windows":
    PYTHON_EXE = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
else:  # Linux/Unix (Railway uses /opt/venv)
    # Try Railway's Nixpacks venv first, fall back to local .venv
    if os.path.exists("/opt/venv/bin/python"):
        PYTHON_EXE = "/opt/venv/bin/python"
    elif os.path.exists("/app/.venv/bin/python"):
        PYTHON_EXE = "/app/.venv/bin/python"
    else:
        PYTHON_EXE = "python3"  # system fallback

RUN_KIT_SCRIPT = os.path.join(JACKPOT_SYSTEM_DIR, "run_kit_v3.py")


def _load_ga_data_from_json() -> Dict:
    """Load GA historical draw data from JSON files in data/ga_results/"""
    results = {
        "cash3_mid": [], "cash3_eve": [], "cash3_night": [],
        "cash4_mid": [], "cash4_eve": [], "cash4_night": [],
    }
    ga_dir = os.path.join(JACKPOT_SYSTEM_DIR, "data", "ga_results")
    if not os.path.exists(ga_dir):
        logger.warning("GA results dir not found — using empty data (fallback random picks)")
        return results

    file_map = {
        "cash3_midday.json":  "cash3_mid",
        "cash3_evening.json": "cash3_eve",
        "cash3_night.json":   "cash3_night",
        "cash4_midday.json":  "cash4_mid",
        "cash4_evening.json": "cash4_eve",
        "cash4_night.json":   "cash4_night",
    }
    for filename, key in file_map.items():
        filepath = os.path.join(ga_dir, filename)
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                # Normalize field name: JSON uses 'winning_number' (singular)
                num = item.get("winning_number") or item.get("winning_numbers", "")
                results[key].append({
                    "draw_date":       item.get("date", ""),
                    "winning_numbers": str(num),
                    "session":         item.get("session", ""),
                })
        except Exception as e:
            logger.warning(f"Could not load {filename}: {e}")
    return results


def get_predictions_for_date(date_str: str, kit: str) -> List[Dict]:
    """Get predictions by calling pick_engine_v3 directly (no subprocess)."""
    try:
        from core.pick_engine_v3 import generate_picks_v3
        from pathlib import Path

        ga_data   = _load_ga_data_from_json()
        subscriber = {"initials": "MBO", "games": ["Cash3", "Cash4"]}
        root       = Path(JACKPOT_SYSTEM_DIR)

        picks = generate_picks_v3(subscriber, None, ga_data, root)

        predictions = []
        for game, lane_data in picks.items():
            for lane, numbers in lane_data.items():
                for number in (numbers or []):
                    if number:
                        predictions.append({
                            "game":   game,
                            "number": str(number),
                            "date":   date_str,
                            "lane":   lane,
                            "kit":    kit,
                        })
        return predictions

    except Exception as e:
        logger.error(f"get_predictions_for_date error: {e}", exc_info=True)
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
        "python_exe": PYTHON_EXE,
        "run_kit_exists": os.path.exists(RUN_KIT_SCRIPT),
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to diagnose engine issues"""
    import subprocess
    kit = request.args.get('kit', 'BOOK3')
    kit_file_map = {
        "BOOK3": os.path.join(JACKPOT_SYSTEM_DIR, "kits", "3Base44ReadyBOOK3.json"),
        "BOOK":  os.path.join(JACKPOT_SYSTEM_DIR, "kits", "Base44ReadyBOOK.json"),
    }
    subscriber_file = kit_file_map.get(kit, '')
    # Quick test run
    cmd = [PYTHON_EXE, RUN_KIT_SCRIPT, '--subscriber', subscriber_file, '--kit', kit, '--output', '/tmp/debug_test', '--days', '1']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return jsonify({
            "python_exe": PYTHON_EXE,
            "python_exists": os.path.exists(PYTHON_EXE),
            "run_kit_script": RUN_KIT_SCRIPT,
            "run_kit_exists": os.path.exists(RUN_KIT_SCRIPT),
            "subscriber_file": subscriber_file,
            "subscriber_exists": os.path.exists(subscriber_file),
            "returncode": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500]
        })
    except Exception as e:
        return jsonify({"error": str(e), "python_exe": PYTHON_EXE, "python_exists": os.path.exists(PYTHON_EXE)})


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
        mfl_preds = [p for p in predictions if p.get("game") == "Millionaire For Life"]
        
        return jsonify({
            "success": True,
            "date": date_str,
            "game": "Millionaire For Life",
            "predictions": mfl_preds[:1] if mfl_preds else [],
            "total_predictions": len(mfl_preds)
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/predictions/generate/<subscriber_id>', methods=['GET', 'POST'])
def generate_predictions(subscriber_id: str):
    """
    Unified prediction endpoint called by the Lovable edge function.
    POST /api/predictions/generate/<subscriberId>
    Body (optional JSON): { "date": "YYYY-MM-DD", "games": ["Cash3", "Cash4", ...] }
    Returns all picks for the requested date grouped by game, plus near-miss advice.
    """
    try:
        body = {}
        if request.is_json:
            body = request.get_json(silent=True) or {}

        date_str = (
            body.get("date")
            or request.args.get("date")
            or datetime.now().strftime("%Y-%m-%d")
        )
        requested_games = body.get("games") or request.args.getlist("games") or []
        kit = (
            body.get("kit")
            or request.args.get("kit")
            or "BOOK3"
        )

        all_predictions = get_predictions_for_date(date_str, kit)

        # Group by game, preserving per-pick metadata
        grouped: Dict[str, List] = {}
        for p in all_predictions:
            game = p.get("game", "Unknown")
            grouped.setdefault(game, []).append({
                "number": p.get("number"),
                "kit":    p.get("kit"),
                "lane":   p.get("lane"),
            })

        # Filter if caller asked for specific games
        if requested_games:
            grouped = {g: v for g, v in grouped.items() if g in requested_games}

        # Near-miss advice — compare current picks against recent actual draws
        near_miss_advice = _compute_near_miss_advice(
            cash3_picks=[p["number"] for p in grouped.get("Cash3", [])],
            cash4_picks=[p["number"] for p in grouped.get("Cash4", [])],
        )

        return jsonify({
            "success": True,
            "subscriber_id": subscriber_id,
            "date": date_str,
            "kit": kit,
            "predictions": grouped,
            "total_picks": sum(len(v) for v in grouped.values()),
            "near_miss_advice": near_miss_advice,
        }), 200

    except Exception as e:
        logger.error(f"generate_predictions error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/near-miss-advice/<subscriber_id>', methods=['GET'])
def near_miss_advice_endpoint(subscriber_id: str):
    """
    Dedicated near-miss correction endpoint.
    GET /api/near-miss-advice/<subscriberId>?games=Cash3,Cash4

    Returns subscriber-facing guidance: which digit was off, what to play next.
    Compares the subscriber's current picks against the most recent actual draws
    (up to 7 draws per session across Midday / Evening / Night).

    Response shape:
        {
          "success": true,
          "subscriber_id": "...",
          "near_miss_advice": {
            "cash3": [ { "pick", "actual", "position_label", "suggested_pick",
                         "message", "confidence_signal", ... }, ... ],
            "cash4": [ ... ],
            "summary": "Cash 3: 1 near-miss detected. ...",
            "has_near_misses": true
          }
        }
    """
    try:
        date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

        all_predictions = get_predictions_for_date(date_str, "BOOK3")
        grouped: Dict[str, List] = {}
        for p in all_predictions:
            game = p.get("game", "Unknown")
            grouped.setdefault(game, []).append(p.get("number"))

        advice = _compute_near_miss_advice(
            cash3_picks=grouped.get("Cash3", []),
            cash4_picks=grouped.get("Cash4", []),
        )

        return jsonify({
            "success": True,
            "subscriber_id": subscriber_id,
            "date": date_str,
            "near_miss_advice": advice,
        }), 200

    except Exception as e:
        logger.error(f"near_miss_advice error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _compute_near_miss_advice(
    cash3_picks: List[str],
    cash4_picks: List[str],
) -> Dict:
    """
    Helper: load GA draw data and run near-miss analysis.
    Returns the full report dict from build_near_miss_report().
    Falls back to an empty report on import or data errors.
    """
    try:
        from core.near_miss_advisor import build_near_miss_report
        ga_data = _load_ga_data_from_json()
        return build_near_miss_report(
            cash3_picks=cash3_picks,
            cash4_picks=cash4_picks,
            ga_data=ga_data,
        )
    except Exception as e:
        logger.warning(f"Near-miss advice skipped: {e}")
        return {
            "cash3": [],
            "cash4": [],
            "summary": "Near-miss analysis unavailable.",
            "has_near_misses": False,
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
