"""
environment_validator_v3_7.py
Winner Environment Validation & Accuracy Assessment

Purpose:
- Validate that signals bias toward winner-rich environments
- Measure correlation between predictions and actual winner counts
- Provide environment accuracy metrics for system validation
- Support backtest analysis against historical winner data

Key Functions:
- validate_winner_bias(): Core validation logic
- compute_environment_accuracy(): Accuracy measurement
- analyze_signal_environment_correlation(): Statistical analysis
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import os


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

WINNER_DATA_PATHS = {
    "Cash3": "data/results/ga_results/Sorted/Cash3_History.csv",
    "Cash4": "data/results/ga_results/Sorted/Cash4_History.csv",
    "MegaMillions": "data/results/jackpot_results/MegaMillions.csv",
    "Powerball": "data/results/jackpot_results/Powerball.csv",
    "Cash4Life": "data/results/jackpot_results/Cash4Life.csv"
}

ENVIRONMENT_THRESHOLDS = {
    "high_winner_density": 0.7,
    "medium_winner_density": 0.4,
    "low_winner_density": 0.3
}


# --------------------------------------------------------------------------
# Core Validation Functions
# --------------------------------------------------------------------------

def validate_winner_bias(predictions_df: pd.DataFrame, actual_winners_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Validate that prediction signals bias toward winner-rich environments.
    
    Args:
        predictions_df: DataFrame with predictions and confidence scores
        actual_winners_df: Optional DataFrame with actual winner count data
    
    Returns:
        Dictionary with validation results and bias metrics
    """
    if predictions_df.empty:
        return {"status": "empty", "bias_validated": False}
    
    try:
        # Load winner data if not provided
        if actual_winners_df is None:
            actual_winners_df = _load_winner_data_for_predictions(predictions_df)
        
        if actual_winners_df.empty:
            return {"status": "no_winner_data", "bias_validated": False}
        
        # Merge predictions with winner data
        merged_df = _merge_predictions_with_winners(predictions_df, actual_winners_df)
        
        if merged_df.empty:
            return {"status": "no_matches", "bias_validated": False}
        
        # Calculate bias metrics
        bias_metrics = _calculate_bias_metrics(merged_df)
        
        # Determine if bias is acceptable
        bias_validated = (
            bias_metrics["high_conf_in_high_winner"] > 0.6 and
            bias_metrics["low_conf_in_low_winner"] > 0.5 and
            bias_metrics["correlation_coefficient"] > 0.3
        )
        
        return {
            "status": "validated",
            "bias_validated": bias_validated,
            "total_predictions": len(predictions_df),
            "matched_predictions": len(merged_df),
            "bias_metrics": bias_metrics,
            "recommendation": _generate_bias_recommendation(bias_metrics, bias_validated)
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e), "bias_validated": False}


