#!/usr/bin/env python3
"""
MMFSN Course Corrector v3.7
Adjusts MMFSN (My Most Frequently Seen Numbers) weights when high-confidence predictions miss.
Tracks actual lottery results vs predictions for 75-100% confidence range plays.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

# Ensure proper imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

@dataclass
class PredictionResult:
    """Tracks a prediction and its actual outcome"""
    date: str
    game: str
    subscriber: str
    predicted_number: str
    actual_number: str
    confidence: float
    mmfsn_score: float
    astro_score: float
    numerology_score: float
    hit: bool

class MMFSNCourseCorrector:
    """
    Adjusts MMFSN weights based on high-confidence prediction performance.
    INTEGRATES WITH EXISTING KIT TRACKING SYSTEM.
    """
    
    def __init__(self, min_confidence: float = 75.0):
        self.min_confidence = min_confidence
        self.adjustment_factor = 0.05  # 5% weight adjustment per miss
        self.results_history = []
        self.execution_log = []  # Track all kit executions
        
    def log_kit_execution(self, subscriber: str, kit_name: str, date_range: str, predictions_count: int):
        """Log kit execution for tracking purposes"""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "subscriber": subscriber,
            "kit_name": kit_name, 
            "date_range": date_range,
            "predictions_generated": predictions_count,
            "smart_logic_version": "v3.7"
        }
        self.execution_log.append(execution_record)
        
        # Save to tracking file
        self._save_execution_log()
        
    def _save_execution_log(self):
        """Save execution log to file for SMART LOGIC tracking"""
        log_file = "data/smart_logic_execution_log.json"
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    existing_log = json.load(f)
            else:
                existing_log = []
                
            # Append new executions
            existing_log.extend(self.execution_log)
            
            # Keep only last 1000 executions (prevent file bloat)
            if len(existing_log) > 1000:
                existing_log = existing_log[-1000:]
                
            with open(log_file, 'w') as f:
                json.dump(existing_log, f, indent=2)
                
            print(f"📝 Execution log updated: {len(existing_log)} total kit runs tracked")
            
        except Exception as e:
            print(f"⚠️ Could not save execution log: {e}")
    
    def get_subscriber_usage_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all subscribers using SMART LOGIC"""
        
        log_file = "data/smart_logic_execution_log.json"
        if not os.path.exists(log_file):
            return {}
            
        try:
            with open(log_file, 'r') as f:
                execution_log = json.load(f)
        except:
            return {}
        
        stats = defaultdict(lambda: {
            'total_runs': 0,
            'kits_used': set(),
            'first_run': None,
            'last_run': None,
            'predictions_generated': 0
        })
        
        for record in execution_log:
            subscriber = record.get('subscriber', 'Unknown')
            stats[subscriber]['total_runs'] += 1
            stats[subscriber]['kits_used'].add(record.get('kit_name', 'Unknown'))
            stats[subscriber]['predictions_generated'] += record.get('predictions_generated', 0)
            
            timestamp = record.get('timestamp', '')
            if not stats[subscriber]['first_run'] or timestamp < stats[subscriber]['first_run']:
                stats[subscriber]['first_run'] = timestamp
            if not stats[subscriber]['last_run'] or timestamp > stats[subscriber]['last_run']:
                stats[subscriber]['last_run'] = timestamp
        
        # Convert sets to lists for JSON serialization
        for subscriber_data in stats.values():
            subscriber_data['kits_used'] = list(subscriber_data['kits_used'])
            
        return dict(stats)
        
    def load_actual_results(self, results_file: str) -> Dict[str, Dict[str, str]]:
        """Load actual lottery results from file"""
        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Results file not found: {results_file}")
            return {}
    
    def load_prediction_data(self, output_dir: str) -> List[PredictionResult]:
        """Load prediction data from subscriber output directory"""
        predictions = []
        
        if not os.path.exists(output_dir):
            return predictions
            
        # Load summary data
        summary_file = os.path.join(output_dir, "summary.json")
        if not os.path.exists(summary_file):
            return predictions
            
        with open(summary_file, 'r') as f:
            summary = json.load(f)
            
        subscriber_name = summary['subscriber']['initials']
        
        # Load daily prediction files
        for filename in os.listdir(output_dir):
            if filename.endswith('.json') and filename != 'summary.json':
                date_str = filename.replace('.json', '')
                daily_file = os.path.join(output_dir, filename)
                
                with open(daily_file, 'r') as f:
                    daily_data = json.load(f)
                
                # Extract predictions for each game
                for game, game_data in daily_data.get('predictions', {}).items():
                    if isinstance(game_data, dict) and 'picks' in game_data:
                        for pick in game_data['picks']:
                            pred_result = PredictionResult(
                                date=date_str,
                                game=game,
                                subscriber=subscriber_name,
                                predicted_number=pick.get('number', ''),
                                actual_number='',  # To be filled by actual results
                                confidence=daily_data.get('score', 0.0),
                                mmfsn_score=daily_data.get('score_components', {}).get('mmfsn', 0.0),
                                astro_score=daily_data.get('score_components', {}).get('astro', 0.0),
                                numerology_score=daily_data.get('score_components', {}).get('numerology', 0.0),
                                hit=False  # To be determined
                            )
                            predictions.append(pred_result)
        
        return predictions
    
    def compare_predictions_to_results(self, predictions: List[PredictionResult], 
                                     actual_results: Dict[str, Dict[str, str]]) -> List[PredictionResult]:
        """Compare predictions to actual results and mark hits/misses"""
        
        for pred in predictions:
            # Skip low confidence predictions
            if pred.confidence < self.min_confidence:
                continue
                
            # Look up actual result for this date/game
            date_results = actual_results.get(pred.date, {})
            actual_number = date_results.get(pred.game, '')
            
            if actual_number:
                pred.actual_number = actual_number
                pred.hit = (pred.predicted_number == actual_number)
        
        return [p for p in predictions if p.confidence >= self.min_confidence]
    
    def analyze_mmfsn_performance(self, predictions: List[PredictionResult]) -> Dict[str, Dict]:
        """Analyze MMFSN performance by subscriber and game"""
        analysis = {}
        
        for pred in predictions:
            if pred.subscriber not in analysis:
                analysis[pred.subscriber] = {
                    'total_predictions': 0,
                    'mmfsn_influenced_misses': 0,
                    'games': {}
                }
            
            subscriber_data = analysis[pred.subscriber]
            subscriber_data['total_predictions'] += 1
            
            if pred.game not in subscriber_data['games']:
                subscriber_data['games'][pred.game] = {
                    'predictions': 0,
                    'hits': 0,
                    'mmfsn_misses': 0,
                    'avg_mmfsn_score': 0.0
                }
            
            game_data = subscriber_data['games'][pred.game]
            game_data['predictions'] += 1
            
            if pred.hit:
                game_data['hits'] += 1
            else:
                # Check if MMFSN score was high (indicating MMFSN influenced the miss)
                if pred.mmfsn_score > 50.0:  # High MMFSN influence
                    subscriber_data['mmfsn_influenced_misses'] += 1
                    game_data['mmfsn_misses'] += 1
            
            # Update average MMFSN score
            game_data['avg_mmfsn_score'] = (
                (game_data['avg_mmfsn_score'] * (game_data['predictions'] - 1) + pred.mmfsn_score) / 
                game_data['predictions']
            )
        
        return analysis
    
    def calculate_weight_adjustments(self, analysis: Dict[str, Dict]) -> Dict[str, Dict]:
        """Calculate MMFSN weight adjustments based on performance"""
        adjustments = {}
        
        for subscriber, data in analysis.items():
            if data['total_predictions'] == 0:
                continue
                
            # Calculate miss rate influenced by MMFSN
            mmfsn_miss_rate = data['mmfsn_influenced_misses'] / data['total_predictions']
            
            # Adjust MMFSN weight down for high miss rates
            if mmfsn_miss_rate > 0.3:  # 30% miss rate threshold
                weight_reduction = min(mmfsn_miss_rate * self.adjustment_factor, 0.20)  # Max 20% reduction
                
                adjustments[subscriber] = {
                    'mmfsn_weight_adjustment': -weight_reduction,
                    'reason': f'High MMFSN miss rate: {mmfsn_miss_rate:.2%}',
                    'games': {}
                }
                
                # Game-specific adjustments
                for game, game_data in data['games'].items():
                    if game_data['predictions'] > 0:
                        game_miss_rate = game_data['mmfsn_misses'] / game_data['predictions']
                        if game_miss_rate > 0.4:  # 40% game-specific miss rate
                            game_weight_reduction = min(game_miss_rate * self.adjustment_factor, 0.15)
                            adjustments[subscriber]['games'][game] = {
                                'mmfsn_weight_adjustment': -game_weight_reduction,
                                'reason': f'High {game} MMFSN miss rate: {game_miss_rate:.2%}'
                            }
        
        return adjustments
    
    def apply_weight_adjustments(self, adjustments: Dict[str, Dict], config_file: str):
        """Apply weight adjustments to configuration"""
        
        # Load current config
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Config file not found: {config_file}")
            return
        
        # Apply adjustments
        for subscriber, adj_data in adjustments.items():
            mmfsn_adjustment = adj_data['mmfsn_weight_adjustment']
            
            # Update global MMFSN weight for subscriber
            if 'subscribers' not in config:
                config['subscribers'] = {}
            if subscriber not in config['subscribers']:
                config['subscribers'][subscriber] = {}
            
            current_weight = config['subscribers'][subscriber].get('mmfsn_weight', 1.0)
            new_weight = max(0.1, current_weight + mmfsn_adjustment)  # Min weight of 0.1
            
            config['subscribers'][subscriber]['mmfsn_weight'] = round(new_weight, 3)
            config['subscribers'][subscriber]['last_adjustment'] = datetime.now().isoformat()
            config['subscribers'][subscriber]['adjustment_reason'] = adj_data['reason']
            
            print(f"📉 {subscriber}: MMFSN weight {current_weight:.3f} → {new_weight:.3f} ({adj_data['reason']})")
        
        # Save updated config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"💾 Weight adjustments saved to {config_file}")
    
    def generate_performance_report(self, analysis: Dict[str, Dict], adjustments: Dict[str, Dict], usage_stats: Dict[str, Dict]) -> str:
        """Generate performance analysis report with SMART LOGIC usage tracking"""
        report_lines = [
            "=" * 80,
            "📊 SMART LOGIC SYSTEM - MMFSN COURSE CORRECTION REPORT",
            "=" * 80,
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Minimum Confidence Threshold: {self.min_confidence}%",
            f"System Version: v3.7 - Adaptive Learning Engine",
            ""
        ]
        
        # SMART LOGIC Usage Summary
        if usage_stats:
            report_lines.extend([
                "🎯 SMART LOGIC SYSTEM USAGE SUMMARY:",
                f"   Active Subscribers: {len(usage_stats)}",
                f"   Total Kit Executions: {sum(stats['total_runs'] for stats in usage_stats.values())}",
                f"   Total Predictions Generated: {sum(stats['predictions_generated'] for stats in usage_stats.values())}",
                ""
            ])
            
            # Top users
            sorted_users = sorted(usage_stats.items(), key=lambda x: x[1]['total_runs'], reverse=True)
            report_lines.extend([
                "👥 TOP SMART LOGIC USERS:",
            ])
            for subscriber, stats in sorted_users[:5]:
                kits = ', '.join(stats['kits_used'])
                report_lines.append(f"   {subscriber}: {stats['total_runs']} runs, {stats['predictions_generated']} predictions ({kits})")
            
            report_lines.append("")
        
        # Performance Analysis
        for subscriber, data in analysis.items():
            if data['total_predictions'] == 0:
                continue
                
            report_lines.extend([
                f"👤 SUBSCRIBER: {subscriber}",
                f"   Total High-Confidence Predictions: {data['total_predictions']}",
                f"   MMFSN-Influenced Misses: {data['mmfsn_influenced_misses']}",
                f"   MMFSN Miss Rate: {data['mmfsn_influenced_misses']/data['total_predictions']:.2%}",
                ""
            ])
            
            # Game breakdown
            for game, game_data in data['games'].items():
                hit_rate = game_data['hits'] / game_data['predictions'] if game_data['predictions'] > 0 else 0
                report_lines.append(f"   🎮 {game}: {game_data['hits']}/{game_data['predictions']} hits ({hit_rate:.2%}) | Avg MMFSN: {game_data['avg_mmfsn_score']:.1f}")
            
            # Adjustments applied
            if subscriber in adjustments:
                adj_data = adjustments[subscriber]
                report_lines.extend([
                    f"   ⚙️ ADJUSTMENT: {adj_data['mmfsn_weight_adjustment']:+.3f} weight change",
                    f"   📝 REASON: {adj_data['reason']}",
                ])
            
            report_lines.append("")
        
        report_lines.extend([
            "🚀 SMART LOGIC ADAPTIVE LEARNING:",
            "   • System tracks every kit execution and prediction",
            "   • Automatically adjusts MMFSN weights based on performance", 
            "   • Each subscriber's system learns independently",
            "   • Continuous improvement through real-world results",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def run_course_correction(self, outputs_dir: str, results_file: str, config_file: str):
        """
        Run complete course correction analysis.
        INTEGRATES WITH EXISTING KIT TRACKING SYSTEM.
        """
        
        print("🔄 Starting MMFSN Course Correction Analysis...")
        print("🎯 SMART LOGIC System - Adaptive Learning Engine v3.7")
        
        # Load actual results
        actual_results = self.load_actual_results(results_file)
        if not actual_results:
            print("❌ No actual results loaded - course correction aborted")
            return
        
        all_predictions = []
        kit_executions_found = 0
        
        # Process all subscriber output directories
        for item in os.listdir(outputs_dir):
            if item.startswith('BOOK3_') and os.path.isdir(os.path.join(outputs_dir, item)):
                output_dir = os.path.join(outputs_dir, item)
                predictions = self.load_prediction_data(output_dir)
                
                if predictions:
                    # Extract subscriber and date range for tracking
                    subscriber = predictions[0].subscriber if predictions else "Unknown"
                    date_range = item.split('_')[-1] if '_' in item else "Unknown"
                    
                    # Log this kit execution
                    self.log_kit_execution(
                        subscriber=subscriber,
                        kit_name="BOOK3",
                        date_range=date_range,
                        predictions_count=len(predictions)
                    )
                    kit_executions_found += 1
                
                all_predictions.extend(predictions)
        
        if not all_predictions:
            print("❌ No prediction data found")
            return
        
        print(f"📊 Loaded {len(all_predictions)} predictions from {kit_executions_found} kit executions")
        
        # Display SMART LOGIC usage statistics
        usage_stats = self.get_subscriber_usage_stats()
        print(f"👥 SMART LOGIC System tracking {len(usage_stats)} subscribers")
        
        # Compare with actual results
        high_confidence_predictions = self.compare_predictions_to_results(all_predictions, actual_results)
        print(f"🎯 Analyzing {len(high_confidence_predictions)} high-confidence predictions")
        
        # Analyze MMFSN performance
        analysis = self.analyze_mmfsn_performance(high_confidence_predictions)
        
        # Calculate adjustments
        adjustments = self.calculate_weight_adjustments(analysis)
        
        # Apply adjustments
        if adjustments:
            self.apply_weight_adjustments(adjustments, config_file)
            print(f"✅ Applied adjustments to {len(adjustments)} subscribers")
        else:
            print("✅ No weight adjustments needed")
        
        # Generate report
        report = self.generate_performance_report(analysis, adjustments, usage_stats)
        
        # Save report
        report_file = os.path.join(outputs_dir, f"mmfsn_course_correction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📋 Report saved to: {report_file}")
        print(f"🎯 SMART LOGIC System continues learning and improving!")
        print("\n" + report)

def main():
    """Main execution function"""
    if len(sys.argv) < 4:
        print("Usage: python mmfsn_course_corrector_v3_7.py <outputs_dir> <results_file> <config_file>")
        sys.exit(1)
    
    outputs_dir = sys.argv[1]
    results_file = sys.argv[2]  
    config_file = sys.argv[3]
    
    corrector = MMFSNCourseCorrector(min_confidence=75.0)
    corrector.run_course_correction(outputs_dir, results_file, config_file)

if __name__ == "__main__":
    main()