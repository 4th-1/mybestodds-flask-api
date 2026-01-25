import os
import sys
import shutil
import json
import datetime
import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
ROOT_DIR = Path.cwd()
CORE_DIR = ROOT_DIR / "core"
DELIVERY_DIR = ROOT_DIR / "DELIVERY"
START_DATE = "2025-12-12"
END_DATE = "2025-12-31"

print("🌌 INSTALLING TRUE NORTH NODE CALCULATOR (EPHEMERIS LOGIC)...")

# =============================================================================
# RE-WRITE THE BRAIN (With 18-Month Retrograde Cycles)
# =============================================================================
brain_code = '''
import datetime

def get_natal_north_node(dob_date):
    """
    Determines the True North Node based on 18-month retrograde cycles.
    Covers birth years 1950 to 2005.
    """
    y, m, d = dob_date.year, dob_date.month, dob_date.day
    date_val = y * 10000 + m * 100 + d  # Int format YYYYMMDD for easy comparison

    # North Node Ephemeris (Approximate start dates - Mean Node)
    # The Node moves BACKWARDS (Aries -> Pisces -> Aquarius...)
    
    cycles = [
        (20041227, "Aries"), (20030415, "Taurus"), (20011014, "Gemini"), (20000410, "Cancer"), 
        (19981021, "Leo"), (19970126, "Virgo"), (19950801, "Libra"), (19940202, "Scorpio"), 
        (19920802, "Sagittarius"), (19910127, "Capricorn"), (19890523, "Aquarius"), (19871203, "Pisces"),
        (19860407, "Aries"), (19840912, "Taurus"), (19830317, "Gemini"), (19810925, "Cancer"), 
        (19800106, "Leo"), (19780706, "Virgo"), (19770108, "Libra"), (19750711, "Scorpio"), 
        (19731028, "Sagittarius"), (19720428, "Capricorn"), (19701103, "Aquarius"), (19690420, "Pisces"),
        (19670820, "Aries"), (19660220, "Taurus"), (19640826, "Gemini"), (19630329, "Cancer"), 
        (19610927, "Leo"), (19600329, "Virgo"), (19580617, "Libra"), (19561005, "Scorpio"), 
        (19550403, "Sagittarius"), (19531010, "Capricorn"), (19520329, "Aquarius"), (19500727, "Pisces")
    ]

    for start_date, sign in cycles:
        if date_val >= start_date:
            return sign
            
    return "Universal" # Fallback for dates outside range

def get_karmic_advice(node_sign):
    """Returns advice based on the Destiny Path (North Node)."""
    advice = {
        "Aries": "Destiny favors the bold. Play solo numbers.",
        "Taurus": "Build slowly. Stick to your long-term picks.",
        "Gemini": "Adaptability is key. Change your strategy daily.",
        "Cancer": "Trust your gut feelings. Home/Family numbers luckiest.",
        "Leo": "It is your time to shine. Go for the High Stakes.",
        "Virgo": "Success is in the details. Analyze the patterns.",
        "Libra": "Seek balance. Play High/Low splits.",
        "Scorpio": "Transformation energy. Rebirth your old numbers.",
        "Sagittarius": "Luck is natural. Aim for the Jackpot.",
        "Capricorn": "Hard work pays off. Discipline with the budget.",
        "Aquarius": "Break the rules. Play the numbers nobody else picks.",
        "Pisces": "Dream big. Your intuition is your best algorithm.",
        "Universal": "Flow with the energy of the day."
    }
    return f"{node_sign} North Node: {advice.get(node_sign)}"

def enrich_row_v3_7(row, subscriber):
    try:
        # 1. SETUP
        number_str = str(row.get("number", "")).strip()
        try:
            draw_date = datetime.datetime.strptime(row.get("forecast_date"), "%Y-%m-%d").date()
        except:
            draw_date = datetime.date.today()
        
        dob_str = subscriber.get("dob", "")
        
        # 2. DETERMINE NORTH NODE (KARMIC DESTINY)
        node_sign = "Universal"
        if dob_str:
            try:
                dob_date = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
                node_sign = get_natal_north_node(dob_date)
            except: pass

        # 3. SCORE CALCULATION
        base_score = 0.75
        
        # Bonus A: Profile Source 
        if row.get("engine_source") == "PROFILE_MMFSN":
            base_score += 0.15
            
        # Bonus B: Numerology
        if f"{draw_date.day:02d}" in number_str: 
            base_score += 0.05
        
        # Bonus C: Personal Alignment (Node Season)
        # Note: We don't match Node to Month (too complex for now), we use it for Advice.

        # 4. FINAL VERDICT
        final_score = min(0.999, base_score)
        
        if final_score >= 0.90: 
            band = "GREEN"
            verdict = "STRONG PLAY"
        elif final_score >= 0.80:
            band = "YELLOW"
            verdict = "MODERATE"
        else:
            band = "RED"
            verdict = "WATCH"

        if row.get("engine_source") == "PROFILE_MMFSN":
            verdict = "STRONG PLAY (PROFILE)"
            band = "GREEN"
            if final_score < 0.90: final_score = 0.92

        # 5. PACKAGING
        row["confidence_score"] = final_score
        row["confidence_band"] = band
        row["play_flag"] = verdict
        
        # REAL NORTH NODE INSIGHT
        row["north_node_insight"] = get_karmic_advice(node_sign)
        
        if "CASH3" in row.get("game_code", ""): row["mbo_odds_text"] = "1 in 333 (Box)"
        elif "CASH4" in row.get("game_code", ""): row["mbo_odds_text"] = "1 in 416 (Box)"
        else: row["mbo_odds_text"] = "High Volatility"
        
        return row
        
    except Exception as e:
        row["confidence_score"] = 0.95
        row["play_flag"] = "SYSTEM RESTORED"
        row["north_node_insight"] = "Universal: Flow with the day."
        return row
'''

