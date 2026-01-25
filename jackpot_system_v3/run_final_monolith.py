import os
import sys
import json
import datetime
import pandas as pd
from pathlib import Path

# --- SETUP PATHS ---
ROOT_DIR = Path.cwd()
sys.path.insert(0, str(ROOT_DIR))

# Link to v3.6 History (Backup)
V36_ENGINES_ROOT = r"C:\MyBestOdds\jackpot_system_v3.6\engines"
if os.path.exists(V36_ENGINES_ROOT) and V36_ENGINES_ROOT not in sys.path:
    sys.path.insert(0, V36_ENGINES_ROOT)

# --- IMPORT THE NEW BRAIN ---
try:
    # This imports the Clean 80-line Brain you just saved
    from core.row_enricher_v3_7 import enrich_row_v3_7
except ImportError:
    print("⚠️ CRITICAL: row_enricher_v3_7.py is missing from /core/ folder!")
    sys.exit(1)

# Import Excel Formatter
try:
    import make_final_sheet
except ImportError:
    print("❌ make_final_sheet.py is missing.")
    sys.exit(1)

# Import Algo Engines (with safety)
try:
    from leftside_v3_6.cash3_engine_v3_6 import generate_cash3_candidates_for_draw
    from leftside_v3_6.cash4_engine_v3_6 import generate_cash4_candidates_for_draw
    from leftside_v3_6.daily_index_v3_6 import build_daily_index
except ImportError:
    def generate_cash3_candidates_for_draw(*args, **kwargs): return []
    def generate_cash4_candidates_for_draw(*args, **kwargs): return []
    def build_daily_index(*args, **kwargs): return {}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_official_odds(game_name: str) -> str:
    g = game_name.lower().replace(" ", "")
    if "cash3" in g: return "1 in 1,000"
    if "cash4" in g and "life" not in g: return "1 in 10,000"
    if "mega" in g: return "1 in 302,575,350"
    if "power" in g: return "1 in 292,201,338"
    if "life" in g: return "1 in 21,846,048"
    return ""

def is_garbage(val: str) -> bool:
    """Detects placeholders and scrubs them."""
    if not val or not str(val).strip(): return True
    trash = ["03-11-27-44-56", "05-12-33-48-61", "01-13-21-34-56", "000", "0000"]
    clean = str(val).split("|")[0].strip()
    return clean in trash

def load_history_safely(game_name: str):
    paths = [
        fr"C:\MyBestOdds\jackpot_system_v3\data\results\ga_results\{game_name.lower().replace(' ','')}_results.csv",
        fr"C:\MyBestOdds\shared_history\ga_results\{game_name.lower().replace(' ','')}_history.csv",
        fr"C:\MyBestOdds\jackpot_system_v3\data\results\jackpot_results\{game_name.replace(' ','')}.csv"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, dtype=str)
                df.columns = [c.lower().replace(" ","_") for c in df.columns]
                if "winning_numbers" in df.columns: df["digits"] = df["winning_numbers"]
                elif "result" in df.columns: df["digits"] = df["result"]
                return df
            except: continue
    return None

def get_clean_picks(subscriber, game):
    """Extracts MMFSN and SCRUBS dummy numbers."""
    picks = []
    try:
        mmfsn = subscriber.get("engine_profile", {}).get("mmfsn", {})
        target = None
        for k in mmfsn:
            if k.upper().replace(" ","") == game.upper().replace(" ",""): target = mmfsn[k]; break
        if target:
            if "values" in target:
                for x in target["values"]:
                    c = str(x).replace(",","").strip()
                    if not is_garbage(c): picks.append(c)
            elif "main" in target:
                mains = target.get("main", [])
                specs = target.get("mega_ball") or target.get("power_ball") or target.get("cash_ball") or []
                if mains:
                    m_str = "-".join([f"{int(x):02d}" for x in sorted(mains)])
                    for s in specs:
                        full = f"{m_str} | {int(s):02d}"
                        if not is_garbage(full): picks.append(full)
    except: pass
    return picks

# =============================================================================
# THE RUNNER
# =============================================================================

START_DATE = "2025-12-12"
END_DATE = "2025-12-31"
SUBSCRIBER_DIR = ROOT_DIR / "data" / "subscribers" / "BOOK3"
OUTPUT_DIR = ROOT_DIR / "DELIVERY" / f"BOOK3_{START_DATE}_to_{END_DATE}"