def compute_environment_accuracy(signals_df: pd.DataFrame, winner_density_df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute accuracy metrics for environment detection.
    
    Args:
        signals_df: DataFrame with prediction signals and environment classifications
        winner_density_df: DataFrame with actual winner density data
    
    Returns:
        Dictionary with accuracy metrics
    """
    if signals_df.empty or winner_density_df.empty:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
    
    try:
        # Merge data by date and game
        merged = pd.merge(
            signals_df[["draw_date", "game", "winner_environment"]],
            winner_density_df[["draw_date", "game", "actual_winner_density"]],
            on=["draw_date", "game"],
            how="inner"
        )
        
        if merged.empty:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
        
        # Convert actual density to environment classification
        merged["actual_environment"] = merged["actual_winner_density"].apply(_density_to_environment)
        
        # Calculate accuracy metrics
        total = len(merged)
        correct = len(merged[merged["winner_environment"] == merged["actual_environment"]])
        
        accuracy = correct / total if total > 0 else 0.0
        
        # Calculate precision and recall for "favorable" environment detection
        favorable_predicted = merged["winner_environment"] == "favorable"
        favorable_actual = merged["actual_environment"] == "favorable"
        
        true_positives = len(merged[favorable_predicted & favorable_actual])
        predicted_positives = len(merged[favorable_predicted])
        actual_positives = len(merged[favorable_actual])
        
        precision = true_positives / predicted_positives if predicted_positives > 0 else 0.0
        recall = true_positives / actual_positives if actual_positives > 0 else 0.0
        
        return {
            "accuracy": round(accuracy, 3),
            "precision": round(precision, 3), 
            "recall": round(recall, 3),
            "f1_score": round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 0.0
        }
        
    except Exception as e:
        print(f"[WARNING] Environment accuracy calculation failed: {e}")
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}


def analyze_signal_environment_correlation(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze correlation between signal strength and winner environments.
    
    Args:
        df: DataFrame with signals, confidence scores, and environment data
    
    Returns:
        Dictionary with correlation analysis results
    """
    if df.empty or "confidence_score" not in df.columns:
        return {"correlation": 0.0, "significance": "none"}
    
    try:
        # Convert environment to numeric for correlation
        environment_numeric = df.get("winner_environment", pd.Series(["neutral"] * len(df))).map({
            "favorable": 1.0,
            "neutral": 0.5,
            "unfavorable": 0.0
        }).fillna(0.5)
        
        confidence_scores = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0)
        
        # Calculate Pearson correlation
        correlation = environment_numeric.corr(confidence_scores)
        
        # Determine significance level
        if abs(correlation) > 0.5:
            significance = "strong"
        elif abs(correlation) > 0.3:
            significance = "moderate"
        elif abs(correlation) > 0.1:
            significance = "weak"
        else:
            significance = "none"
        
        return {
            "correlation": round(correlation, 3),
            "significance": significance,
            "sample_size": len(df),
            "analysis": _generate_correlation_analysis(correlation, significance)
        }
        
    except Exception as e:
        print(f"[WARNING] Correlation analysis failed: {e}")
        return {"correlation": 0.0, "significance": "none"}


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _load_winner_data_for_predictions(predictions_df: pd.DataFrame) -> pd.DataFrame:
    """Load winner count data for games present in predictions."""
    winner_dfs = []
    
    games_in_predictions = predictions_df["game"].unique() if "game" in predictions_df.columns else []
    
    for game in games_in_predictions:
        if game in WINNER_DATA_PATHS:
            try:
                winner_path = WINNER_DATA_PATHS[game]
                if os.path.exists(winner_path):
                    winner_df = pd.read_csv(winner_path)
                    winner_df["game"] = game
                    winner_dfs.append(winner_df)
            except Exception as e:
                print(f"[WARNING] Could not load winner data for {game}: {e}")
    
    return pd.concat(winner_dfs, ignore_index=True) if winner_dfs else pd.DataFrame()


def _merge_predictions_with_winners(predictions_df: pd.DataFrame, winners_df: pd.DataFrame) -> pd.DataFrame:
    """Merge predictions with winner count data by date and game."""
    try:
        # Ensure date columns are properly formatted
        if "draw_date" in predictions_df.columns:
            predictions_df["draw_date"] = pd.to_datetime(predictions_df["draw_date"]).dt.date
        if "date" in winners_df.columns:
            winners_df["date"] = pd.to_datetime(winners_df["date"]).dt.date
            winners_df = winners_df.rename(columns={"date": "draw_date"})
        
        # Merge on date and game
        merged = pd.merge(
            predictions_df,
            winners_df[["draw_date", "game", "winner_count"]].drop_duplicates(),
            on=["draw_date", "game"],
            how="left"
        )
        
        # Calculate winner density
        if "winner_count" in merged.columns:
            merged["actual_winner_density"] = pd.to_numeric(merged["winner_count"], errors="coerce").fillna(0) / 100.0
            merged["actual_winner_density"] = merged["actual_winner_density"].clip(0, 1)
        
        return merged
        
    except Exception as e:
        print(f"[WARNING] Merge failed: {e}")
        return pd.DataFrame()