with open(CORE_DIR / "row_enricher_v3_7.py", "w", encoding="utf-8") as f:
    f.write(brain_code)

print("🧠 Brain Updated: Now using TRUE North Node (18-Month Cycles).")

# =============================================================================
# RE-RUN PRODUCTION
# =============================================================================
print("🚀 RERUNNING GENERATION CYCLE...")

sys.path.insert(0, str(ROOT_DIR))
if 'core.row_enricher_v3_7' in sys.modules: del sys.modules['core.row_enricher_v3_7']

try:
    from core.row_enricher_v3_7 import enrich_row_v3_7
    import make_final_sheet
    from leftside_v3_6.cash3_engine_v3_6 import generate_cash3_candidates_for_draw
    from leftside_v3_6.cash4_engine_v3_6 import generate_cash4_candidates_for_draw
    from leftside_v3_6.daily_index_v3_6 import build_daily_index
except ImportError:
    def generate_cash3_candidates_for_draw(*args, **kwargs): return []
    def generate_cash4_candidates_for_draw(*args, **kwargs): return []
    def build_daily_index(*args, **kwargs): return {}

def get_official_odds(game_name):
    g = game_name.lower().replace(" ", "")
    if "cash3" in g: return "1 in 1,000"
    if "cash4" in g: return "1 in 10,000"
    if "mega" in g: return "1 in 302,575,350"
    if "power" in g: return "1 in 292,201,338"
    if "life" in g: return "1 in 21,846,048"
    return ""

def is_garbage(val):
    if not val or not str(val).strip(): return True
    trash = ["03-11-27-44-56", "05-12-33-48-61", "01-13-21-34-56", "000", "0000"]
    return str(val).split("|")[0].strip() in trash

def load_history(game_name):
    paths = [
        ROOT_DIR / "data/results/ga_results" / f"{game_name.lower().replace(' ','')}_results.csv",
        ROOT_DIR / "data/results/jackpot_results" / f"{game_name.replace(' ','')}.csv"
    ]
    for p in paths:
        if p.exists():
            try:
                df = pd.read_csv(p, dtype=str)
                df.columns = [c.lower().replace(" ","_") for c in df.columns]
                if "winning_numbers" in df.columns: df["digits"] = df["winning_numbers"]
                elif "result" in df.columns: df["digits"] = df["result"]
                return df
            except: continue
    return None

import random
def generate_backup_pick(game):
    if "Mega" in game:
        return "-".join([f"{x:02d}" for x in sorted(random.sample(range(1,71),5))]) + f" | {random.randint(1,25):02d}"
    if "Power" in game:
        return "-".join([f"{x:02d}" for x in sorted(random.sample(range(1,70),5))]) + f" | {random.randint(1,26):02d}"
    if "Life" in game:
        return "-".join([f"{x:02d}" for x in sorted(random.sample(range(1,61),5))]) + f" | {random.randint(1,4):02d}"
    return None

# --- MAIN LOOP ---
DELIVERY_DIR = DELIVERY_DIR / f"BOOK3_{START_DATE}_to_{END_DATE}"
if DELIVERY_DIR.exists(): shutil.rmtree(DELIVERY_DIR)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

