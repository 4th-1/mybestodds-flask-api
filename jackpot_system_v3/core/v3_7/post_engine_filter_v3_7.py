"""
post_engine_filter_v3_7.py
Post-Engine Selectivity & Quality Control Filter

Purpose:
- Apply selectivity logic to achieve ~20-30% silence periods
- Filter out low-quality predictions based on confidence thresholds
- Detect winner environments and bias toward favorable conditions
- Maintain quality control without changing core prediction engine

Key Functions:
- apply_selectivity_filter(): Main filtering logic
- detect_winner_environment(): Environment analysis
- calculate_silence_score(): Quality scoring for silence decisions
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import numpy as np


# --------------------------------------------------------------------------
# Configuration Constants
# --------------------------------------------------------------------------

DEFAULT_SILENCE_THRESHOLD = 0.65  # Confidence threshold for silence
DEFAULT_SILENCE_RATE_TARGET = 0.25  # Target 25% silence rate for Cash games
MIN_CONFIDENCE_FOR_PLAY = 45.0  # Minimum confidence for Cash games
WINNER_ENVIRONMENT_BOOST = 0.10  # Boost for favorable winner environments

# Game-specific configurations for different play patterns
GAME_SPECIFIC_CONFIG = {
    "Cash3": {
        "min_confidence": 35.0,  # Lowered from 45 for more plays
        "target_silence_rate": 0.25,  # 25% silence
        "confidence_boost": 0.0
    },
    "Cash4": {
        "min_confidence": 35.0,  # Lowered from 45 for more plays  
        "target_silence_rate": 0.25,  # 25% silence
        "confidence_boost": 0.0
    },
    "MegaMillions": {
        "min_confidence": 15.0,  # Much lower for jackpots (was 45!)
        "target_silence_rate": 0.70,  # 70% silence (very selective)
        "confidence_boost": 0.20  # Boost scores to compensate for low baseline
    },
    "Powerball": {
        "min_confidence": 15.0,  # Much lower for jackpots (was 45!)
        "target_silence_rate": 0.70,  # 70% silence (very selective)
        "confidence_boost": 0.20  # Boost scores to compensate
    },
    "Cash4Life": {
        "min_confidence": 18.0,  # Slightly higher than other jackpots
        "target_silence_rate": 0.65,  # 65% silence 
        "confidence_boost": 0.15  # Moderate boost
    }
}


def get_game_config(game_name: str) -> Dict[str, Any]:
    """Get game-specific configuration, with fallback to defaults."""
    return GAME_SPECIFIC_CONFIG.get(game_name, {
        "min_confidence": MIN_CONFIDENCE_FOR_PLAY,
        "target_silence_rate": DEFAULT_SILENCE_RATE_TARGET,
        "confidence_boost": 0.0
    })


# --------------------------------------------------------------------------
# Core Selectivity Logic
# --------------------------------------------------------------------------

def apply_selectivity_filter(
    df: pd.DataFrame,
    silence_threshold: float = DEFAULT_SILENCE_THRESHOLD,
    target_silence_rate: float = DEFAULT_SILENCE_RATE_TARGET
) -> pd.DataFrame:
    """
    Apply post-engine selectivity filtering to achieve target silence rate.
    Now uses game-specific configurations for different play patterns.
    
    Args:
        df: DataFrame with scored predictions
        silence_threshold: Confidence threshold below which to consider silence (deprecated)
        target_silence_rate: Global target percentage (overridden by game-specific config)
    
    Returns:
        DataFrame with play_flag column added (True/False for play/silence)
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Detect primary game type for configuration
    if 'game' in df.columns and not df['game'].empty:
        primary_game = df['game'].mode().iloc[0] if not df['game'].mode().empty else "Cash3"
    else:
        primary_game = "Cash3"  # Default fallback
    
    game_config = get_game_config(primary_game)
    actual_target_silence_rate = game_config["target_silence_rate"]
    min_confidence = game_config["min_confidence"]
    confidence_boost = game_config["confidence_boost"]
    
    print(f"[FILTER] Game: {primary_game}, Target silence: {actual_target_silence_rate:.1%}, Min conf: {min_confidence}")
    
    # Apply game-specific confidence boost for jackpot games
    if confidence_boost > 0:
        df["confidence_score"] = df.get("confidence_score", 0) + (confidence_boost * 100)  # Convert to percentage
    
    # Calculate silence scores for each prediction
    df["silence_score"] = df.apply(lambda row: calculate_silence_score(row), axis=1)
    
    # Detect winner environments
    df["winner_environment"] = df.apply(lambda row: detect_winner_environment(row), axis=1)
    
    # Apply winner environment boost
    df.loc[df["winner_environment"] == "favorable", "silence_score"] += WINNER_ENVIRONMENT_BOOST
    
    # Use game-specific target silence rate
    df_sorted = df.sort_values('silence_score', ascending=False)
    play_count = int(len(df) * (1 - actual_target_silence_rate))  # Number to keep playing
    
    # Initialize all as silenced, then mark top scorers to play
    df["play_flag"] = False
    if play_count > 0:
        top_indices = df_sorted.head(play_count).index
        df.loc[top_indices, "play_flag"] = True
    
    # Apply game-specific minimum confidence floor
    current_silence_count = (df["play_flag"] == False).sum()
    if current_silence_count < len(df) * actual_target_silence_rate:
        # We have room to silence more low confidence predictions
        df.loc[df["confidence_score"] < min_confidence, "play_flag"] = False
    
    # Add silence reason for tracking
    df["silence_reason"] = df.apply(lambda row: _determine_silence_reason(row, min_confidence), axis=1)
    
    return df


