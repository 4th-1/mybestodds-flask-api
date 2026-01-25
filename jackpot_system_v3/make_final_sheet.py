import sys
import json
import pandas as pd
from pathlib import Path

# ==========================================
# CONFIGURATION: OFFICIAL ODDS MAP
# ==========================================
OFFICIAL_ODDS_MAP = {
    "CASH3": "1 in 1,000",
    "CASH 3": "1 in 1,000",
    "C3": "1 in 1,000",
    "CASH4": "1 in 10,000",
    "CASH 4": "1 in 10,000",
    "C4": "1 in 10,000",
    "CASH4LIFE": "1 in 21,846,048",
    "C4L": "1 in 21,846,048",
    "MEGAMILLIONS": "1 in 302,575,350",
    "MM": "1 in 302,575,350",
    "POWERBALL": "1 in 292,201,338",
    "PB": "1 in 292,201,338",
}

# ==========================================
# COLUMN WIDTHS & STYLING
# ==========================================
COLUMN_WIDTHS = {
    "A:A": 12,  # Date
    "B:B": 15,  # Game
    "C:C": 22,  # BOV (Verdict)
    "D:D": 20,  # Your Numbers
    "E:E": 35,  # Play Instruction
    "F:F": 18,  # Confidence %
    "G:G": 20,  # My Best Odds
    "H:H": 22,  # Official Odds
    "I:I": 30   # North Node
}

def clean_game_name(g):
    g = str(g).upper().strip()
    if "CASH3" in g: return "Cash 3"
    if "CASH4" in g and "LIFE" not in g: return "Cash 4"
    if "MEGA" in g: return "Mega Millions"
    if "POWER" in g: return "Powerball"
    if "LIFE" in g: return "Cash4Life"
    return g.title()

def format_excel(df, output_path):
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='MyBestOdds Picks', index=False)
    
    workbook  = writer.book
    worksheet = writer.sheets['MyBestOdds Picks']

    # --- STYLES ---
    header_fmt = workbook.add_format({
        'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
        'fg_color': '#0F172A', 'font_color': '#FFFFFF', 'border': 1
    })
    
    center_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
    left_fmt   = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
    
    # Verdict Colors
    green_fmt  = workbook.add_format({'bg_color': '#DCFCE7', 'font_color': '#166534', 'align': 'center', 'bold': True}) # Strong Green
    yellow_fmt = workbook.add_format({'bg_color': '#FEF9C3', 'font_color': '#854D0E', 'align': 'center'}) # Play Yellow
    gray_fmt   = workbook.add_format({'bg_color': '#F3F4F6', 'font_color': '#9CA3AF', 'align': 'center'}) # Skip Gray

    # 1. Set Widths
    for col, width in COLUMN_WIDTHS.items():
        worksheet.set_column(col, width)

    # 2. Write Headers
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_fmt)

    # 3. Write Data
    for row_num in range(1, len(df) + 1):
        # Date & Game
        worksheet.write(row_num, 0, df.iloc[row_num-1]['Date'], center_fmt)
        worksheet.write(row_num, 1, df.iloc[row_num-1]['Game'], center_fmt)

        # BOV (Verdict) - Conditional Formatting
        bov = str(df.iloc[row_num-1]['Best Odds Verdict (BOV)']).upper()
        fmt = center_fmt
        if "STRONG" in bov or "GREEN" in bov: fmt = green_fmt
        elif "PLAY" in bov or "FUN" in bov: fmt = yellow_fmt
        elif "SKIP" in bov or "PASS" in bov: fmt = gray_fmt
        worksheet.write(row_num, 2, bov, fmt)

        # Your Numbers (String to keep "004")
        worksheet.write_string(row_num, 3, str(df.iloc[row_num-1]['Your Numbers']), center_fmt)

        # Instructions (Left aligned)
        worksheet.write(row_num, 4, df.iloc[row_num-1]['Play Instruction'], left_fmt)

        # Confidence %
        worksheet.write(row_num, 5, df.iloc[row_num-1]['Confidence Score (%)'], center_fmt)

        # Odds
        worksheet.write(row_num, 6, df.iloc[row_num-1]['My Best Odds (1 in X)'], center_fmt)
        worksheet.write(row_num, 7, df.iloc[row_num-1]['Official Lottery Odds'], center_fmt)
        
        # North Node
        worksheet.write(row_num, 8, df.iloc[row_num-1]['North Node Insight'], left_fmt)

    writer.close()
    print(f"✅ EXCEL GENERATED: {output_path}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python make_final_sheet.py <INPUT_JSON> <OUTPUT_XLSX>")
        return

    input_json = Path(sys.argv[1])
    output_xlsx = Path(sys.argv[2])

    print(f"Reading: {input_json}")
    try:
        with open(input_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    clean_rows = []
    
    for r in data:
        # --- LOGIC MAPPING ---
        
        # 1. Date
        date_val = r.get("forecast_date") or r.get("draw_date") or r.get("date") or ""
        
        # 2. Game
        raw_game = str(r.get("game", "")).upper()
        game_display = clean_game_name(raw_game)
        
        # 3. Verdict (BOV) - Map 'play_flag' or 'confidence_band' to human terms
        raw_flag = r.get("play_flag", "")
        raw_band = r.get("confidence_band", "")
        if "FUN" in raw_flag: verdict = "PLAY (FUN)"
        elif "GREEN" in raw_band: verdict = "STRONG PLAY"
        elif "YELLOW" in raw_band: verdict = "MODERATE"
        else: verdict = raw_band or "WATCH"

        # 4. Numbers (Handle Zeros)
        raw_num = str(r.get("number", "")).strip()
        # Ensure Cash 3 has 3 digits, Cash 4 has 4
        if "CASH3" in raw_game and raw_num: raw_num = raw_num.zfill(3)
        if "CASH4" in raw_game and "LIFE" not in raw_game and raw_num: raw_num = raw_num.zfill(4)

        # 5. Instructions
        instr = r.get("legend_text") or r.get("rubik_notes") or r.get("bob_note") or r.get("play_type") or ""
        
        # 6. Confidence %
        try:
            conf = float(r.get("confidence_score", 0))
            if conf < 1.0: conf = conf * 100
            conf_str = f"{conf:.1f}%"
        except:
            conf_str = ""

        # 7. MBO Odds
        mbo = r.get("mbo_odds_text") or r.get("best_odds_v36") or ""
        if isinstance(mbo, (int, float)): mbo = f"1 in {mbo}"

        # 8. Official Odds
        off_odds = OFFICIAL_ODDS_MAP.get(raw_game, "")
        if not off_odds:
            off_odds = OFFICIAL_ODDS_MAP.get(raw_game.replace(" ", ""), "")

        # 9. North Node
        nn = r.get("north_node_insight", "")

        clean_rows.append({
            "Date": date_val,
            "Game": game_display,
            "Best Odds Verdict (BOV)": verdict,
            "Your Numbers": raw_num,
            "Play Instruction": instr,
            "Confidence Score (%)": conf_str,
            "My Best Odds (1 in X)": mbo,
            "Official Lottery Odds": off_odds,
            "North Node Insight": nn
        })

    df = pd.DataFrame(clean_rows)
    format_excel(df, output_xlsx)

if __name__ == "__main__":
    main()