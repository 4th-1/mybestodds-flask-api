#!/usr/bin/env python3
"""
CONFIDENCE DISTRIBUTION ANALYZER
=====================================
Analyzes the actual confidence distribution from our 2000 test subscribers
to understand realistic confidence levels and adjust filtering accordingly.
"""

import os
import sys
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time

# Get project root and setup path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

class ConfidenceAnalyzer:
    """Analyzes confidence distribution from processed subscribers."""
    
    def __init__(self):
        self.data_dir = os.path.join(PROJECT_ROOT, 'data')
        self.target_date = '2025-12-22'
        self.all_confidences = []
        self.all_predictions = []
        
    def analyze_subscriber_output(self, subscriber_id):
        """Analyze confidence distribution for a single subscriber."""
        try:
            # Look for the subscriber's JSON output
            output_file = os.path.join(self.data_dir, f"{subscriber_id}_{self.target_date}_daily.json")
            
            if not os.path.exists(output_file):
                return None
                
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            confidences = []
            predictions = []
            
            # Extract confidence scores from predictions
            for game in ['Cash3', 'Cash4', 'Cash4Life', 'MegaMillions']:
                if game in data.get('predictions', {}):
                    game_data = data['predictions'][game]
                    
                    # Extract cash confidence
                    if 'cash_confidence' in game_data:
                        cash_conf = float(game_data['cash_confidence'])
                        confidences.append({
                            'subscriber_id': subscriber_id,
                            'game': game,
                            'type': 'cash_confidence',
                            'confidence': cash_conf
                        })
                        
                        if cash_conf >= 60:  # 60%+ threshold for analysis
                            predictions.append({
                                'subscriber_id': subscriber_id,
                                'game': game,
                                'type': 'cash_confidence',
                                'confidence': cash_conf,
                                'prediction': game_data.get('number', 'N/A'),
                                'date': self.target_date
                            })
                    
                    # Extract jackpot confidence
                    if 'jackpot_confidence' in game_data:
                        jp_conf = float(game_data['jackpot_confidence'])
                        confidences.append({
                            'subscriber_id': subscriber_id,
                            'game': game,
                            'type': 'jackpot_confidence',
                            'confidence': jp_conf
                        })
                        
                        if jp_conf >= 60:  # 60%+ threshold for analysis
                            predictions.append({
                                'subscriber_id': subscriber_id,
                                'game': game,
                                'type': 'jackpot_confidence',
                                'confidence': jp_conf,
                                'prediction': game_data.get('number', 'N/A'),
                                'date': self.target_date
                            })
            
            return confidences, predictions
            
        except Exception as e:
            print(f"   ❌ Error analyzing {subscriber_id}: {e}")
            return None
    
    def analyze_batch(self, start_id, end_id):
        """Analyze a batch of subscribers."""
        batch_confidences = []
        batch_predictions = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            subscriber_ids = [f"TEST{i:04d}" for i in range(start_id, end_id + 1)]
            results = list(executor.map(self.analyze_subscriber_output, subscriber_ids))
            
            for result in results:
                if result:
                    confidences, predictions = result
                    batch_confidences.extend(confidences)
                    batch_predictions.extend(predictions)
        
        return batch_confidences, batch_predictions
    
    def run_full_analysis(self):
        """Run full confidence distribution analysis."""
        print("🔍 MY BEST ODDS - CONFIDENCE DISTRIBUTION ANALYSIS")
        print("=" * 80)
        print(f"📅 Date: {self.target_date}")
        print(f"👥 Analyzing: 2000 test subscribers")
        print()
        
        # Process in batches of 100 for faster analysis
        batch_size = 100
        total_batches = 20
        
        for batch_num in range(1, total_batches + 1):
            start_id = (batch_num - 1) * batch_size + 1
            end_id = batch_num * batch_size
            
            print(f"📦 BATCH {batch_num}/{total_batches} (TEST{start_id:04d}-TEST{end_id:04d})")
            print("-" * 50)
            
            batch_confidences, batch_predictions = self.analyze_batch(start_id, end_id)
            
            self.all_confidences.extend(batch_confidences)
            self.all_predictions.extend(batch_predictions)
            
            print(f"   📊 Confidence scores collected: {len(batch_confidences)}")
            print(f"   🎯 High predictions (60%+): {len(batch_predictions)}")
            print()
        
        # Generate comprehensive analysis
        self.generate_analysis_report()
    
    def generate_analysis_report(self):
        """Generate comprehensive confidence analysis report."""
        if not self.all_confidences:
            print("❌ No confidence data found!")
            return
        
        df_conf = pd.DataFrame(self.all_confidences)
        df_pred = pd.DataFrame(self.all_predictions)
        
        print("📈 CONFIDENCE DISTRIBUTION ANALYSIS")
        print("=" * 80)
        
        # Overall statistics
        print(f"📊 Total confidence scores analyzed: {len(self.all_confidences):,}")
        print(f"🎯 High confidence predictions (60%+): {len(self.all_predictions):,}")
        print()
        
        # Distribution by ranges
        print("📊 CONFIDENCE DISTRIBUTION BY RANGES:")
        print("-" * 50)
        
        ranges = [
            (90, 100, "🔥 ELITE (90-100%)"),
            (80, 89.99, "⭐ PREMIUM (80-89%)"),
            (75, 79.99, "💎 HIGH (75-79%)"),
            (70, 74.99, "🎯 STRONG (70-74%)"),
            (65, 69.99, "✅ GOOD (65-69%)"),
            (60, 64.99, "📈 ABOVE AVERAGE (60-64%)"),
            (50, 59.99, "📊 AVERAGE (50-59%)"),
            (0, 49.99, "📉 BELOW AVERAGE (<50%)")
        ]
        
        for min_conf, max_conf, label in ranges:
            count = len(df_conf[(df_conf['confidence'] >= min_conf) & (df_conf['confidence'] <= max_conf)])
            pct = (count / len(df_conf)) * 100 if len(df_conf) > 0 else 0
            print(f"  {label}: {count:,} ({pct:.1f}%)")
        
        print()
        
        # Top predictions report
        if len(self.all_predictions) > 0:
            print("🏆 TOP HIGH CONFIDENCE PREDICTIONS (60%+)")
            print("=" * 80)
            
            df_pred_sorted = df_pred.sort_values('confidence', ascending=False)
            
            # Group by confidence ranges
            for min_conf, max_conf, label in ranges[:6]:  # Only show 60%+ ranges
                range_preds = df_pred_sorted[
                    (df_pred_sorted['confidence'] >= min_conf) & 
                    (df_pred_sorted['confidence'] <= max_conf)
                ]
                
                if len(range_preds) > 0:
                    print(f"\n{label}:")
                    print("-" * 50)
                    
                    # Show top 10 from this range
                    for idx, row in range_preds.head(10).iterrows():
                        print(f"  🎲 {row['subscriber_id']}: {row['game']} - {row['prediction']} ({row['confidence']:.1f}%)")
            
            # Save detailed report
            self.save_detailed_report(df_pred_sorted)
        else:
            print("❌ No high confidence predictions (60%+) found.")
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE!")
    
    def save_detailed_report(self, df_pred_sorted):
        """Save detailed report to JSON and CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON report
        json_file = os.path.join(PROJECT_ROOT, f"confidence_analysis_{timestamp}.json")
        report_data = {
            'analysis_date': datetime.now().isoformat(),
            'target_date': self.target_date,
            'total_subscribers': 2000,
            'total_confidence_scores': len(self.all_confidences),
            'high_confidence_predictions': len(self.all_predictions),
            'top_predictions': df_pred_sorted.to_dict('records')[:100]  # Top 100
        }
        
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Save CSV report
        csv_file = os.path.join(PROJECT_ROOT, f"high_confidence_predictions_{timestamp}.csv")
        df_pred_sorted.to_csv(csv_file, index=False)
        
        print(f"📄 Detailed JSON report saved: {json_file}")
        print(f"📄 CSV export saved: {csv_file}")

def main():
    """Main execution function."""
    analyzer = ConfidenceAnalyzer()
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()