def calculate_silence_score(row: pd.Series) -> float:
    """
    Calculate a composite score to determine if prediction should be silenced.
    Higher score = more likely to play (less likely to silence).
    
    Returns: Score in [0.0, 1.0] range
    """
    score = 0.0
    
    # Base score from confidence (maximum generous + boost for low conf)
    confidence = float(row.get("confidence_score", 0))
    conf_score = confidence / 100.0
    
    # Boost lower confidence scores to reduce silence rate
    if confidence < 40:
        conf_score *= 1.5  # 50% boost for low confidence
    elif confidence < 60:
        conf_score *= 1.2  # 20% boost for medium confidence
    
    score += min(conf_score, 0.9)  # Max 90% from confidence
    
    # Signal strength indicators (minimal but present)
    if row.get("delta_high_flag", False):
        score += 0.02
    if row.get("markov_advantaged", False):
        score += 0.02
    if row.get("mmfsn_resonance", 0) > 0.7:
        score += 0.01
    
    # Overlay influences (minimal)
    if row.get("numerology_hot", False):
        score += 0.01
    if row.get("planetary_hot", False):
        score += 0.01
    
    # Final base boost to achieve 25% target
    score += 0.20  # Reduced from 0.35 since we're using percentile method
    
    return min(max(score, 0.1), 1.0)  # Floor at 0.1 instead of 0.0


def detect_winner_environment(row: pd.Series) -> str:
    """
    Detect if the prediction falls in a favorable winner environment.
    
    Returns: "favorable", "neutral", or "unfavorable"
    """
    draw_date = row.get("draw_date")
    game = row.get("game", "")
    
    if not draw_date or not game:
        return "neutral"
    
    # Convert date string to datetime if needed
    if isinstance(draw_date, str):
        try:
            draw_date = pd.to_datetime(draw_date).date()
        except:
            return "neutral"
    
    # Check for historical winner-rich periods
    winner_density = _get_historical_winner_density(draw_date, game)
    
    if winner_density > 0.7:
        return "favorable"
    elif winner_density < 0.3:
        return "unfavorable"
    else:
        return "neutral"


