#!/usr/bin/env python3
"""
final_book3_summary.py

Summary report for all 14 BOOK3 subscribers with their processing status
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Mapping of subscriber codes to names based on JSON files
SUBSCRIBER_MAPPING = {
    "JHD": "John HF Douglas (JHD_BOOK3.json)",
    "AA": "Alisha Asha (AA_BOOK3.json)",
    "JDR": "Jimmy Deshawn Roberts (JDR_BOOK3.json)", 
    "BO": "Bakiea Owens (BO_BOOK3.json)",
    "VAL": "Valencia Allen-Love (VAL_BOOK3.json)",
    "MT": "Martin Taylor (MT_BOOK3.json)",
    "CP": "Corey Patterson (CP_BOOK3.json)",
    "TN": "Tad Newton (TN_BOOK3.json)",
    "YTL": "Yadonnis Tucker Lee (YTL_BOOK3.json)",
    "JDSII": "Joseph David Smith II (JDSII_BOOK3.json)",
    "JDS": "Joseph D Smith (JDS_BOOK3.json)",
    "AJS": "Adonna Janay Smith (AJS_BOOK3.json)",
    "YRS": "Yolanda Renee Smith (YRS_BOOK3.json)",
    "CW": "Consuela Ward (CW_BOOK3.json)",
}

# Alternative codes that might be used in output directories
ALTERNATIVE_CODES = {
    "JD": "JHD",  # John HF Douglas might be coded as JD
    "AS": "AJS",  # Adonna Janay Smith might be coded as AS  
    "JS": "JDS",  # Joseph D Smith might be coded as JS
    "VA": "VAL",  # Valencia might be coded as VA
    "YL": "YTL",  # Yadonnis Tucker Lee might be coded as YL
    "YS": "YRS",  # Yolanda Renee Smith might be coded as YS
    "JR": "JDR",  # Jimmy Deshawn Roberts might be coded as JR
}

def main():
    print("📋 BOOK3 SUBSCRIBER PROCESSING SUMMARY")
    print("=" * 60)
    print("Coverage Period: December 22-31, 2025")
    print("Total Subscribers: 14")
    print()
    
    # Find all December directories
    december_dirs = {}
    if OUTPUTS_DIR.exists():
        for d in OUTPUTS_DIR.iterdir():
            if (d.is_dir() and 
                d.name.startswith("BOOK3_") and 
                "2025-12-22_to_2025-12-31" in d.name):
                # Extract code
                parts = d.name.split("_")
                if len(parts) >= 2:
                    code = parts[1]
                    december_dirs[code] = d
    
    print(f"🔍 Found {len(december_dirs)} processed directories:")
    for code in sorted(december_dirs.keys()):
        print(f"  ✅ {code}: {december_dirs[code].name}")
    
    print()
    
    # Check status for each expected subscriber
    processed_subscribers = []
    missing_subscribers = []
    
    for expected_code, subscriber_name in SUBSCRIBER_MAPPING.items():
        found = False
        actual_code = None
        
        # Check direct match
        if expected_code in december_dirs:
            found = True
            actual_code = expected_code
        else:
            # Check alternative codes
            for alt_code, mapped_code in ALTERNATIVE_CODES.items():
                if mapped_code == expected_code and alt_code in december_dirs:
                    found = True
                    actual_code = alt_code
                    break
        
        if found:
            # Check if Excel file exists
            excel_file = december_dirs[actual_code] / f"{december_dirs[actual_code].name}.xlsx"
            excel_status = "✅" if excel_file.exists() else "❌"
            processed_subscribers.append((expected_code, actual_code, subscriber_name, excel_status))
        else:
            missing_subscribers.append((expected_code, subscriber_name))
    
    print("📊 INDIVIDUAL SUBSCRIBER STATUS:")
    print("-" * 60)
    
    for expected_code, actual_code, name, excel_status in processed_subscribers:
        display_code = f"{expected_code}" if expected_code == actual_code else f"{expected_code}→{actual_code}"
        print(f"  ✅ {display_code:<8} {name:<40} Excel: {excel_status}")
    
    for expected_code, name in missing_subscribers:
        print(f"  ❌ {expected_code:<8} {name:<40} Missing")
    
    print()
    print("🎯 FINAL STATISTICS:")
    print(f"  Processed: {len(processed_subscribers)}/14")
    print(f"  Missing: {len(missing_subscribers)}/14")
    excel_count = sum(1 for _, _, _, excel in processed_subscribers if excel == "✅")
    print(f"  Excel files: {excel_count}/{len(processed_subscribers)}")
    
    if len(processed_subscribers) == 14 and excel_count == 14:
        print("\\n🎉 SUCCESS: All 14 BOOK3 subscribers processed with Excel files!")
        print("   📅 Coverage: December 22-31, 2025")
        print("   📂 Location: outputs/BOOK3_*_2025-12-22_to_2025-12-31/")
        print("   📈 Ready for delivery!")
    elif len(missing_subscribers) > 0:
        print(f"\\n⚠️  {len(missing_subscribers)} subscribers still need processing:")
        for code, name in missing_subscribers:
            print(f"     {code}: {name}")
    elif excel_count < len(processed_subscribers):
        print(f"\\n⚠️  {len(processed_subscribers) - excel_count} Excel files missing")
    
    print("\\n📁 All output files are located in:")
    print("   c:\\MyBestOdds\\jackpot_system_v3\\outputs\\")

if __name__ == "__main__":
    main()