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
_PREDICTION_GATE_DISABLED = os.getenv("DISABLE_PREDICTION_GATE", "").strip().lower() in {
    "1", "true", "yes", "on"
}

# Runtime-injected draw results (survive until next redeploy).
# Key: e.g. "cash3_eve" — Value: list of normalized draw dicts
_ga_extra_entries: Dict[str, List] = {
    "cash3_mid": [], "cash3_eve": [], "cash3_night": [],
    "cash4_mid": [], "cash4_eve": [], "cash4_night": [],
}

# ── Ingest audit log ────────────────────────────────────────────────────────
# Persisted to disk at data/ingest_audit.json on every successful ingest.
# In-memory mirror for fast /api/engine/status reads without a disk round-trip.
_ingest_audit_log: List[Dict] = []

def _load_audit_log() -> None:
    """Load persisted audit log from disk into _ingest_audit_log at startup."""
    global _ingest_audit_log
    audit_path = os.path.join(JACKPOT_SYSTEM_DIR, "data", "ingest_audit.json")
    try:
        if os.path.exists(audit_path):
            with open(audit_path, "r", encoding="utf-8") as f:
                _ingest_audit_log = json.load(f)
    except Exception as e:
        logger.warning(f"[audit] could not load ingest_audit.json: {e}")

def _append_audit_log(game: str, session: str, date_str: str,
                     winning_number: str, source: str = "ingest") -> None:
    """Append one entry to the in-memory audit log and persist to disk (best-effort)."""
    entry = {
        "ingested_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "game":           game,
        "session":        session,
        "date":           date_str,
        "winning_number": winning_number,
        "source":         source,
    }
    _ingest_audit_log.append(entry)
    audit_path = os.path.join(JACKPOT_SYSTEM_DIR, "data", "ingest_audit.json")
    try:
        os.makedirs(os.path.dirname(audit_path), exist_ok=True)
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(_ingest_audit_log, f, indent=2)
    except Exception as e:
        logger.warning(f"[audit] disk write failed (non-fatal): {e}")

# Load persisted audit log at startup
_load_audit_log()


def _check_prediction_secret() -> bool:
    """Returns True if the request carries a valid prediction secret header."""
    if _PREDICTION_GATE_DISABLED:
        # Explicit maintenance/open-mode override.
        return True
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
        from jackpot_system_v3.core.pick_engine_v3 import _recommended_play, _confidence_ui
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        triple_preds = [p for p in predictions if p.get("game") in ["Cash3", "Triples"]]
        _gad = _load_ga_data_from_json()
        c3_history = [d["winning_numbers"] for d in _gad.get("cash3_mid", []) + _gad.get("cash3_eve", []) + _gad.get("cash3_night", [])]
        for p in triple_preds:
            _rp = _recommended_play(p.get("confidence_score") or 0.0, p.get("number", ""), c3_history)
            p["recommended_play"] = _rp
            p.update(_confidence_ui(_rp, p.get("lane", ""), game="Cash3"))
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
        from jackpot_system_v3.core.pick_engine_v3 import _recommended_play, _confidence_ui
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK")
        quad_preds = [p for p in predictions if p.get("game") in ["Cash4", "Quads"]]
        _gad = _load_ga_data_from_json()
        c4_history = [d["winning_numbers"] for d in _gad.get("cash4_mid", []) + _gad.get("cash4_eve", []) + _gad.get("cash4_night", [])]
        for p in quad_preds:
            _rp = _recommended_play(p.get("confidence_score") or 0.0, p.get("number", ""), c4_history)
            p["recommended_play"] = _rp
            p.update(_confidence_ui(_rp, p.get("lane", ""), game="Cash4"))
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


