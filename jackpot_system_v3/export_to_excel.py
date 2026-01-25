#!/usr/bin/env python3
"""
Convert High Confidence CSV to Excel Format
===========================================
Converts the high confidence predictions CSV into the format expected by
the final_kit_formatter_v3_7.py for Excel export.
"""

import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

# Project root setup
PROJECT_ROOT = Path(__file__).parent.absolute()

def convert_csv_to_formatter_json():
    """Convert CSV results to formatter-compatible JSON."""
    
    # Find the most recent high confidence CSV file
    csv_files = list(PROJECT_ROOT.glob("high_confidence_results_*.csv"))
    
    if not csv_files:
        print("❌ No high confidence CSV files found!")
        return None
        
    # Get the most recent file
    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Using CSV file: {latest_csv}")
    
    # Read the CSV data
    df = pd.read_csv(latest_csv)
    
    # Convert to formatter expected format
    formatter_data = []
    
    for _, row in df.iterrows():
        # Determine BOV based on confidence level
        confidence = float(row['confidence'])
        if confidence >= 0.85:
            bov = "GREEN"  # 85%+ = Strong Play
        elif confidence >= 0.80:
            bov = "YELLOW"  # 80-84% = Moderate Play  
        elif confidence >= 0.75:
            bov = "TAN"  # 75-79% = Caution Play
        else:
            bov = "RED"  # Below 75% = Avoid
        
        # Create North Node Insight based on game and confidence
        insights = {
            "Cash3": f"Mercury aligns with Venus - {row['confidence_percent']} cosmic confidence for quick cash manifestation.",
            "Cash4": f"Jupiter's blessing enhances four-digit energy - {row['confidence_percent']} stellar alignment detected.", 
            "Cash4Life": f"Saturn's life-path energy converges - {row['confidence_percent']} lifetime opportunity window.",
            "MegaMillions": f"Lunar nodes activate mega abundance - {row['confidence_percent']} jackpot potential unlocked.",
            "Powerball": f"Solar eclipse energy amplifies power - {row['confidence_percent']} transformative alignment."
        }
        
        formatter_row = {
            "date": row['date'],
            "draw_date": row['date'], 
            "game": row['game'],
            "number": row['numbers'],
            "numbers": row['numbers'],
            "play_type": "STRAIGHT",
            "confidence_score": confidence,  # For MBO calculation
            "confidence": confidence,  # For jackpot games
            "play_flag": bov,
            "north_node_insight": insights.get(row['game'], f"Cosmic alignment at {row['confidence_percent']} confidence."),
            "draw_time": "Evening" if row['game'] in ["Cash3", "Cash4"] else ""
        }
        
        formatter_data.append(formatter_row)
    
    # Save as JSON for formatter
    json_file = PROJECT_ROOT / "high_confidence_predictions_formatter.json"
    with open(json_file, 'w') as f:
        json.dump(formatter_data, f, indent=2)
    
    print(f"✅ Formatter JSON created: {json_file}")
    print(f"📊 Records converted: {len(formatter_data)}")
    
    return json_file

def create_excel_export():
    """Create the final Excel export using the formatter."""
    
    # Convert CSV to formatter JSON
    json_file = convert_csv_to_formatter_json()
    if not json_file:
        return
    
    # Set up output directory  
    output_dir = PROJECT_ROOT / "DELIVERY" / "HIGH_CONFIDENCE_2025-12-22"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Import and use the formatter
    sys_path = str(PROJECT_ROOT / "core" / "v3_7")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    
    from final_kit_formatter_v3_7 import export_final_kit
    
    # Generate Excel file
    subscriber_id = "HIGH_CONFIDENCE_PREDICTIONS"
    kit_type = "BOOK3_ANALYSIS"
    
    try:
        export_final_kit(
            forecast_json_path=str(json_file),
            output_dir=str(output_dir), 
            subscriber_id=subscriber_id,
            kit_type=kit_type
        )
        
        # Find the generated Excel file
        excel_files = list(output_dir.glob("*.xlsx"))
        if excel_files:
            excel_file = excel_files[0]
            print(f"🎉 Excel file created: {excel_file}")
            print(f"📊 High Confidence Predictions (75%+) formatted with:")
            print(f"   ✅ Color-coded Best Odds Verdict (BOV)")
            print(f"   ✅ My Best Odds (MBO) calculations")
            print(f"   ✅ North Node Insights") 
            print(f"   ✅ Professional styling and formatting")
        else:
            print("❌ Excel file not found after formatting")
            
    except Exception as e:
        print(f"❌ Error during Excel formatting: {e}")
        
        # Fallback: Create basic Excel file
        print("🔄 Creating basic Excel export...")
        create_basic_excel_export(output_dir)

def create_basic_excel_export(output_dir):
    """Create a basic Excel export if formatter fails."""
    
    # Find the CSV file
    csv_files = list(PROJECT_ROOT.glob("high_confidence_results_*.csv"))
    if not csv_files:
        return
        
    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
    df = pd.read_csv(latest_csv)
    
    # Basic Excel export with enhanced formatting
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = output_dir / f"HIGH_CONFIDENCE_PREDICTIONS_BASIC_{timestamp}.xlsx"
    
    # Create Excel with enhanced column names
    export_df = df.copy()
    export_df.columns = [
        'Subscriber', 'Date', 'Game', 'Numbers', 'Confidence (Decimal)',
        'Confidence (%)', 'My Best Odds', 'Source'
    ]
    
    # Add BOV column based on confidence
    def get_bov(confidence):
        if confidence >= 0.85:
            return "GREEN - Strong Play"
        elif confidence >= 0.80:
            return "YELLOW - Moderate Play"
        elif confidence >= 0.75:
            return "TAN - Caution Play"
        else:
            return "RED - Avoid"
    
    export_df['Best Odds Verdict (BOV)'] = export_df['Confidence (Decimal)'].apply(get_bov)
    
    # Reorder columns
    export_df = export_df[['Date', 'Game', 'Numbers', 'Confidence (%)', 'Best Odds Verdict (BOV)', 
                          'My Best Odds', 'Subscriber', 'Source']]
    
    export_df.to_excel(excel_file, index=False, sheet_name="High Confidence Predictions")
    print(f"📊 Basic Excel export created: {excel_file}")

if __name__ == "__main__":
    import sys
    
    print("🎯 MY BEST ODDS - HIGH CONFIDENCE EXCEL EXPORT")
    print("=" * 60)
    print("📅 Converting predictions to Excel format...")
    print()
    
    create_excel_export()
    
    print("\n" + "=" * 60) 
    print("✅ EXCEL EXPORT COMPLETE!")