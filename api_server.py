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

# Runtime-injected draw results (survive until next redeploy).
# Key: e.g. "cash3_eve" — Value: list of normalized draw dicts
_ga_extra_entries: Dict[str, List] = {
    "cash3_mid": [], "cash3_eve": [], "cash3_night": [],
    "cash4_mid": [], "cash4_eve": [], "cash4_night": [],
}


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

    # Merge any runtime-injected entries (from /api/results/ingest)
    for key, extras in _ga_extra_entries.items():
        for entry in extras:
            if entry not in results[key]:
                results[key].append(entry)

    return results


def get_predictions_for_date(date_str: str, kit: str, subscriber: dict = None) -> List[Dict]:
    """Get predictions by calling pick_engine_v3 directly (no subprocess)."""
    try:
        from core.pick_engine_v3 import generate_picks_v3
        from pathlib import Path

        ga_data = _load_ga_data_from_json()
        root    = Path(JACKPOT_SYSTEM_DIR)

        # Use real subscriber data when provided; fall back to generic identity
        if not subscriber:
            subscriber = {"initials": "MBO", "games": ["Cash3", "Cash4"]}

        picks = generate_picks_v3(subscriber, None, ga_data, root)

        # Extract per-game stats for confidence scoring, then remove the
        # internal key so it doesn't leak into the predictions loop below.
        raw_stats = picks.pop("_stats", {})
        c3_stats  = raw_stats.get("cash3", {})
        c4_stats  = raw_stats.get("cash4", {})
        c3_max    = max((v["score"] for v in c3_stats.values()), default=1.0) or 1.0
        c4_max    = max((v["score"] for v in c4_stats.values()), default=1.0) or 1.0

        predictions = []
        for game, lane_data in picks.items():
            for lane, numbers in lane_data.items():
                for number in (numbers or []):
                    if number:
                        # Normalized confidence from engine stats (0.0–1.0).
                        # Picks not found in stats (e.g. pure permutations from
                        # the signal family) receive a conservative default.
                        if game == "Cash3" and c3_stats:
                            raw_score = c3_stats.get(str(number), {}).get("score", 1.0)
                            conf = round(min(raw_score / c3_max, 1.0), 4)
                        elif game == "Cash4" and c4_stats:
                            raw_score = c4_stats.get(str(number), {}).get("score", 1.0)
                            conf = round(min(raw_score / c4_max, 1.0), 4)
                        else:
                            conf = None
                        predictions.append({
                            "game":             game,
                            "number":           str(number),
                            "date":             date_str,
                            "lane":             lane,
                            "kit":              kit,
                            "confidence_score": conf,
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

        # Generate MMFSN profile file so the pick engine can load it per-subscriber.
        # mmfsn data may arrive as a top-level "mmfsn" key or inside birth_profile.
        mmfsn_data = body.get("mmfsn") or birth_profile.get("mmfsn") or {}
        initials = (
            birth_profile.get("initials")
            or birth_profile.get("subscriber_initials")
            or ""
        ).upper()
        if mmfsn_data:
            try:
                mmfsn_dir = os.path.join(JACKPOT_SYSTEM_DIR, "data", "mmfsn_profiles")
                os.makedirs(mmfsn_dir, exist_ok=True)
                MAX_PER_GAME = 5
                mmfsn_clean = {
                    "Cash3": (mmfsn_data.get("Cash3") or mmfsn_data.get("cash3") or [])[-MAX_PER_GAME:],
                    "Cash4": (mmfsn_data.get("Cash4") or mmfsn_data.get("cash4") or [])[-MAX_PER_GAME:],
                }
                profile_payload = {
                    "initials":        initials,
                    "subscriber_id":   subscriber_id,
                    "mmfsn_numbers":   mmfsn_clean,
                    "weight":          0.60,
                    "notes":           "Generated by subscribers_sync",
                }
                # Primary key: subscriber UUID (collision-proof)
                uuid_path = os.path.join(mmfsn_dir, f"{subscriber_id}_mmfsn.json")
                with open(uuid_path, "w", encoding="utf-8") as f:
                    json.dump(profile_payload, f, indent=2)
                # Secondary key: initials (backwards compat + pick engine lookup)
                if initials:
                    init_path = os.path.join(mmfsn_dir, f"{initials}_mmfsn.json")
                    with open(init_path, "w", encoding="utf-8") as f:
                        json.dump(profile_payload, f, indent=2)
                logger.info(f"MMFSN profile written: uuid={subscriber_id} initials={initials or '(none)'} "
                            f"({len(mmfsn_clean['Cash3'])} Cash3, {len(mmfsn_clean['Cash4'])} Cash4)")
            except Exception as _e:
                logger.warning(f"MMFSN profile generation failed for {subscriber_id}: {_e}")

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

        # Load persisted subscriber record (written by /api/subscribers/sync)
        subscriber_record = {"initials": "MBO", "games": ["Cash3", "Cash4"]}
        record_path = os.path.join(SUBSCRIBERS_DIR, f"{subscriber_id}.json")
        if os.path.exists(record_path):
            try:
                with open(record_path, "r", encoding="utf-8") as _f:
                    _rec = json.load(_f)
                birth = _rec.get("birth_profile") or {}
                initials = (
                    birth.get("initials")
                    or birth.get("subscriber_initials")
                    or _rec.get("initials")
                    or "MBO"
                ).upper()
                subscriber_record = {
                    "initials":     initials,
                    "subscriber_id": subscriber_id,
                    "games":        ["Cash3", "Cash4"],
                    "birthdate":    birth.get("dob") or birth.get("birth_date") or "",
                    "birthtime":    birth.get("tob") or birth.get("birth_time") or "",
                    "birthplace":   birth.get("pob") or birth.get("birth_place") or "",
                }
            except Exception as _e:
                logger.warning(f"Could not load subscriber record for {subscriber_id}: {_e}")

        all_predictions = get_predictions_for_date(date_str, kit, subscriber=subscriber_record)

        # Group by game, preserving per-pick metadata
        grouped: Dict[str, List] = {}
        for p in all_predictions:
            game = p.get("game", "Unknown")
            grouped.setdefault(game, []).append({
                "number":           p.get("number"),
                "kit":              p.get("kit"),
                "lane":             p.get("lane"),
                "confidence_score": p.get("confidence_score"),
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
        logger.warning(f"Near-miss advice skipped: {e}", exc_info=True)
        return {
            "cash3": [],
            "cash4": [],
            "summary": "Near-miss analysis unavailable.",
            "has_near_misses": False,
        }


@app.route('/api/results/ingest', methods=['POST'])
def results_ingest():
    """
    Called by the Lovable scraper edge function after each draw is published.
    Appends the result to the in-memory ga_data cache so near-miss advice and
    predictions use it immediately, and also persists it to the JSON file on disk
    (best-effort — a Railway redeploy will reload from the last committed JSON).

    POST /api/results/ingest
    Header: X-Prediction-Secret: <secret>
    Body:
        {
          "game":           "Cash3" | "Cash4",
          "session":        "midday" | "evening" | "night",
          "date":           "2026-04-22",   // YYYY-MM-DD
          "winning_number": "507",
          "dryRun":         true            // optional — validate + idempotency check only, no writes
        }

    dryRun can also be passed as a query string: ?dryRun=true

    Response (normal):
        { "success": true, "game": "Cash3", "session": "evening",
          "date": "2026-04-22", "winning_number": "507" }

    Response (dryRun=true):
        { "success": true, "dryRun": true, "would_write": true,
          "already_present": false, "entry": {...}, ... }
    """
    if not _check_prediction_secret():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        body = request.get_json(silent=True) or {}
        dry_run        = bool(body.get("dryRun") or request.args.get("dryRun") == "true")
        game           = (body.get("game") or "").strip()
        session_raw    = (body.get("session") or "").strip().lower()
        date_str       = (body.get("date") or "").strip()
        winning_number = str(body.get("winning_number") or "").strip()

        # --- Validate inputs ---------------------------------------------------
        valid_games    = {"Cash3", "Cash4"}
        session_map    = {"midday": "mid", "evening": "eve", "night": "night"}
        file_map_rev   = {
            "cash3_mid":   "cash3_midday.json",
            "cash3_eve":   "cash3_evening.json",
            "cash3_night": "cash3_night.json",
            "cash4_mid":   "cash4_midday.json",
            "cash4_eve":   "cash4_evening.json",
            "cash4_night": "cash4_night.json",
        }

        if game not in valid_games:
            return jsonify({"success": False,
                            "error": f"game must be one of {sorted(valid_games)}"}), 400
        if session_raw not in session_map:
            return jsonify({"success": False,
                            "error": f"session must be one of {sorted(session_map)}"}), 400
        if not date_str:
            return jsonify({"success": False, "error": "date is required (YYYY-MM-DD)"}), 400
        if not winning_number:
            return jsonify({"success": False, "error": "winning_number is required"}), 400

        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False,
                            "error": "date must be in YYYY-MM-DD format"}), 400

        # Validate winning_number is digits only
        if not winning_number.isdigit():
            return jsonify({"success": False,
                            "error": "winning_number must be numeric digits"}), 400

        # Expected digit length
        expected_len = 3 if game == "Cash3" else 4
        if len(winning_number) != expected_len:
            return jsonify({"success": False,
                            "error": f"{game} winning_number must be {expected_len} digits"}), 400

        # --- Build cache key and normalized entry ------------------------------
        sess_key  = session_map[session_raw]
        cache_key = f"{game.lower()}_{sess_key}"   # e.g. "cash3_eve"

        entry = {
            "draw_date":       date_str,
            "winning_numbers": winning_number,
            "session":         session_raw.capitalize(),
        }

        # --- Idempotency check (same logic used for real writes) ---------------
        already_present = date_str in {e["draw_date"] for e in _ga_extra_entries[cache_key]}

        # --- Dry-run: return what would happen without touching anything -------
        if dry_run:
            logger.info(f"[ingest:dryRun] {cache_key} {date_str} → {winning_number} "
                        f"would_write={not already_present}")
            return jsonify({
                "success":         True,
                "dryRun":          True,
                "would_write":     not already_present,
                "already_present": already_present,
                "entry":           entry,
                "game":            game,
                "session":         session_raw,
                "date":            date_str,
                "winning_number":  winning_number,
            }), 200

        # --- Update in-memory buffer (idempotent) ------------------------------
        if not already_present:
            _ga_extra_entries[cache_key].append(entry)
            logger.info(f"[ingest] in-memory: {cache_key} {date_str} → {winning_number}")
        else:
            logger.info(f"[ingest] duplicate skipped (already in memory): {cache_key} {date_str}")

        # --- Persist to JSON file (best-effort) --------------------------------
        ga_dir   = os.path.join(JACKPOT_SYSTEM_DIR, "data", "ga_results")
        filename = file_map_rev[cache_key]
        filepath = os.path.join(ga_dir, filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
            else:
                disk_data = []

            # Idempotent: only append if this date is not already on disk
            disk_dates = {
                r.get("draw_date") or r.get("date", "") for r in disk_data
            }
            if date_str not in disk_dates:
                # Store in the same format as the existing JSON entries
                disk_entry = {
                    "date":           date_str,
                    "winning_number": winning_number,
                    "session":        session_raw.capitalize(),
                    "draw_date":      date_str,
                }
                disk_data.append(disk_entry)
                os.makedirs(ga_dir, exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(disk_data, f, indent=2)
                logger.info(f"[ingest] disk write OK: {filename}")
            else:
                logger.info(f"[ingest] disk already has {date_str} in {filename}, skipped")
        except Exception as disk_err:
            # Non-fatal — in-memory update already succeeded
            logger.warning(f"[ingest] disk write failed (non-fatal): {disk_err}")

        return jsonify({
            "success":        True,
            "game":           game,
            "session":        session_raw,
            "date":           date_str,
            "winning_number": winning_number,
        }), 200

    except Exception as e:
        logger.error(f"results_ingest error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/prune-mmfsn', methods=['POST'])
def admin_prune_mmfsn():
    """
    One-time admin utility: remove auto-generated dummy MMFSN profiles
    (AAA_mmfsn.json through ZZZ_mmfsn.json) that have empty Cash3/Cash4 arrays.
    Leaves any profile that has actual numbers stored.
    Header: X-Prediction-Secret required.
    """
    if not _check_prediction_secret():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    mmfsn_dir = os.path.join(JACKPOT_SYSTEM_DIR, "data", "mmfsn_profiles")
    if not os.path.exists(mmfsn_dir):
        return jsonify({"success": True, "deleted": 0, "kept": 0}), 200

    deleted, kept = 0, 0
    for fname in os.listdir(mmfsn_dir):
        if not fname.endswith("_mmfsn.json"):
            continue
        fpath = os.path.join(mmfsn_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            nums = data.get("mmfsn_numbers", {})
            has_data = bool(nums.get("Cash3") or nums.get("Cash4"))
            if not has_data:
                os.remove(fpath)
                deleted += 1
            else:
                kept += 1
        except Exception:
            kept += 1  # don't delete files we can't parse

    logger.info(f"MMFSN prune: deleted={deleted} kept={kept}")
    return jsonify({"success": True, "deleted": deleted, "kept": kept}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