@app.route('/api/cash4/straight-rank', methods=['GET'])
def cash4_straight_rank():
    """
    Rank all straight orderings of a Cash4 box combination by session-specific
    positional frequency.  Percentages normalized to 100% across all orderings.

    Query parameters
    ----------------
    digits  : str — required. 4-digit box combo, e.g. '3618' or '1188'.
    session : str — required. midday | evening | night

    Available to BOOK, BOOK3, and BOSK tiers (all Cash4 subscribers).

    Response includes:
    - rankings : list of {rank, number, pct, label} — all unique orderings
    - session_context : per-position top digit + alignment flag for each input digit
    - aligned_positions : how many of the 4 input digit positions match session-top digits
    """
    try:
        if not _check_prediction_secret():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        from jackpot_system_v3.core.pick_engine_v3 import rank_cash4_straight_orderings
        digits = request.args.get('digits', '').strip()
        session = request.args.get('session', '').strip().lower()
        if not digits:
            return jsonify({'success': False, 'error': 'Missing required parameter: ?digits=3618'}), 400
        if not session:
            return jsonify({'success': False, 'error': 'Missing required parameter: ?session=midday|evening|night'}), 400
        result = rank_cash4_straight_orderings(digits, session)
        if not result.get('valid', True):
            return jsonify({'success': False, **result}), 400
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        logger.error(f"Cash4 straight rank error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/triples/due-signal', methods=['GET'])
def triples_due_signal():
    """
    Cash3 triple due-signal — predicts which same-digit numbers (000–999)
    are statistically overdue based on historical gap analysis.
    Five-factor model: overdue ratio, gap percentile, digit heat,
    frequency trend, max-gap breach.
    """
    try:
        from jackpot_system_v3.core.triple_due_signal import compute_due_signal
        result = compute_due_signal('Cash3')
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Triples due-signal error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/quads/due-signal', methods=['GET'])
def quads_due_signal():
    """
    Cash4 quad due-signal — predicts which same-digit numbers (0000–9999)
    are statistically overdue based on historical gap analysis.
    Five-factor model: overdue ratio, gap percentile, digit heat,
    frequency trend, max-gap breach.
    """
    try:
        from jackpot_system_v3.core.triple_due_signal import compute_due_signal
        result = compute_due_signal('Cash4')
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Quads due-signal error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/due-signal/check', methods=['GET'])
def due_signal_check():
    """
    Subscriber query: check whether a specific triple or quad is due to fall.

    Query parameters
    ----------------
    number : str  — required. e.g. '555' (Cash3 triple) or '3333' (Cash4 quad).

    Response includes:
    - Gap analysis (overdue ratio, gap percentile, max-gap breach)
    - Historical condition fingerprint (moon phase, zodiac, numerology,
      day-of-week, month, session affinity at every historical hit)
    - Today's celestial conditions vs. historical fingerprint (side-by-side)
    - Condition alignment score and verdict
    - Play advice (session, wager guide, play type)
    - Plain-English narrative
    """
    try:
        from jackpot_system_v3.core.triple_due_signal import check_number
        number = request.args.get('number', '').strip()
        if not number:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: ?number=555 (Cash3 triple) or ?number=3333 (Cash4 quad)"
            }), 400
        result = check_number(number)
        if not result.get('valid', True):
            return jsonify({"success": False, **result}), 400
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Due-signal check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/powerball/predict', methods=['GET'])
def predict_powerball():
    """Get Powerball predictions"""
    try:
        from jackpot_system_v3.core.pick_engine_v3 import _jackpot_confidence_ui
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        pb_preds = [p for p in predictions if p.get("game") == "Powerball"]
        _ui = _jackpot_confidence_ui("Powerball")
        for p in pb_preds:
            p.update(_ui)
        
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
        from jackpot_system_v3.core.pick_engine_v3 import _jackpot_confidence_ui
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        mm_preds = [p for p in predictions if p.get("game") == "Mega Millions"]
        _ui = _jackpot_confidence_ui("Mega Millions")
        for p in mm_preds:
            p.update(_ui)
        
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
        from jackpot_system_v3.core.pick_engine_v3 import _jackpot_confidence_ui
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        predictions = get_predictions_for_date(date_str, "BOOK3")
        mfl_preds = [p for p in predictions if p.get("game") == "Millionaire For Life"]
        _ui = _jackpot_confidence_ui("Millionaire For Life")
        for p in mfl_preds:
            p.update(_ui)
        
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
    layer1_armed = bool(_PREDICTION_SECRET) and not _PREDICTION_GATE_DISABLED

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
        requested_kit = (
            body.get("kit")
            or body.get("kit_type")
            or request.args.get("kit")
        )
        mmfsn = body.get("mmfsn") or {}

        # Load persisted subscriber record (written by /api/subscribers/sync)
        subscriber_record = {"initials": "MBO", "games": ["Cash3", "Cash4"], "tier": "book3"}
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
                    "tier":         (_rec.get("tier") or "bosk").lower(),
                    "games":        ["Cash3", "Cash4"],
                    "birthdate":    birth.get("dob") or birth.get("birth_date") or "",
                    "birthtime":    birth.get("tob") or birth.get("birth_time") or "",
                    "birthplace":   birth.get("pob") or birth.get("birth_place") or "",
                }
            except Exception as _e:
                logger.warning(f"Could not load subscriber record for {subscriber_id}: {_e}")

        tier_to_kit = {"book3": "BOOK3", "book": "BOOK", "bosk": "BOSK"}
        kit = (requested_kit or tier_to_kit.get(subscriber_record.get("tier"), "BOSK")).upper()

        all_predictions = get_predictions_for_date(date_str, kit, subscriber=subscriber_record)

        # Build game histories for pair-signal detection in _recommended_play
        _gad = _load_ga_data_from_json()
        _c3_hist = [d["winning_numbers"] for d in _gad.get("cash3_mid", []) + _gad.get("cash3_eve", []) + _gad.get("cash3_night", [])]
        _c4_hist = [d["winning_numbers"] for d in _gad.get("cash4_mid", []) + _gad.get("cash4_eve", []) + _gad.get("cash4_night", [])]

        # Group by game, preserving per-pick metadata
        grouped: Dict[str, List] = {}
        from jackpot_system_v3.core.pick_engine_v3 import (
            _recommended_play, _confidence_ui, _jackpot_confidence_ui,
            _box_type,
            _C4_BOX_PAYOUT, _C3_BOX_PAYOUT,
            _C4_STRAIGHT_BOX_STRAIGHT_PAYOUT, _C4_STRAIGHT_BOX_BOX_PAYOUT,
            _C3_STRAIGHT_BOX_STRAIGHT_PAYOUT, _C3_STRAIGHT_BOX_BOX_PAYOUT,
            _C3_STRAIGHT_PAYOUT, _C4_STRAIGHT_PAYOUT,
            _C3_PAIR_PAYOUT,
            _C3_COMBO_PAYOUT, _C3_COMBO_TICKET_COST,
            _C3_1OFF_STRAIGHT_MATCH_PAYOUT, _C3_1OFF_ONE_DIGIT_PAYOUT,
            _C3_1OFF_TWO_DIGIT_PAYOUT, _C3_1OFF_THREE_DIGIT_PAYOUT,
        )
        _JACKPOT_GAMES = {"Powerball", "Mega Millions", "MegaMillions", "Millionaire For Life"}
        for p in all_predictions:
            game = p.get("game", "Unknown")
            conf = p.get("confidence_score") or 0.0
            _lane = p.get("lane", "")
            if game in _JACKPOT_GAMES:
                _rp = "STRAIGHT"
                _ui = _jackpot_confidence_ui(game)
            else:
                hist = _c3_hist if game in ("Cash3", "Triples") else (_c4_hist if game in ("Cash4", "Quads") else None)
                _rp = _recommended_play(conf, p.get("number", ""), hist)
                _ui = _confidence_ui(_rp, _lane, game=game)

            pick_entry = {
                "number":           p.get("number"),
                "kit":              p.get("kit"),
                "lane":             _lane,
                "confidence_score": conf,
                "recommended_play": _rp,
                "confidence_label": _ui["label"],
                "confidence_color": _ui["color"],
                "confidence_tier":  _ui["tier"],
                "confidence_description": _ui["description"],
            }

            # Inject payout details for all play types
            _num = p.get("number", "")
            _is_c4 = game in ("Cash4", "Quads")
            _is_c3 = game in ("Cash3", "Triples")
            if _rp in ("BOX", "STRAIGHT_BOX") and (_is_c3 or _is_c4):
                _bt = _box_type(_num)
                pick_entry["box_type"] = _bt
                if _is_c4:
                    pick_entry["box_payout"] = _C4_BOX_PAYOUT.get(_bt)
                    if _rp == "STRAIGHT_BOX":
                        pick_entry["straight_box_straight_payout"] = _C4_STRAIGHT_BOX_STRAIGHT_PAYOUT.get(_bt)
                        pick_entry["straight_box_box_payout"] = _C4_STRAIGHT_BOX_BOX_PAYOUT.get(_bt)
                elif _is_c3:
                    pick_entry["box_payout"] = _C3_BOX_PAYOUT.get(_bt)
                    if _rp == "STRAIGHT_BOX":
                        pick_entry["straight_box_straight_payout"] = _C3_STRAIGHT_BOX_STRAIGHT_PAYOUT.get(_bt)
                        pick_entry["straight_box_box_payout"] = _C3_STRAIGHT_BOX_BOX_PAYOUT.get(_bt)
                    # Combo is the "all permutations" upgrade from BOX — always available for Cash3 box plays
                    if _bt in _C3_COMBO_TICKET_COST:
                        pick_entry["combo_payout"] = _C3_COMBO_PAYOUT
                        pick_entry["combo_ticket_cost"] = _C3_COMBO_TICKET_COST[_bt]
            elif _rp == "STRAIGHT" and (_is_c3 or _is_c4):
                pick_entry["straight_payout"] = _C3_STRAIGHT_PAYOUT if _is_c3 else _C4_STRAIGHT_PAYOUT
            elif _rp == "STRAIGHT+1OFF" and _is_c3:
                # 1-Off is a GA Cash3 product; include its payout tiers for all STRAIGHT+1OFF Cash3 picks
                pick_entry["straight_payout"] = _C3_STRAIGHT_PAYOUT
                pick_entry["one_off_straight_match_payout"] = _C3_1OFF_STRAIGHT_MATCH_PAYOUT
                pick_entry["one_off_one_digit_payout"]      = _C3_1OFF_ONE_DIGIT_PAYOUT
                pick_entry["one_off_two_digit_payout"]      = _C3_1OFF_TWO_DIGIT_PAYOUT
                pick_entry["one_off_three_digit_payout"]    = _C3_1OFF_THREE_DIGIT_PAYOUT
            elif _rp in ("FRONT_PAIR", "BACK_PAIR") and _is_c3:
                pick_entry["pair_payout"] = _C3_PAIR_PAYOUT

            # Option 1 — inject suggested_1off + full straight_rankings for STRAIGHT+1OFF Cash4 picks
            if _rp == "STRAIGHT+1OFF" and game in ("Cash4", "Quads"):
                try:
                    from jackpot_system_v3.core.pick_engine_v3 import rank_cash4_straight_orderings as _rank_ord
                    from datetime import datetime as _dt_now
                    # Derive session from current ET hour (approximate)
                    _et_hour = (_dt_now.utcnow().hour - 4) % 24  # rough ET offset
                    if _et_hour < 13:
                        _sess = "midday"
                    elif _et_hour < 20:
                        _sess = "evening"
                    else:
                        _sess = "night"
                    _ord_result = _rank_ord(p.get("number", ""), _sess)
                    if _ord_result.get("valid", True) and _ord_result.get("rankings"):
                        _rankings = _ord_result["rankings"]
                        # suggested_1off = highest-ranked ordering that differs from the main pick
                        _main_num = p.get("number", "")
                        _alt = next((r for r in _rankings if r["number"] != _main_num), None)
                        pick_entry["suggested_1off"] = _alt["number"] if _alt else None
                        pick_entry["suggested_1off_pct"] = _alt["pct"] if _alt else None
                        pick_entry["straight_rankings"] = _rankings
                        pick_entry["straight_session"] = _sess
                        pick_entry["aligned_positions"] = _ord_result.get("aligned_positions")
                except Exception as _e1off:
                    logger.warning(f"1off ranking failed for {p.get('number')}: {_e1off}")

            grouped.setdefault(game, []).append(pick_entry)

        # Inject MMFSN picks sent by the edge function (BOOK3 personal-number lane)
        if mmfsn and kit == "BOOK3":
            _inject_mmfsn_picks(grouped, mmfsn, subscriber_id, date_str)

        # BOSK tier — Cash3 and Cash4 only, no jackpot games
        _BOSK_GAMES = {"Cash3", "Cash4", "Triples", "Quads"}
        if kit == "BOSK":
            grouped = {g: v for g, v in grouped.items() if g in _BOSK_GAMES}

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
        valid_cash_games   = {"Cash3", "Cash4"}
        valid_jackpot_games = {"Powerball", "MegaMillions", "MillionaireForLife", "Cash4Life"}
        valid_games        = valid_cash_games | valid_jackpot_games
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

        # Jackpot games: store in a separate in-memory log — no session JSON files
        if game in valid_jackpot_games:
            entry = {
                "draw_date":       date_str,
                "winning_numbers": winning_number,
                "session":         session_raw.capitalize() if session_raw else "Evening",
                "game":            game,
            }
            if dry_run:
                return jsonify({"success": True, "dryRun": True, "would_write": True,
                                "game": game, "date": date_str,
                                "winning_number": winning_number}), 200
            cache_key = f"jackpot_{game.lower()}"
            already = date_str in {e["draw_date"] for e in _ga_extra_entries.get(cache_key, [])}
            if not already:
                _ga_extra_entries.setdefault(cache_key, []).append(entry)
                logger.info(f"[ingest:jackpot] {game} {date_str} → {winning_number}")
            return jsonify({"success": True, "game": game, "date": date_str,
                            "winning_number": winning_number}), 200
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
            _append_audit_log(game, session_raw, date_str, winning_number, source="ingest")
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


