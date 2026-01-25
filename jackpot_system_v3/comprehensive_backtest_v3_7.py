"""
comprehensive_backtest_v3_7.py
Comprehensive Validation Script for BOOK3 Kit Improvements

Purpose:
- Run backtest validation against Jan 1 - Nov 10, 2025 data
- Test both Cash games and Jackpot games  
- Validate confidence scoring improvements
- Verify selectivity filtering effectiveness
- Check winner environment correlation

Usage:
    python jackpot_system_v3/comprehensive_backtest_v3_7.py
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime, date
from pathlib import Path

# Project root setup
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import our modules
try:
    from core.v3_7.engine_core_v3_7 import MyBestOddsEngineV37
    from core.v3_7.post_engine_filter_v3_7 import apply_selectivity_filter, validate_silence_rate, generate_filter_report
    from audit.environment_validator_v3_7 import generate_validation_report, validate_winner_bias
    from audit.CONFIDENCE_AUDIT_v3_7 import validate_rows
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}")
    print("Make sure you're running from the jackpot_system_v3 directory.")
    sys.exit(1)


# Configuration
BACKTEST_START = "2025-01-01"
BACKTEST_END = "2025-11-10"
BOOK3_SUBSCRIBERS_DIR = PROJECT_ROOT / "data" / "subscribers" / "BOOK3"
OUTPUT_DIR = PROJECT_ROOT / "backtest_validation_output"
REPORT_DIR = OUTPUT_DIR / "reports"


def load_book3_subscribers():
    """Load all BOOK3 subscriber configurations."""
    if not BOOK3_SUBSCRIBERS_DIR.exists():
        print(f"[ERROR] BOOK3 subscribers directory not found: {BOOK3_SUBSCRIBERS_DIR}")
        return []
    
    subscribers = []
    for sub_file in BOOK3_SUBSCRIBERS_DIR.glob("*.json"):
        try:
            with open(sub_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config['_file_path'] = str(sub_file)
                subscribers.append(config)
        except Exception as e:
            print(f"[WARNING] Failed to load subscriber {sub_file}: {e}")
    
    return subscribers


def run_single_subscriber_backtest(subscriber_config, engine):
    """Run backtest for a single subscriber."""
    sub_name = subscriber_config.get('subscriber_id', 'Unknown')
    print(f"\n[BACKTEST] Running subscriber: {sub_name}")
    
    try:
        # Generate predictions
        predictions = engine.generate_forecast(BACKTEST_START, BACKTEST_END, subscriber_config)
        
        if not predictions:
            print(f"[WARNING] No predictions generated for {sub_name}")
            return None
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(predictions)
        print(f"[INFO] Generated {len(df)} raw predictions")
        
        # Apply post-engine filtering
        df_filtered = apply_selectivity_filter(df)
        print(f"[INFO] After filtering: {len(df_filtered)} predictions")
        
        # Analyze results
        results = {
            'subscriber_id': sub_name,
            'total_predictions': len(df),
            'filtered_predictions': len(df_filtered),
            'games_covered': df['game'].unique().tolist() if 'game' in df.columns else [],
            'confidence_stats': _analyze_confidence_distribution(df_filtered),
            'filtering_stats': validate_silence_rate(df_filtered),
            'environment_validation': validate_winner_bias(df_filtered) if not df_filtered.empty else {}
        }
        
        return results
        
    except Exception as e:
        print(f"[ERROR] Backtest failed for {sub_name}: {e}")
        return {
            'subscriber_id': sub_name,
            'error': str(e),
            'status': 'failed'
        }


def _analyze_confidence_distribution(df):
    """Analyze confidence score distribution for validation."""
    if df.empty or 'confidence_score' not in df.columns:
        return {"status": "no_data"}
    
    confidence_scores = pd.to_numeric(df['confidence_score'], errors='coerce').dropna()
    
    if confidence_scores.empty:
        return {"status": "no_valid_scores"}
    
    # Check for uniform scoring (the original problem)
    unique_scores = confidence_scores.nunique()
    score_variation = confidence_scores.std()
    
    return {
        "status": "analyzed",
        "mean": round(confidence_scores.mean(), 2),
        "std": round(confidence_scores.std(), 2),
        "min": round(confidence_scores.min(), 2),
        "max": round(confidence_scores.max(), 2),
        "unique_scores": unique_scores,
        "total_predictions": len(confidence_scores),
        "variation_healthy": score_variation > 5.0,  # Good variation indicator
        "range_healthy": (confidence_scores.max() - confidence_scores.min()) > 30.0,  # Good range
        "distribution": {
            "low_conf_20_40": len(confidence_scores[(confidence_scores >= 20) & (confidence_scores < 40)]),
            "med_conf_40_70": len(confidence_scores[(confidence_scores >= 40) & (confidence_scores < 70)]),  
            "high_conf_70_95": len(confidence_scores[(confidence_scores >= 70) & (confidence_scores <= 95)])
        }
    }


def generate_comprehensive_report(all_results):
    """Generate comprehensive validation report."""
    
    # Create reports directory
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    total_subscribers = len(all_results)
    successful_runs = len([r for r in all_results if 'error' not in r])
    failed_runs = total_subscribers - successful_runs
    
    # Aggregate statistics
    total_predictions = sum(r.get('total_predictions', 0) for r in all_results if 'total_predictions' in r)
    total_filtered = sum(r.get('filtered_predictions', 0) for r in all_results if 'filtered_predictions' in r)
    
    # Analyze confidence improvements
    confidence_improvements = []
    for result in all_results:
        conf_stats = result.get('confidence_stats', {})
        if conf_stats.get('status') == 'analyzed':
            confidence_improvements.append({
                'subscriber': result.get('subscriber_id'),
                'variation_healthy': conf_stats.get('variation_healthy', False),
                'range_healthy': conf_stats.get('range_healthy', False),
                'unique_scores': conf_stats.get('unique_scores', 0),
                'std_dev': conf_stats.get('std', 0)
            })
    
    # Calculate improvement metrics
    healthy_variation_pct = (len([c for c in confidence_improvements if c['variation_healthy']]) / 
                           len(confidence_improvements) * 100) if confidence_improvements else 0
    
    healthy_range_pct = (len([c for c in confidence_improvements if c['range_healthy']]) / 
                        len(confidence_improvements) * 100) if confidence_improvements else 0
    
    # Generate report
    report = f"""
