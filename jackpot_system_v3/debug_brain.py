import os
import sys
import json
from pathlib import Path

# --- SETUP PATHS ---
ROOT_DIR = Path.cwd()
sys.path.insert(0, str(ROOT_DIR))

# --- DIAGNOSTIC START ---
print("🔍 STARTING BRAIN DIAGNOSTIC...")
print(f"📂 Root Directory: {ROOT_DIR}")

# 1. CHECK FILE EXISTENCE
enricher_path = ROOT_DIR / "core" / "row_enricher_v3_7.py"
if not enricher_path.exists():
    print(f"❌ CRITICAL FAIL: {enricher_path} does not exist!")
    print("👉 You need to make sure 'row_enricher_v3_7.py' is inside the 'core' folder.")
    sys.exit(1)
else:
    print(f"✅ Found row_enricher_v3_7.py")

# 2. ATTEMPT IMPORT (No Try/Except - Let it crash!)
print("🔄 Attempting to import Scoring Logic...")
try:
    from core.row_enricher_v3_7 import enrich_row_v3_7
    print("✅ Import SUCCESSFUL. The brain is loaded.")
except Exception as e:
    print("\n❌ IMPORT CRASHED! Here is the error:")
    print("-" * 40)
    print(e)
    print("-" * 40)
    print("👉 This error tells us exactly what file or library is missing.")
    sys.exit(1)

# 3. RUN TEST DATA
print("🧪 Running Test Data (Martin Taylor's 926)...")
test_row = {
    "game": "Cash 3",
    "game_code": "CASH3",
    "number": "926",
    "forecast_date": "2025-12-12",
    "draw_date": "2025-12-12",
    "draw_time": "EVENING",
    "kit_name": "BOOK3",
    "subscriber_id": "MT"
}

# Mock Subscriber Profile
test_sub = {
    "subscriber_id": "MT",
    "dob": "1971-12-16",
    "engine_profile": {"numerology": {}, "astrology": {}}
}

try:
    result = enrich_row_v3_7(test_row, test_sub)
    print("\n✅ CALCULATION SUCCESS!")
    print(f"🎯 Score: {result.get('confidence_score')}")
    print(f"🗣️ Insight: {result.get('north_node_insight')}")
    print(f"📊 Odds: {result.get('mbo_odds_text')}")
    
    if result.get('confidence_score') == 0.95 and result.get('confidence_band') == "GREEN":
        print("⚠️ WARNING: The result looks like the Default/Fallback.")
        print("This means the logic inside 'enrich_row' caught an error and returned a safe value.")
    
except Exception as e:
    print("\n❌ CALCULATION CRASHED! Here is the error:")
    print("-" * 40)
    import traceback
    traceback.print_exc()
    print("-" * 40)