@app.route('/api/engine/status', methods=['GET'])
def engine_status():
    """
    GET /api/engine/status

    Returns a live snapshot of the course-correction engine state:
      - Last ingest per session with how many minutes/hours ago it occurred
      - Total draws loaded per session (JSON file + in-memory injected)
      - Current near-miss neighbor pool for Cash3 and Cash4
      - Ingest audit log (last 30 entries, newest first)
      - Whether any session is overdue (> 26 h since last ingest)

    No auth required — read-only diagnostic endpoint.
    """
    try:
        from jackpot_system_v3.core.pick_engine_v3 import _extract_near_miss_neighbors

        gad = _load_ga_data_from_json()

        # ── Draw counts per session ──────────────────────────────────────────
        session_counts = {
            k: len(v) for k, v in gad.items()
            if k.startswith("cash")
        }

        # ── Last ingest per session from audit log ───────────────────────────
        now_utc = datetime.utcnow()
        _sess_abbr = {"midday": "mid", "evening": "eve", "night": "night"}
        last_ingest: Dict[str, Dict] = {}
        for entry in reversed(_ingest_audit_log):
            abbr = _sess_abbr.get(entry.get("session", ""), "?")
            key = f"{entry['game'].lower()}_{abbr}"
            if key not in last_ingest:
                try:
                    ingested_dt = datetime.strptime(entry["ingested_at"], "%Y-%m-%dT%H:%M:%SZ")
                    minutes_ago = int((now_utc - ingested_dt).total_seconds() / 60)
                    last_ingest[key] = {
                        "draw_date":      entry["date"],
                        "winning_number": entry["winning_number"],
                        "ingested_at":    entry["ingested_at"],
                        "minutes_ago":    minutes_ago,
                        "overdue":        minutes_ago > 26 * 60,  # > 26 h
                    }
                except Exception:
                    pass

        # ── Near-miss neighbor pools ─────────────────────────────────────────
        cash3_history = (
            gad.get("cash3_mid", []) + gad.get("cash3_eve", []) + gad.get("cash3_night", [])
        )
        cash4_history = (
            gad.get("cash4_mid", []) + gad.get("cash4_eve", []) + gad.get("cash4_night", [])
        )
        try:
            from jackpot_system_v3.core.pick_engine_v3 import (
                _extract_near_miss_neighbors, _extract_combo_history,
                _extract_combo_history_dated, _build_combo_stats,
                NEAR_MISS_LOOKBACK, MIN_SCORE_FOR_CORRECTION,
                NEAR_MISS_BOOST_SCALE, DECAY_WEIGHT_90D, DECAY_WEIGHT_12MO,
                DECAY_WEIGHT_OLDER,
            )
            _decay = (DECAY_WEIGHT_90D, DECAY_WEIGHT_12MO, DECAY_WEIGHT_OLDER)

            c3_combos = _extract_combo_history(cash3_history, 3)
            c3_dated  = _extract_combo_history_dated(cash3_history, 3)
            c3_base   = _build_combo_stats(c3_combos, combo_dates=c3_dated, decay_weights=_decay)
            c3_neighbors = sorted(_extract_near_miss_neighbors(
                cash3_history, 3,
                lookback=NEAR_MISS_LOOKBACK,
                base_stats=c3_base,
                min_score=MIN_SCORE_FOR_CORRECTION,
            ))

            c4_combos = _extract_combo_history(cash4_history, 4)
            c4_dated  = _extract_combo_history_dated(cash4_history, 4)
            c4_base   = _build_combo_stats(c4_combos, combo_dates=c4_dated, decay_weights=_decay)
            c4_neighbors = sorted(_extract_near_miss_neighbors(
                cash4_history, 4,
                lookback=NEAR_MISS_LOOKBACK,
                base_stats=c4_base,
                min_score=MIN_SCORE_FOR_CORRECTION,
            ))

            # Last N source draws that seeded the neighbors
            c3_recent_source = []
            for item in reversed(cash3_history[-NEAR_MISS_LOOKBACK*3:]):
                raw = str(item.get("winning_numbers") or item.get("winning_number") or "").strip()
                if len(raw) == 3 and raw.isdigit() and raw not in c3_recent_source:
                    c3_recent_source.append(raw)
                    if len(c3_recent_source) >= NEAR_MISS_LOOKBACK:
                        break
            c4_recent_source = []
            for item in reversed(cash4_history[-NEAR_MISS_LOOKBACK*3:]):
                raw = str(item.get("winning_numbers") or item.get("winning_number") or "").strip()
                if len(raw) == 4 and raw.isdigit() and raw not in c4_recent_source:
                    c4_recent_source.append(raw)
                    if len(c4_recent_source) >= NEAR_MISS_LOOKBACK:
                        break
        except Exception as ne:
            logger.warning(f"[engine/status] neighbor pool error: {ne}")
            c3_neighbors, c4_neighbors = [], []
            c3_recent_source, c4_recent_source = [], []

        # ── Audit log tail (last 30, newest first) ───────────────────────────
        audit_tail = list(reversed(_ingest_audit_log[-30:]))

        # ── Overdue sessions ─────────────────────────────────────────────────
        overdue_sessions = [
            k for k, v in last_ingest.items() if v.get("overdue")
        ]

        return jsonify({
            "success":         True,
            "as_of":           now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "draw_counts":     session_counts,
            "last_ingest":     last_ingest,
            "overdue_sessions": overdue_sessions,
            "near_miss": {
                "lookback":          NEAR_MISS_LOOKBACK,
                "min_score_trigger": MIN_SCORE_FOR_CORRECTION,
                "boost_scale":       NEAR_MISS_BOOST_SCALE,
                "cash3": {
                    "source_draws":  c3_recent_source,
                    "neighbor_pool": c3_neighbors,
                    "neighbor_count": len(c3_neighbors),
                },
                "cash4": {
                    "source_draws":  c4_recent_source,
                    "neighbor_pool": c4_neighbors,
                    "neighbor_count": len(c4_neighbors),
                },
            },
            "decay_weights": {
                "90d":   DECAY_WEIGHT_90D,
                "12mo":  DECAY_WEIGHT_12MO,
                "older": DECAY_WEIGHT_OLDER,
            },
            "audit_log":       audit_tail,
            "total_ingests":   len(_ingest_audit_log),
        }), 200

    except Exception as e:
        logger.error(f"engine_status error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/results/fetch-latest', methods=['GET', 'POST'])
def fetch_latest_results():
    """
    Fetch today's GA Lottery results from lotterypost.com and auto-ingest them.

    Designed to be called by a free cron service (e.g. cron-job.org) 3× daily:
        12:45 PM ET  (17:45 UTC)  — after Midday draw at 12:29 PM
         7:15 PM ET  (00:15 UTC)  — after Evening draw at  6:59 PM
        11:50 PM ET  (04:50 UTC)  — after Night draw   at 11:34 PM

    Auth: X-Prediction-Secret header (same secret as other protected endpoints).
    Optional: ?dryRun=true to validate without writing.

    Response:
        { "success": true, "fetched": 6, "ingested": 3,
          "cash3_count": 3, "cash4_count": 3, "dry_run": false }
    """
    if not _check_prediction_secret():
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    dry_run = request.args.get("dryRun", "false").lower() == "true"

    try:
        from fetch_ga_results import fetch_and_ingest
        secret    = os.environ.get("PREDICTIONS_API_SECRET", "")
        self_url  = request.host_url.rstrip("/") + "/api/results/ingest"
        result    = fetch_and_ingest(self_url, secret, dry_run=dry_run)
        result["success"] = True
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"fetch-latest error: {e}", exc_info=True)
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
