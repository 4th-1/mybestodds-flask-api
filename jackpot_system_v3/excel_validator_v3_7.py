#!/usr/bin/env python3
"""
Excel Output Validator v3.7
===========================

Validates Excel files to ensure:
1. Confidence scores are properly displayed (not all 15%)
2. BOV colors are correctly assigned
3. Data shows proper variance between subscribers  
4. No hardcoded identical values

Created: December 22, 2025
Purpose: Prevent Excel formatting issues
"""

import pandas as pd
from pathlib import Path
import json
from typing import List, Dict, Any


def validate_excel_output(excel_file: Path) -> Dict[str, Any]:
    """Validate an Excel file for common issues"""
    
    issues = []
    warnings = []
    
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)
        
        # Check 1: Confidence score variance
        if 'Cash Confidence Score (%)' in df.columns:
            conf_scores = df['Cash Confidence Score (%)'].dropna()
            unique_scores = conf_scores.nunique()
            
            if unique_scores <= 1:
                issues.append("All confidence scores are identical")
            elif unique_scores <= 3:
                warnings.append(f"Only {unique_scores} unique confidence scores")
        
        # Check 2: BOV color distribution
        if 'Best Odds Verdict (BOV)' in df.columns:
            bov_counts = df['Best Odds Verdict (BOV)'].value_counts()
            
            if len(bov_counts) <= 1:
                issues.append("All BOV colors are identical")
            
            if bov_counts.get('GREEN', 0) == 0 and any(df.columns.str.contains('Confidence')):
                warnings.append("No GREEN BOV classifications found")
        
        # Check 3: Unrealistic confidence values
        for col in df.columns:
            if 'confidence' in col.lower() and 'score' in col.lower():
                low_conf = (df[col] < 20).sum()
                if low_conf > len(df) * 0.8:  # 80% below 20%
                    issues.append(f"Most confidence scores suspiciously low ({col})")
        
        # Check 4: My Best Odds uniformity
        if 'My Best Odds (MBO)' in df.columns:
            mbo_unique = df['My Best Odds (MBO)'].nunique()
            if mbo_unique <= 1:
                issues.append("All MBO values are identical")
        
        validation_result = {
            "file": str(excel_file),
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "warnings": warnings,
            "total_rows": len(df),
            "unique_confidence_scores": conf_scores.nunique() if 'Cash Confidence Score (%)' in df.columns else 0
        }
        
        return validation_result
        
    except Exception as e:
        return {
            "file": str(excel_file),
            "status": "ERROR", 
            "issues": [f"Could not read file: {e}"],
            "warnings": [],
            "total_rows": 0,
            "unique_confidence_scores": 0
        }


def validate_all_book3_files() -> List[Dict[str, Any]]:
    """Validate all BOOK3 Excel files"""
    
    outputs_dir = Path(__file__).parent / "outputs"
    book3_dirs = list(outputs_dir.glob("BOOK3_*_2025-12-22_to_2025-12-31"))
    
    results = []
    
    for book3_dir in book3_dirs:
        excel_file = book3_dir / f"{book3_dir.name}.xlsx"
        if excel_file.exists():
            result = validate_excel_output(excel_file)
            results.append(result)
    
    return results


if __name__ == "__main__":
    print("🔍 EXCEL OUTPUT VALIDATION")
    print("=" * 40)
    
    results = validate_all_book3_files()
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL") 
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"📊 VALIDATION RESULTS:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️  Errors: {errors}")
    
    for result in results:
        if result["status"] != "PASS":
            print(f"\n❌ {result['file']}:")
            for issue in result["issues"]:
                print(f"   • {issue}")
            for warning in result["warnings"]:
                print(f"   ⚠️  {warning}")