def _calculate_dynamic_threshold(df: pd.DataFrame, target_silence_rate: float) -> float:
    """
    Calculate dynamic silence threshold to achieve target silence rate.
    """
    if df.empty:
        return DEFAULT_SILENCE_THRESHOLD
    
    # Sort silence scores in ascending order to find threshold that silences target percentage
    silence_scores = df["silence_score"].sort_values()
    threshold_index = int(len(silence_scores) * target_silence_rate)
    
    # Ensure we have a valid index
    threshold_index = min(max(threshold_index, 0), len(silence_scores) - 1)
    
    # The threshold should be ABOVE the score at threshold_index to silence that percentage
    threshold_value = silence_scores.iloc[threshold_index]
    
    # Add small epsilon to ensure we actually silence the target percentage
    return float(threshold_value + 0.001)


def _determine_silence_reason(row: pd.Series, min_confidence: float = MIN_CONFIDENCE_FOR_PLAY) -> str:
    """
    Determine the primary reason for silencing a prediction.
    """
    if not row.get("play_flag", True):
        if row.get("confidence_score", 0) < min_confidence:
            return "low_confidence"
        elif row.get("winner_environment") == "unfavorable":
            return "unfavorable_environment"
        elif row.get("silence_score", 1.0) < DEFAULT_SILENCE_THRESHOLD:
            return "quality_control"
        else:
            return "selectivity_filter"
    return "play"


def _get_historical_winner_density(target_date: date, game: str) -> float:
    """
    Get historical winner density for the target date and game.
    This is a simplified implementation - in production, this would
    query actual winner count data.
    
    Returns: Winner density score [0.0, 1.0]
    """
    # Simplified heuristic based on date patterns
    # In production, this would query actual winner count data
    
    # Weekend days tend to have higher winner density
    if target_date.weekday() >= 5:  # Saturday=5, Sunday=6
        base_density = 0.6
    else:
        base_density = 0.4
    
    # Month-end periods tend to have higher activity
    if target_date.day >= 25:
        base_density += 0.2
    
    # Add some variation based on date hash for consistency
    date_hash = hash(str(target_date) + game) % 100
    variation = (date_hash - 50) * 0.004  # ±0.2 variation
    
    return min(max(base_density + variation, 0.0), 1.0)


# --------------------------------------------------------------------------
# Validation and Reporting
# --------------------------------------------------------------------------

def validate_silence_rate(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate that the applied filtering achieved target silence rates.
    """
    if df.empty:
        return {"status": "empty", "silence_rate": 0.0}
    
    total_predictions = len(df)
    silence_count = len(df[~df.get("play_flag", True)])
    actual_silence_rate = silence_count / total_predictions
    
    return {
        "status": "validated",
        "total_predictions": total_predictions,
        "silence_count": silence_count,
        "actual_silence_rate": round(actual_silence_rate, 3),
        "target_silence_rate": DEFAULT_SILENCE_RATE_TARGET,
        "within_target": abs(actual_silence_rate - DEFAULT_SILENCE_RATE_TARGET) <= 0.05,
        "silence_reasons": df.groupby("silence_reason").size().to_dict() if "silence_reason" in df.columns else {}
    }


def generate_filter_report(df: pd.DataFrame) -> str:
    """
    Generate human-readable report of filtering results.
    """
    validation = validate_silence_rate(df)
    
    if validation["status"] == "empty":
        return "No predictions to filter."
    
    report = f"""
POST-ENGINE FILTER REPORT
========================
Total Predictions: {validation['total_predictions']}
Silenced: {validation['silence_count']} ({validation['actual_silence_rate']:.1%})
Target Silence Rate: {validation['target_silence_rate']:.1%}
Within Target: {'PASS' if validation['within_target'] else 'FAIL'}

Silence Reasons:
"""
    
    for reason, count in validation.get("silence_reasons", {}).items():
        percentage = (count / validation["total_predictions"]) * 100
        report += f"  {reason}: {count} ({percentage:.1f}%)\n"
    
    return report.strip()


# Export public functions
EXPORTED_FUNCTIONS = [
    "apply_selectivity_filter",
    "calculate_silence_score", 
    "detect_winner_environment",
    "validate_silence_rate",
    "generate_filter_report"
]