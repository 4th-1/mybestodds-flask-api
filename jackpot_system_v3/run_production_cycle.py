import os
import sys
import json
import glob
import pandas as pd
from pathlib import Path

# --- SETUP ---
ROOT_DIR = Path.cwd()
sys.path.insert(0, str(ROOT_DIR))

try:
    from core.engine_v3_7 import MyBestOddsEngineV37
    import make_final_sheet
except ImportError as e:
    print(f"❌ CRITICAL ERROR: {e}")
    sys.exit(1)

START_DATE = "2025-12-12"
END_DATE = "2025-12-31"
SUBSCRIBER_DIR = ROOT_DIR / "data" / "subscribers" / "BOOK3"
OUTPUT_DIR = ROOT_DIR / "DELIVERY" / f"BOOK3_{START_DATE}_to_{END_DATE}"

def cleanup():
    if not OUTPUT_DIR.exists(): return
    for f in OUTPUT_DIR.glob("*__to_.xlsx"):
        try: os.remove(f)
        except: pass
    for f in OUTPUT_DIR.glob(f"*_{START_DATE}_to_{END_DATE}.xlsx"):
        try: os.remove(f)
        except: pass

def main():
    print(f"🚀 STARTING FINAL PRODUCTION RUN")
    cleanup()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sub_files = list(SUBSCRIBER_DIR.glob("*.json"))
    
    for sub_file in sub_files:
        sub_name = sub_file.stem
        print(f"🔹 Processing: {sub_name}")

        try:
            with open(sub_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            engine = MyBestOddsEngineV37(config)
            rows = engine.generate_forecast(START_DATE, END_DATE, config)
            
            if not rows: continue

            clean_rows = []
            for r in rows:
                # 1. Date
                date_val = r.get("forecast_date") or START_DATE
                
                # 2. Game Display
                raw_game = str(r.get("game") or "Unknown").upper()
                if "CASH3" in raw_game: game_display = "Cash 3"
                elif "CASH4" in raw_game: game_display = "Cash 4"
                elif "MEGA" in raw_game: game_display = "Mega Millions"
                elif "POWER" in raw_game: game_display = "Powerball"
                elif "LIFE" in raw_game: game_display = "Cash4Life"
                else: game_display = raw_game.title()

                # 3. Number Formatting
                num = str(r.get("number", "")).strip()
                if "Cash 3" in game_display: num = num.zfill(3)
                if "Cash 4" in game_display and "Life" not in game_display: num = num.zfill(4)
                
                # 4. Verdict / Colors
                # The Excel Formatter usually looks for "STRONG PLAY", "PLAY (FUN)", etc.
                verdict = r.get("play_flag", "WATCH")
                
                clean_rows.append({
                    "Date": str(date_val),
                    "Game": game_display,
                    "Best Odds Verdict (BOV)": verdict,
                    "Your Numbers": num,
                    "Play Instruction": r.get("legend_text", ""),
                    "Confidence Score (%)": f"{float(r.get('confidence_score', 0))*100:.1f}%",
                    "My Best Odds (1 in X)": r.get("mbo_odds_text", ""),
                    "Official Lottery Odds": r.get("official_odds", ""), # <-- MAPS THE ODDS
                    "North Node Insight": r.get("north_node_insight", "")
                })

            target_xlsx = OUTPUT_DIR / f"{sub_name}_{START_DATE}_to_{END_DATE}.xlsx"
            df = pd.DataFrame(clean_rows)
            make_final_sheet.format_excel(df, str(target_xlsx))
            print(f"   ✅ SUCCESS: {target_xlsx.name}")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print(f"\n🏁 JOB DONE.")

if __name__ == "__main__":
    main()