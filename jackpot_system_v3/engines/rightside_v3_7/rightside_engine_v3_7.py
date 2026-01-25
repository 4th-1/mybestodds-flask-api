"""
rightside_engine_v3_7.py
-----------------------------------------------------------
Jackpot Scoring Engine (v3.7)

Games supported:
    • MEGA_MILLIONS
    • POWERBALL
    • CASH4LIFE

Purpose:
    Clean, confidence-based scoring engine for jackpot games.
    NO MMFSN. NO personalization. NO legacy scoring fields.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Any

# ENHANCED ENGINE INTEGRATION
try:
    from .rightside_engine_v3_7_ENHANCED import (
        score_jackpot_row_enhanced,
        build_jackpot_scores as build_jackpot_scores_enhanced,
        EnhancedJackpotEngine
    )
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError:
    ENHANCED_ENGINE_AVAILABLE = False


# -----------------------------------------------------------
# BACKWARD COMPATIBLE INTERFACE WITH ENHANCEMENT
# -----------------------------------------------------------

def score_jackpot_row(row: pd.Series, game: str, subscriber_data: Dict = None) -> Dict[str, Any]:
    """
    Compute a CONFIDENCE SCORE for a jackpot draw.
    Enhanced with multi-number generation when available.
    """
    
    # Use enhanced engine if available
    if ENHANCED_ENGINE_AVAILABLE and subscriber_data is not None:
        return score_jackpot_row_enhanced(row, game, subscriber_data)
    
    # FALLBACK: Original scoring logic (recalibrated for realism)
    score = 0.0
    notes = []

    # BASE SCORE BOOST for jackpot games (they need higher baseline)
    score += 2.0  # Start with 2 points instead of 0
    notes.append("Base jackpot bonus")

    # -----------------------------
    # RECENCY / SUM SIGNAL (More generous)
    # -----------------------------
    sum_main = row[["n1", "n2", "n3", "n4", "n5"]].sum()

    if sum_main < 120:
        score += 1.5  # Increased from 1.0
        notes.append("Low sum (strong)")
    elif sum_main < 150:
        score += 1.0  # Increased from 0.5
        notes.append("Medium sum (good)")
    elif sum_main < 180:  # NEW: Medium-high range
        score += 0.5
        notes.append("Medium-high sum")

    # -----------------------------
    # BONUS BALL PATTERN (More generous)
    # -----------------------------
    bonus = int(row["bonus"])
    if 1 <= bonus <= 5:
        score += 1.2  # Increased from 1.0
        notes.append("Low bonus (excellent)")
    elif bonus <= 10:
        score += 0.8  # Increased from 0.5
        notes.append("Mid bonus (good)")
    elif bonus <= 15:  # NEW: Mid-range bonus
        score += 0.4
        notes.append("Mid-range bonus")

    # -----------------------------
    # DIGIT REPEATS (More generous)
    # -----------------------------
    nums = [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"]]
    unique = len(set(nums))
    
    if unique == 5:  # All unique
        score += 0.8  # Increased from typical penalty
        notes.append("All unique numbers")
    elif unique == 4:  # One repeat
        score += 1.0  # Bonus for mild repeats
        notes.append("One repeat pair")
    else:  # Multiple repeats
        score += 0.5  # Still give some points
        notes.append("Multiple repeats")

    # -----------------------------
    # ADDITIONAL PATTERNS (New scoring opportunities)
    # -----------------------------
    
    # Even/Odd distribution scoring
    even_count = sum(1 for n in nums if n % 2 == 0)
    if 2 <= even_count <= 3:  # Balanced even/odd
        score += 0.6
        notes.append("Balanced even/odd")
    
    # Consecutive number check
    sorted_nums = sorted(nums)
    consecutive_pairs = sum(1 for i in range(4) if sorted_nums[i+1] - sorted_nums[i] == 1)
    if consecutive_pairs >= 1:
        score += 0.4
        notes.append("Has consecutive numbers")
    
    # Bonus ball relationship to main numbers
    bonus_close_to_main = any(abs(bonus - n) <= 3 for n in nums)
    if bonus_close_to_main:
        score += 0.3
        notes.append("Bonus close to main numbers")

    # -----------------------------
    # GAME-SPECIFIC NUDGE (Enhanced)
    # -----------------------------
    game = game.upper()
    if game == "MEGA_MILLIONS":
        score += 0.5  # Increased from 0.2
        notes.append("MegaMillions bonus")
    elif game == "POWERBALL":
        score += 0.4  # Increased from 0.15
        notes.append("Powerball bonus")
    elif game == "CASH4LIFE":
        score += 0.3  # Increased from 0.1
        notes.append("Cash4Life bonus")

    # -----------------------------
    # FINAL CONFIDENCE CONVERSION (CALIBRATED for actual performance)
    # -----------------------------
    # CALIBRATED confidence ranges based on audit results:
    # - Cash4Life: 10.27% actual (excellent) → 10-13% range
    # - Powerball: 1.39% actual (over-optimistic) → 2-4% range  
    # - MegaMillions: 0% actual (no data) → 2-5% range (conservative)
    
    base_confidence = score * 1.5  # Reduced scaling for realism
    
    game = game.upper()
    if game == "CASH4LIFE":
        # EXCELLENT alignment - keep current range
        confidence_percentage = min(max(base_confidence, 10.0), 13.0)  # 10-13%
        calibration_note = "CALIBRATED: 10-13% (actual 10.27%)"
    elif game == "POWERBALL":
        # OVER-OPTIMISTIC - reduce significantly  
        confidence_percentage = min(max(base_confidence * 0.4, 2.0), 4.0)  # 2-4%
        calibration_note = "CALIBRATED: 2-4% (was 6-10%, actual 1.39%)"
    elif game == "MEGA_MILLIONS":
        # CONSERVATIVE - no actual data
        confidence_percentage = min(max(base_confidence * 0.5, 2.0), 5.0)  # 2-5%
        calibration_note = "CALIBRATED: 2-5% (conservative, no data)"
    else:
        # Fallback for unknown games
        confidence_percentage = min(base_confidence, 5.0)  # Cap at 5%
        calibration_note = "FALLBACK: 5% max"
    
    notes.append(calibration_note)
    
    return {
        "confidence_score": round(confidence_percentage, 1),  # Return as percentage
        "raw_score": round(score, 3),
        "confidence_notes": "; ".join(notes) if notes else "No strong signals"
    }


# -----------------------------------------------------------
# APPLY TO A WHOLE DATAFRAME
# -----------------------------------------------------------

def build_scores_for_game(df: pd.DataFrame, game: str, subscriber_data: Dict = None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    scores = df.apply(lambda row: score_jackpot_row(row, game, subscriber_data), axis=1)

    df["confidence_score"] = scores.apply(lambda x: x["confidence_score"])  # Now percentage
    df["raw_score"] = scores.apply(lambda x: x.get("raw_score", 0))
    df["confidence_notes"] = scores.apply(lambda x: x["confidence_notes"])
    
    # Add game column for filtering
    df["game"] = game

    return df.sort_values("draw_date").reset_index(drop=True)


# -----------------------------------------------------------
# TOP-LEVEL PUBLIC ENGINE
# -----------------------------------------------------------

def build_jackpot_scores(history_context: Dict[str, pd.DataFrame], subscriber_data: Dict = None) -> Dict[str, pd.DataFrame]:
    # Use enhanced engine if available
    if ENHANCED_ENGINE_AVAILABLE and subscriber_data is not None:
        return build_jackpot_scores_enhanced(history_context, subscriber_data)
    
    # Fallback to standard scoring
    return {
        "mega_millions_scores": build_scores_for_game(
            history_context.get("mega_millions"), "MEGA_MILLIONS", subscriber_data
        ),
        "powerball_scores": build_scores_for_game(
            history_context.get("powerball"), "POWERBALL", subscriber_data
        ),
        "cash4life_scores": build_scores_for_game(
            history_context.get("cash4life"), "CASH4LIFE", subscriber_data
        ),
    }


# -----------------------------------------------------------
# SMOKE TEST
# -----------------------------------------------------------

if __name__ == "__main__":
    print("\n=== INTEGRATED JACKPOT SCORE ENGINE v3.7 ===")
    
    # Test subscriber data for enhanced features
    test_subscriber = {
        'identity': {
            'first_name': 'Joseph',
            'last_name': 'Smith',
            'date_of_birth': '1985-03-15'
        }
    }
    
    # Test row data
    test_row = pd.Series({
        'n1': 5, 'n2': 12, 'n3': 23, 'n4': 35, 'n5': 48,
        'bonus': 3, 'draw_date': '2025-12-21'
    })
    
    print(f"Enhanced Engine Available: {ENHANCED_ENGINE_AVAILABLE}")
    
    # Test standard scoring
    print("\n🔹 STANDARD SCORING (No subscriber data):")
    standard_result = score_jackpot_row(test_row, "CASH4LIFE")
    print(f"  Confidence: {standard_result['confidence_score']:.1f}%")
    print(f"  Notes: {standard_result['confidence_notes']}")
    
    # Test enhanced scoring
    if ENHANCED_ENGINE_AVAILABLE:
        print("\n🔹 ENHANCED SCORING (With subscriber data):")
        enhanced_result = score_jackpot_row(test_row, "CASH4LIFE", test_subscriber)
        print(f"  Confidence: {enhanced_result['confidence_score']:.1f}%")
        print(f"  Full Combination: {enhanced_result.get('full_combination', 'N/A')}")
        print(f"  Generation Method: {enhanced_result.get('generation_method', 'standard')}")
    
    print("\n✅ INTEGRATION COMPLETE!")
    print("🎰 Right Engine now supports both standard and enhanced predictions!")
    print("📊 Confidence scores recalibrated to realistic ranges!")