COMPREHENSIVE BOOK3 BACKTEST VALIDATION REPORT
==============================================
Date Range: {BACKTEST_START} to {BACKTEST_END}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

EXECUTION SUMMARY
-----------------
Total Subscribers: {total_subscribers}
Successful Runs: {successful_runs}
Failed Runs: {failed_runs}
Success Rate: {(successful_runs/total_subscribers*100):.1f}%

PREDICTION VOLUME
-----------------
Total Raw Predictions: {total_predictions:,}
After Selectivity Filtering: {total_filtered:,}
Overall Silence Rate: {((total_predictions-total_filtered)/total_predictions*100):.1f}% (Target: ~25%)

CONFIDENCE SCORING IMPROVEMENTS
-------------------------------
Subscribers with Healthy Score Variation: {healthy_variation_pct:.1f}% (Target: >90%)
Subscribers with Healthy Score Range: {healthy_range_pct:.1f}% (Target: >90%)

Average Confidence Statistics:
"""
    
    if confidence_improvements:
        avg_std = sum(c['std_dev'] for c in confidence_improvements) / len(confidence_improvements)
        avg_unique = sum(c['unique_scores'] for c in confidence_improvements) / len(confidence_improvements)
        
        report += f"- Average Standard Deviation: {avg_std:.2f} (Target: >5.0)\n"
        report += f"- Average Unique Scores per Subscriber: {avg_unique:.1f} (Target: >20)\n"
    
    # Game coverage analysis
    games_covered = set()
    for result in all_results:
        games = result.get('games_covered', [])
        games_covered.update(games)
    
    report += f"""
GAME COVERAGE
-------------
Games Tested: {', '.join(sorted(games_covered)) if games_covered else 'None'}
Cash Games Included: {'✓' if any(g in ['Cash3', 'Cash4'] for g in games_covered) else '✗'}
Jackpot Games Included: {'✓' if any(g in ['MegaMillions', 'Powerball', 'Cash4Life'] for g in games_covered) else '✗'}

VALIDATION STATUS
-----------------
"""
    
    # Overall validation verdict
    confidence_fix_success = healthy_variation_pct >= 90 and healthy_range_pct >= 90
    silence_rate_success = 20 <= ((total_predictions-total_filtered)/total_predictions*100) <= 30
    
    if confidence_fix_success and silence_rate_success:
        verdict = "✅ VALIDATION PASSED"
        details = "Confidence scoring and selectivity improvements are working correctly."
    elif confidence_fix_success:
        verdict = "⚠️ PARTIAL SUCCESS"
        details = "Confidence scoring improved, but selectivity filtering needs adjustment."
    elif silence_rate_success:
        verdict = "⚠️ PARTIAL SUCCESS"  
        details = "Selectivity filtering working, but confidence scoring needs improvement."
    else:
        verdict = "❌ VALIDATION FAILED"
        details = "Both confidence scoring and selectivity filtering need additional work."
    
    report += f"""
