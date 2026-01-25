print("=== PROBE SCRIPT STARTED ===")

import sys
import datetime
import traceback
import os

print("PYTHON:", sys.executable)
print("CWD   :", os.getcwd())

# ---- Import rightside (Option A: correct architectural import) ----
try:
    from engines.rightside_v3_7 import rightside_engine_v3_6 as rs
    print("[OK] Imported engines.rightside_v3_7.rightside_engine_v3_6")
except Exception as e:
    print("[FAIL] Import rightside_engine_v3_6:", e)
    traceback.print_exc()
    raise

# ---- Find builder ----
build_fn = None
for name in ("build_engine_for_game", "build_engine", "get_engine_for_game", "engine_for_game"):
    if hasattr(rs, name):
        build_fn = getattr(rs, name)
        print(f"[OK] Using builder: {name}")
        break

if build_fn is None:
    raise RuntimeError("No engine builder found in rightside_engine_v3_6")

ROOT = r"C:\MyBestOdds\jackpot_system_v3"
paths = {
    "megamillions": rf"{ROOT}\data\results\jackpot_results\MegaMillions.csv",
    "powerball":    rf"{ROOT}\data\results\jackpot_results\Powerball.csv",
    "cash4life":    rf"{ROOT}\data\results\jackpot_results\Cash4Life.csv",
}

tier = "BOOK3"
today = datetime.date(2025, 12, 17)

def probe(engine, label, a, b):
    try:
        out = engine.generate_picks_for_range(a, b)
        n = 0 if out is None else len(out)
        print(f"{label}: len={n}")
        if isinstance(out, list) and n > 0:
            print(" sample:", out[:2])
    except Exception:
        print(f"[ERROR] {label}")
        traceback.print_exc()

for game, csv in paths.items():
    print("\n" + "="*60)
    print("GAME:", game)
    print("CSV :", csv)
    print("CSV exists:", os.path.exists(csv))

    engine = build_fn(game, tier, csv)
    print("ENGINE:", type(engine).__name__)

    probe(engine, "Exact day", today, today)
    probe(engine, "±7 days", today - datetime.timedelta(days=7), today + datetime.timedelta(days=7))
    probe(engine, "±30 days", today - datetime.timedelta(days=30), today + datetime.timedelta(days=30))
    probe(engine, "Fallback None,None", None, None)

print("\n=== PROBE COMPLETE ===")
