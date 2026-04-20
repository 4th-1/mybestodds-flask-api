"""MY BEST ODDS - Flask API Server v3.0
=====================================
Connects Python prediction engine (v3.7) to Lovable frontend
Fixed entry point with proper prediction routing
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import hmac
import os
import secrets
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

# ── Subscription gate ────────────────────────────────────────────────────────
# PREDICTIONS_API_SECRET must be set in Railway env vars.
# The Lovable edge function must send this as the X-Prediction-Secret header
# AFTER verifying the user has an active Supabase subscription.
# Without the header, /api/predictions/generate returns 403.
_PREDICTION_SECRET = os.getenv("PREDICTIONS_API_SECRET", "")


def _check_prediction_secret() -> bool:
    """Returns True if the request carries a valid prediction secret header."""
    if not _PREDICTION_SECRET:
        # Secret not configured — allow through (dev/local mode)
        return True
    provided = request.headers.get("X-Prediction-Secret", "")
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(
        provided.encode("utf-8"),
        _PREDICTION_SECRET.encode("utf-8"),
    )


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


def _inject_mmfsn_picks(
    grouped: Dict[str, List],
    mmfsn: dict,
    subscriber_id: str,
    date_str: str,
) -> None:
    """
    Append MMFSN picks sent by the edge function into the grouped predictions dict.

    - Normalises game keys sent by the edge function ("Cash 3" → "Cash3", etc.)
    - Applies a per-day rotation so the subset surfaced varies daily without
      changing the master list.  Rotation seed = MD5(subscriber_id + date_str).
    - Each injected pick carries lane="lane_mmfsn" and source="mmfsn" so the
      frontend can distinguish system picks from personal-number picks.
    """
    # Edge function may send "Cash 3" / "Cash 4"; normalise to engine key names
    _key_map = {
        "Cash 3": "Cash3",
        "Cash3":  "Cash3",
        "Cash 4": "Cash4",
        "Cash4":  "Cash4",
    }
    _MAX_PER_GAME = 3  # max MMFSN picks surfaced per game per day

    seed_hex = hashlib.md5(f"{subscriber_id}{date_str}".encode()).hexdigest()
    seed_int = int(seed_hex, 16)

    for raw_game, numbers in mmfsn.items():
        game_key = _key_map.get(raw_game)
        if not game_key or not numbers:
            continue
        # Rotate: deterministic daily selection without repeating consecutively
        rotated = [numbers[(seed_int + i) % len(numbers)] for i in range(min(_MAX_PER_GAME, len(numbers)))]
        grouped.setdefault(game_key, [])
        for num in rotated:
            grouped[game_key].append({
                "number": str(num),
                "kit":    "BOOK3",
                "lane":   "lane_mmfsn",
                "source": "mmfsn",
            })


@app.route('/api/subscription/gate/<subscriber_id>', methods=['GET'])
def subscription_gate(subscriber_id: str):
    """
    Lightweight gate-check endpoint called by the Lovable route guard.
    GET /api/subscription/gate/<subscriberId>
         ?tier=book3   (optional — passed by edge function from Supabase profile)
         ?is_admin=true (optional — passed for admin bypass)

    NO secret required on this endpoint (it reveals nothing sensitive).
    Subscription status (active/cancelled) is Supabase's responsibility — the
    edge function should have already checked that before calling here.

    This endpoint tells the frontend:
      - whether Layer 1 (/api/predictions/generate) will accept its calls
        (i.e. is PREDICTIONS_API_SECRET configured and valid?)
      - the normalised tier string for the UI
      - whether the user is admin

    Response shape:
        {
          "access": true,
          "subscriber_id": "<uuid>",
          "tier": "book3" | "book" | "bosk" | null,
          "is_admin": false,
          "layer1_armed": true   <- false means secret not configured (dev mode)
        }

    If secret IS configured and the caller doesn't supply X-Prediction-Secret,
    access is still true here (gate is open) — Layer 1 is the hard boundary.
    """
    tier = (request.args.get("tier") or "").lower() or None
    is_admin = request.args.get("is_admin", "false").lower() == "true"
    layer1_armed = bool(_PREDICTION_SECRET)

    return jsonify({
        "access":        True,
        "subscriber_id": subscriber_id,
        "tier":          tier,
        "is_admin":      is_admin,
        "layer1_armed":  layer1_armed,
    }), 200


@app.route('/api/subscribers/sync', methods=['POST'])
def subscribers_sync():
    """
    Called by the Lovable check-subscription edge function whenever it confirms
    a paid tier.  Registers (or refreshes) the subscriber in Flask so that
    subsequent calls to /api/predictions/generate are unlocked.

    POST /api/subscribers/sync
    Header: X-Prediction-Secret: <secret>
    Body: { "id": "<uuid>", "tier": "book3"|"book"|"bosk", "birth_profile": {...} }

    Response:
        { "success": true, "subscriber_id": "<uuid>", "tier": "book3" }
    """
    if not _check_prediction_secret():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        body = request.get_json(silent=True) or {}
        subscriber_id = body.get("id") or body.get("subscriber_id", "")
        tier = (body.get("tier") or "").lower()
        birth_profile = body.get("birth_profile") or {}

        if not subscriber_id:
            return jsonify({"success": False, "error": "id is required"}), 400

        valid_tiers = {"book3", "book", "bosk"}
        if tier not in valid_tiers:
            tier = "bosk"  # safe default

        # Persist subscriber record so predictions work per-user
        os.makedirs(SUBSCRIBERS_DIR, exist_ok=True)
        record_path = os.path.join(SUBSCRIBERS_DIR, f"{subscriber_id}.json")
        record = {
            "subscriber_id": subscriber_id,
            "tier":          tier,
            "birth_profile": birth_profile,
            "synced_at":     datetime.utcnow().isoformat() + "Z",
        }
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        logger.info(f"Subscriber synced: {subscriber_id} tier={tier}")
        return jsonify({
            "success":       True,
            "subscriber_id": subscriber_id,
            "tier":          tier,
        }), 200

    except Exception as e:
        logger.error(f"subscribers_sync error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/predictions/generate/<subscriber_id>', methods=['GET', 'POST'])
def generate_predictions(subscriber_id: str):
    """
    Unified prediction endpoint called by the Lovable edge function.
    POST /api/predictions/generate/<subscriberId>
    Header: X-Prediction-Secret: <secret>   ← required when PREDICTIONS_API_SECRET is set
    Body (optional JSON): { "date": "YYYY-MM-DD", "games": ["Cash3", "Cash4", ...] }
    Returns all picks for the requested date grouped by game, plus near-miss advice.
    """
    if not _check_prediction_secret():
        logger.warning(f"Blocked unauthorised predictions request for subscriber {subscriber_id}")
        return jsonify({"success": False, "error": "Subscription required"}), 403

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
            or body.get("kit_type")
            or request.args.get("kit")
            or "BOOK3"
        ).upper()
        mmfsn = body.get("mmfsn") or {}

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

        # Inject MMFSN picks sent by the edge function (BOOK3 personal-number lane)
        if mmfsn and kit == "BOOK3":
            _inject_mmfsn_picks(grouped, mmfsn, subscriber_id, date_str)

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