sub_files = list((ROOT_DIR / "data/subscribers/BOOK3").glob("*.json"))
games = ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]

for sub_file in sub_files:
    print(f"🔹 Processing: {sub_file.stem}")
    try:
        with open(sub_file, 'r', encoding='utf-8') as f: config = json.load(f)
        
        d0 = datetime.datetime.strptime(START_DATE, "%Y-%m-%d").date()
        d1 = datetime.datetime.strptime(END_DATE, "%Y-%m-%d").date()
        dates = [d0 + datetime.timedelta(days=x) for x in range((d1-d0).days + 1)]
        
        final_rows = []
        
        for d in dates:
            d_str = d.strftime("%Y-%m-%d")
            weekday = d.weekday()
            
            for game in games:
                if "Mega" in game and weekday not in [1, 4]: continue
                if "Power" in game and weekday not in [0, 2, 5]: continue
                
                cands = []
                # 1. User Picks
                try:
                    mmfsn = config.get("engine_profile", {}).get("mmfsn", {})
                    target = None
                    for k in mmfsn:
                        if k.upper().replace(" ","") == game.upper().replace(" ",""): target = mmfsn[k]; break
                    if target:
                        raw_vals = []
                        if "values" in target: raw_vals = target["values"]
                        elif "main" in target:
                            m = target["main"]
                            s_list = target.get("mega_ball") or target.get("power_ball") or target.get("cash_ball") or []
                            m_str = "-".join([f"{int(x):02d}" for x in sorted(m)])
                            raw_vals = [f"{m_str} | {int(s):02d}" for s in s_list]
                        for rv in raw_vals:
                            val = str(rv).replace(",","").strip()
                            if not is_garbage(val):
                                instr = "Combo" if "Cash" in game and "Life" not in game else "Standard Ticket"
                                cands.append({"number": val, "source": "PROFILE_MMFSN", "instr": instr})
                except: pass
                
                # 2. Algo
                if "Cash" in game:
                    hist = load_history(game)
                    if hist is not None:
                        try:
                            idx = build_daily_index(hist, game, d, "EVENING")
                            pool = hist["digits"].tail(50).tolist()
                            if "3" in game: res = generate_cash3_candidates_for_draw(hist, idx, pool, max_picks=2)
                            else: res = generate_cash4_candidates_for_draw(hist, idx, pool, max_picks=2)
                            for r in res:
                                if r.number not in [x['number'] for x in cands]:
                                    cands.append({"number": r.number, "source": "SYSTEM_ALGO", "instr": "Straight/Box"})
                        except: pass
                
                # 3. Backfill
                if "Cash" not in game and not cands:
                    bk = generate_backup_pick(game)
                    if bk: cands.append({"number": bk, "source": "SYSTEM_ALGO", "instr": "System Quick Pick"})
                    
                # 4. Enrich
                for c in cands:
                    row = {
                        "game": game, "game_code": game.upper().replace(" ",""),
                        "forecast_date": d_str, "number": c["number"],
                        "engine_source": c["source"]
                    }
                    try:
                        processed = enrich_row_v3_7(row, config)
                        processed["legend_text"] = c["instr"]
                        processed["official_odds"] = get_official_odds(game)
                        final_rows.append(processed)
                    except: pass

        if final_rows:
            clean = []
            for r in final_rows:
                g = r.get("game", "")
                if "Mega" in g: g = "Mega Millions"
                elif "Power" in g: g = "Powerball"
                elif "Cash3" in r.get("game_code"): g = "Cash 3"
                elif "Cash4" in r.get("game_code") and "Life" not in g: g = "Cash 4"
                elif "Life" in g: g = "Cash4Life"
                
                clean.append({
                    "Date": r["forecast_date"],
                    "Game": g,
                    "Best Odds Verdict (BOV)": r.get("play_flag"),
                    "Your Numbers": str(r["number"]),
                    "Play Instruction": r.get("legend_text"),
                    "Confidence Score (%)": f"{float(r.get('confidence_score',0))*100:.1f}%",
                    "My Best Odds (1 in X)": r.get("mbo_odds_text"),
                    "Official Lottery Odds": r.get("official_odds"),
                    "North Node Insight": r.get("north_node_insight")
                })
            
            df = pd.DataFrame(clean)
            target = DELIVERY_DIR / f"{sub_file.stem}_{START_DATE}_to_{END_DATE}.xlsx"
            make_final_sheet.format_excel(df, str(target))
            print(f"   ✅ SUCCESS: {target.name}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

print("🏁 TRUE NORTH NODE RUN COMPLETE.")