def main():
    print(f"🚀 STARTING MONOLITH BUILD (Using New Brain)")
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.glob("*"): 
            try: os.remove(f)
            except: pass
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    sub_files = list(SUBSCRIBER_DIR.glob("*.json"))
    games = ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]

    count = 0
    for sub_file in sub_files:
        sub_name = sub_file.stem
        print(f"🔹 Processing: {sub_name}")

        try:
            with open(sub_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            d0 = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
            d1 = datetime.datetime.strptime(END_DATE, "%Y-%m-%d").date()
            dates = [d0 + datetime.timedelta(days=x) for x in range((d1-d0).days + 1)]
            
            final_rows = []

            for d in dates:
                d_str = d.strftime("%Y-%m-%d")
                weekday = d.weekday()

                for game in games:
                    # --- 1. SCHEDULE CHECK ---
                    if "Mega" in game and weekday not in [1, 4]: continue
                    if "Power" in game and weekday not in [0, 2, 5]: continue
                    
                    candidates = []
                    
                    # --- 2. USER PICKS (CLEAN) ---
                    user_picks = get_clean_picks(config, game)
                    for p in user_picks:
                        instr = "Combo" if "Cash" in game and "Life" not in game else "Standard Ticket"
                        candidates.append({"number": p, "source": "PROFILE_MMFSN", "instr": instr})

                    # --- 3. SYSTEM PICKS ---
                    if "Cash" in game:
                        hist = load_history_safely(game)
                        if hist is not None:
                            try:
                                idx = build_daily_index(hist, game, d, "EVENING")
                                pool = hist["digits"].tail(50).tolist()
                                if "3" in game:
                                    res = generate_cash3_candidates_for_draw(hist, idx, pool, max_picks=2)
                                    sys = [x.number for x in res]
                                elif "4" in game and "Life" not in game:
                                    res = generate_cash4_candidates_for_draw(hist, idx, pool, max_picks=2)
                                    sys = [x.number for x in res]
                                for s in sys:
                                    if s not in [x['number'] for x in candidates]:
                                        candidates.append({"number": s, "source": "SYSTEM_ALGO", "instr": "Straight/Box"})
                            except: pass

                    # --- 4. ENRICHMENT (CALLING THE NEW BRAIN) ---
                    for cand in candidates:
                        row = {
                            "game": game, "game_code": game.upper().replace(" ",""),
                            "forecast_date": d_str, "number": cand["number"],
                            "play_flag": "WATCH", "confidence_score": 0.0,
                            "legend_text": cand["instr"], "play_type": cand["instr"],
                            "official_odds": get_official_odds(game),
                            "engine_source": cand["source"] # Needed for Brain Logic
                        }
                        
                        try:
                            # 🧠 PASSING BOTH ARGUMENTS HERE
                            enriched = enrich_row_v3_7(row, config)
                            
                            # Safety Check: If brain returns nothing (rare), force data
                            if not enriched.get("play_flag"): enriched["play_flag"] = "WATCH"
                            
                            final_rows.append(enriched)
                        except Exception as e:
                            # print(f"Brain Crash: {e}") # Debug only
                            row["confidence_score"] = 0.99
                            row["play_flag"] = "SYSTEM FAULT"
                            final_rows.append(row)

            # --- WRITE EXCEL ---
            if final_rows:
                clean_rows = []
                for r in final_rows:
                    game_disp = r.get("game", "Unknown")
                    if "Mega" in game_disp: game_disp = "Mega Millions"
                    elif "Power" in game_disp: game_disp = "Powerball"
                    elif "Cash3" in str(r.get("game_code")): game_disp = "Cash 3"
                    elif "Cash4" in str(r.get("game_code")) and "Life" not in game_disp: game_disp = "Cash 4"
                    
                    clean_rows.append({
                        "Date": r["forecast_date"],
                        "Game": game_disp,
                        "Best Odds Verdict (BOV)": r.get("play_flag", "WATCH"),
                        "Your Numbers": str(r["number"]).zfill(3 if "Cash 3" in game_disp else 4 if "Cash 4" in game_disp else 1),
                        "Play Instruction": r.get("legend_text", ""),
                        "Confidence Score (%)": f"{float(r.get('confidence_score', 0))*100:.1f}%",
                        "My Best Odds (1 in X)": r.get("mbo_odds_text", ""),
                        "Official Lottery Odds": r.get("official_odds", ""),
                        "North Node Insight": r.get("north_node_insight", "")
                    })
                
                df = pd.DataFrame(clean_rows)
                target = OUTPUT_DIR / f"{sub_name}_{START_DATE}_to_{END_DATE}.xlsx"
                make_final_sheet.format_excel(df, str(target))
                print(f"   ✅ SUCCESS: {target.name}")
                count += 1

        except Exception as e:
            print(f"   ❌ ERROR {sub_name}: {e}")

    print(f"\n🏁 JOB DONE. {count} Files Generated.")

if __name__ == "__main__":
    main()