def _calculate_bias_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate bias metrics from merged prediction/winner data."""
    metrics = {}
    
    # Convert confidence to categories
    df["confidence_category"] = pd.cut(
        pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0),
        bins=[0, 40, 70, 100],
        labels=["low", "medium", "high"]
    )
    
    # Convert winner density to categories
    df["winner_category"] = pd.cut(
        df["actual_winner_density"].fillna(0),
        bins=[0, 0.3, 0.7, 1.0],
        labels=["low", "medium", "high"]
    )
    
    total = len(df)
    if total == 0:
        return {k: 0.0 for k in ["high_conf_in_high_winner", "low_conf_in_low_winner", "correlation_coefficient"]}
    
    # High confidence predictions in high winner environments
    high_conf_high_winner = len(df[(df["confidence_category"] == "high") & (df["winner_category"] == "high")])
    high_conf_total = len(df[df["confidence_category"] == "high"])
    metrics["high_conf_in_high_winner"] = high_conf_high_winner / high_conf_total if high_conf_total > 0 else 0.0
    
    # Low confidence predictions in low winner environments  
    low_conf_low_winner = len(df[(df["confidence_category"] == "low") & (df["winner_category"] == "low")])
    low_conf_total = len(df[df["confidence_category"] == "low"])
    metrics["low_conf_in_low_winner"] = low_conf_low_winner / low_conf_total if low_conf_total > 0 else 0.0
    
    # Overall correlation
    try:
        confidence_numeric = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0)
        winner_density_numeric = pd.to_numeric(df["actual_winner_density"], errors="coerce").fillna(0)
        metrics["correlation_coefficient"] = confidence_numeric.corr(winner_density_numeric) or 0.0
    except:
        metrics["correlation_coefficient"] = 0.0
    
    return {k: round(v, 3) for k, v in metrics.items()}


def _density_to_environment(density: float) -> str:
    """Convert winner density to environment classification."""
    if density >= ENVIRONMENT_THRESHOLDS["high_winner_density"]:
        return "favorable"
    elif density >= ENVIRONMENT_THRESHOLDS["medium_winner_density"]:
        return "neutral"
    else:
        return "unfavorable"


def _generate_bias_recommendation(bias_metrics: Dict[str, float], bias_validated: bool) -> str:
    """Generate recommendation based on bias validation results."""
    if bias_validated:
        return "✓ Winner bias validation PASSED. Signals appropriately favor winner-rich environments."
    
    issues = []
    if bias_metrics.get("high_conf_in_high_winner", 0) <= 0.6:
        issues.append("High confidence predictions not sufficiently biased toward high-winner environments")
    if bias_metrics.get("low_conf_in_low_winner", 0) <= 0.5:
        issues.append("Low confidence predictions not sufficiently correlated with low-winner environments")
    if bias_metrics.get("correlation_coefficient", 0) <= 0.3:
        issues.append("Overall correlation between confidence and winner density is weak")
    
    return "✗ Winner bias validation FAILED. Issues: " + "; ".join(issues)


def _generate_correlation_analysis(correlation: float, significance: str) -> str:
    """Generate human-readable correlation analysis."""
    if significance == "strong":
        return f"Strong {'positive' if correlation > 0 else 'negative'} correlation (r={correlation:.3f}) indicates good environment detection."
    elif significance == "moderate":
        return f"Moderate {'positive' if correlation > 0 else 'negative'} correlation (r={correlation:.3f}) suggests acceptable environment sensitivity."
    elif significance == "weak":
        return f"Weak correlation (r={correlation:.3f}) indicates limited environment detection capability."
    else:
        return f"No meaningful correlation (r={correlation:.3f}) between signals and winner environments."


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def generate_validation_report(predictions_df: pd.DataFrame, winner_data_df: Optional[pd.DataFrame] = None) -> str:
    """Generate comprehensive validation report for winner environment detection."""
    
    # Run validation
    bias_validation = validate_winner_bias(predictions_df, winner_data_df)
    
    # Generate correlation analysis
    correlation_analysis = analyze_signal_environment_correlation(predictions_df)
    
    # Build report
    report = f"""
WINNER ENVIRONMENT VALIDATION REPORT
===================================
Status: {bias_validation.get('status', 'unknown').upper()}
Bias Validated: {'✓ PASS' if bias_validation.get('bias_validated', False) else '✗ FAIL'}

Prediction Statistics:
- Total Predictions: {bias_validation.get('total_predictions', 0)}
- Matched with Winner Data: {bias_validation.get('matched_predictions', 0)}

Bias Metrics:
"""
    
    bias_metrics = bias_validation.get('bias_metrics', {})
    for metric, value in bias_metrics.items():
        report += f"- {metric.replace('_', ' ').title()}: {value:.3f}\n"
    
    report += f"""
Correlation Analysis:
- Correlation Coefficient: {correlation_analysis.get('correlation', 0):.3f}
- Significance Level: {correlation_analysis.get('significance', 'unknown').upper()}
- Sample Size: {correlation_analysis.get('sample_size', 0)}

Analysis: {correlation_analysis.get('analysis', 'No analysis available')}

Recommendation:
{bias_validation.get('recommendation', 'No recommendation available')}
"""
    
    return report.strip()


# Export public functions
EXPORTED_FUNCTIONS = [
    "validate_winner_bias",
    "compute_environment_accuracy", 
    "analyze_signal_environment_correlation",
    "generate_validation_report"
]