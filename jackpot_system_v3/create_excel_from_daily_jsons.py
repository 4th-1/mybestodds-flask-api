#!/usr/bin/env python3
"""
create_excel_from_daily_jsons.py

Consolidate daily JSON files into Excel format for BOOK3 subscribers
Converts the daily JSON files (2025-12-22.json, etc.) into the format expected by make_final_sheet.py
"""

import json
import pandas as pd
from pathlib import Path
import sys

def load_daily_predictions(output_dir):
    """Load all daily prediction JSON files from a subscriber output directory."""
    output_path = Path(output_dir)
    all_predictions = []
    
    # Find all daily JSON files (2025-12-22.json pattern)
    for json_file in sorted(output_path.glob("2025-*.json")):
        print(f"Loading {json_file.name}...")
        
        try:
            with open(json_file, 'r') as f:
                daily_data = json.load(f)
            
            # Extract picks for each game
            date = daily_data.get('date', json_file.stem)
            picks = daily_data.get('picks', {})
            
            for game, game_picks in picks.items():
                # Get lanes for this game
                lane_system = game_picks.get('lane_system', [])
                lane_mmfsn = game_picks.get('lane_mmfsn', [])
                
                # Combine all picks for this game
                all_picks = lane_system + lane_mmfsn
                
                for pick in all_picks:
                    prediction = {
                        'forecast_date': date,
                        'game': game,
                        'prediction': pick,
                        'confidence': 0.15,  # Default confidence
                        'verdict': 'GREEN',  # Default verdict
                        'play_instruction': 'STRAIGHT',
                        'my_odds': '1 in 500',
                        'north_node': 'Favorable'
                    }
                    all_predictions.append(prediction)
                    
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue
    
    return all_predictions

def create_excel_from_predictions(predictions, excel_output_path):
    """Create Excel file from consolidated predictions using make_final_sheet logic."""
    
    # Convert to the format expected by make_final_sheet.py
    formatted_data = []
    
    for pred in predictions:
        # Extract core fields
        date_val = pred.get("forecast_date", "")
        game = pred.get("game", "").upper()
        
        # Clean game name
        if "CASH3" in game:
            clean_game = "Cash 3"
        elif "CASH4" in game and "LIFE" not in game:
            clean_game = "Cash 4"  
        elif "LIFE" in game:
            clean_game = "Cash4Life"
        elif "MEGA" in game:
            clean_game = "Mega Millions"
        elif "POWER" in game:
            clean_game = "Powerball"
        else:
            clean_game = game.title()
        
        # Get prediction numbers
        numbers = pred.get("prediction", pred.get("numbers", ""))
        
        # Get confidence
        confidence = pred.get("confidence", 0)
        if isinstance(confidence, (int, float)):
            confidence_str = f"{confidence:.1%}"
        else:
            confidence_str = str(confidence)
        
        # Get verdict/BOV
        verdict = pred.get("verdict", pred.get("final_verdict", ""))
        
        # Get play instruction
        play_instruction = pred.get("play_instruction", pred.get("rubik_classification", ""))
        
        # Get my odds
        my_odds = pred.get("my_odds", pred.get("odds", ""))
        
        # Get official odds
        official_odds_map = {
            "CASH3": "1 in 1,000",
            "CASH 3": "1 in 1,000",
            "CASH4": "1 in 10,000", 
            "CASH 4": "1 in 10,000",
            "CASH4LIFE": "1 in 21,846,048",
            "MEGAMILLIONS": "1 in 302,575,350",
            "POWERBALL": "1 in 292,201,338",
        }
        official_odds = official_odds_map.get(game, "")
        
        # North Node (astronomical overlay info)
        north_node = pred.get("north_node", pred.get("astro_summary", ""))
        
        formatted_row = {
            "Date": date_val,
            "Game": clean_game,
            "BOV": verdict,
            "Your Numbers": str(numbers),
            "Play Instruction": play_instruction,
            "Confidence %": confidence_str,
            "My Best Odds": str(my_odds),
            "Official Odds": official_odds,
            "North Node": str(north_node)
        }
        
        formatted_data.append(formatted_row)
    
    # Create DataFrame and Excel file
    df = pd.DataFrame(formatted_data)
    
    # Create Excel with formatting
    with pd.ExcelWriter(excel_output_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='MyBestOdds Picks', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['MyBestOdds Picks']
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1
        })
        
        # Set column widths
        column_widths = [12, 15, 22, 20, 35, 18, 20, 22, 30]
        for i, width in enumerate(column_widths):
            worksheet.set_column(i, i, width)
        
        # Apply header format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Apply cell format to data
        for row in range(1, len(df) + 1):
            for col in range(len(df.columns)):
                worksheet.write(row, col, df.iloc[row-1, col], cell_format)
    
    print(f"Success! Excel file created: {excel_output_path}")
    print(f"Total predictions: {len(formatted_data)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python create_excel_from_daily_jsons.py <OUTPUT_DIRECTORY>")
        print("Example: python create_excel_from_daily_jsons.py outputs/BOOK3_AA_2025-12-22_to_2025-12-31")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"Error: Directory {output_dir} not found")
        sys.exit(1)
    
    # Load all daily predictions
    print(f"Processing {output_dir}...")
    predictions = load_daily_predictions(output_dir)
    
    if not predictions:
        print("No predictions found!")
        sys.exit(1)
    
    # Create Excel file
    excel_filename = f"{output_path.name}.xlsx"
    excel_path = output_path / excel_filename
    
    create_excel_from_predictions(predictions, excel_path)
    
    print(f"Done! Excel file available at: {excel_path}")

if __name__ == "__main__":
    main()