Overall Verdict: {verdict}
{details}

RECOMMENDATIONS
---------------
"""
    
    if not confidence_fix_success:
        report += "• Adjust confidence scoring variation parameters in score_fx_v3_7.py\n"
    if not silence_rate_success:
        report += "• Tune selectivity threshold in post_engine_filter_v3_7.py\n"
    if failed_runs > 0:
        report += f"• Investigate {failed_runs} failed subscriber runs for errors\n"
    
    report += "\nDETAILED SUBSCRIBER RESULTS\n" + "=" * 27 + "\n"
    
    for result in all_results[:10]:  # Show first 10 detailed results
        sub_name = result.get('subscriber_id', 'Unknown')
        if 'error' in result:
            report += f"\n{sub_name}: FAILED - {result['error']}\n"
        else:
            conf_stats = result.get('confidence_stats', {})
            filter_stats = result.get('filtering_stats', {})
            
            report += f"""
{sub_name}:
- Predictions: {result.get('total_predictions', 0)} → {result.get('filtered_predictions', 0)}
- Silence Rate: {filter_stats.get('actual_silence_rate', 0):.1%}
- Confidence Range: {conf_stats.get('min', 0):.1f} - {conf_stats.get('max', 0):.1f}
- Score Variation: {'Healthy' if conf_stats.get('variation_healthy') else 'Poor'}
"""
    
    if len(all_results) > 10:
        report += f"\n... and {len(all_results) - 10} more subscribers (see detailed JSON output)\n"
    
    # Save report
    report_file = REPORT_DIR / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Save detailed JSON results
    json_file = REPORT_DIR / f"detailed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n[REPORTS SAVED]")
    print(f"Summary Report: {report_file}")
    print(f"Detailed Results: {json_file}")
    
    return report


def main():
    """Main execution function."""
    print(f"[START] Comprehensive BOOK3 Backtest Validation")
    print(f"Date Range: {BACKTEST_START} to {BACKTEST_END}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load subscribers
    print(f"\n[LOADING] BOOK3 subscribers from {BOOK3_SUBSCRIBERS_DIR}")
    subscribers = load_book3_subscribers()
    
    if not subscribers:
        print("[ERROR] No BOOK3 subscribers found. Cannot proceed with validation.")
        return
    
    print(f"[INFO] Found {len(subscribers)} BOOK3 subscribers")
    
    # Initialize engine
    print(f"\n[ENGINE] Initializing My Best Odds Engine v3.7...")
    engine = MyBestOddsEngineV37(config={})
    
    # Run backtests
    print(f"\n[BACKTEST] Running validation for all subscribers...")
    all_results = []
    
    for i, subscriber in enumerate(subscribers, 1):
        print(f"\nProgress: {i}/{len(subscribers)}")
        result = run_single_subscriber_backtest(subscriber, engine)
        if result:
            all_results.append(result)
    
    # Generate comprehensive report
    print(f"\n[REPORTING] Generating comprehensive validation report...")
    report = generate_comprehensive_report(all_results)
    
    # Print summary to console
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    # Extract key metrics from report for console display
    total_predictions = sum(r.get('total_predictions', 0) for r in all_results if 'total_predictions' in r)
    total_filtered = sum(r.get('filtered_predictions', 0) for r in all_results if 'filtered_predictions' in r)
    silence_rate = ((total_predictions-total_filtered)/total_predictions*100) if total_predictions > 0 else 0
    
    print(f"Total Predictions Generated: {total_predictions:,}")
    print(f"After Selectivity Filtering: {total_filtered:,}")
    print(f"Achieved Silence Rate: {silence_rate:.1f}% (Target: ~25%)")
    
    # Check if improvements were successful
    confidence_improvements = [r.get('confidence_stats', {}) for r in all_results if r.get('confidence_stats', {}).get('status') == 'analyzed']
    healthy_variation = len([c for c in confidence_improvements if c.get('variation_healthy', False)])
    
    if healthy_variation > 0:
        print(f"Confidence Scoring Improvement: {healthy_variation}/{len(confidence_improvements)} subscribers show healthy variation")
    
    print("\nSee detailed reports in:", REPORT_DIR)
    print("\n[COMPLETE] Backtest validation finished.")


if __name__ == "__main__":
    main()