#!/usr/bin/env python3
"""
SMART LOGIC Kit Execution Tracker v3.7
=======================================

Tracks every kit execution, subscriber activity, and prediction generation
to provide comprehensive analytics on SMART LOGIC system usage.

INTEGRATES WITH EXISTING AUDIT SYSTEM
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

class SmartLogicTracker:
    """Tracks all SMART LOGIC system executions and usage"""
    
    def __init__(self):
        # Use per-process log file for parallel safety
        self.log_file = os.path.join(
            PROJECT_ROOT, "data",
            f"smart_logic_execution_log_{os.getpid()}.json"
        )
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """Ensure data directory exists for tracking logs"""
        data_dir = os.path.join(PROJECT_ROOT, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def log_kit_execution(self, subscriber_file: str, kit_name: str, output_dir: str = "outputs"):
        """
        Log a kit execution for tracking.
        Called from run_kit_v3.py and other kit runners.
        """
        
        # Extract subscriber info
        subscriber_initials = self._extract_subscriber_initials(subscriber_file)
        
        # Determine date range from output directory naming
        date_range = self._determine_date_range()
        
        # Create execution record
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "subscriber_file": subscriber_file,
            "subscriber_initials": subscriber_initials,
            "kit_name": kit_name,
            "output_directory": output_dir,
            "date_range": date_range,
            "smart_logic_version": "v3.7",
            "execution_type": "individual_kit",
            "system_components": {
                "swiss_ephemeris": True,
                "personalized_scoring": True,
                "mmfsn_integration": True,
                "course_correction": True
            }
        }
        
        # Add to log
        self._append_to_log(execution_record)
        
        try:
            # Print without emoji to avoid UnicodeEncodeError in Windows console
            print(f"SMART LOGIC execution logged: {subscriber_initials} - {kit_name}")
        except UnicodeEncodeError:
            print(f"SMART LOGIC execution logged: {subscriber_initials} - {kit_name}")
        
    def log_batch_execution(self, subscriber_count: int, kit_name: str, description: str = ""):
        """Log batch kit execution (like batch_run_all_book3_with_excel.py)"""
        
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "execution_type": "batch_run",
            "subscriber_count": subscriber_count,
            "kit_name": kit_name,
            "description": description,
            "smart_logic_version": "v3.7",
            "system_components": {
                "swiss_ephemeris": True,
                "personalized_scoring": True,
                "mmfsn_integration": True,
                "course_correction": True
            }
        }
        
        self._append_to_log(execution_record)
        print(f"📝 SMART LOGIC batch execution logged: {subscriber_count} subscribers - {kit_name}")
    
    def get_usage_analytics(self) -> Dict:
        """Get comprehensive SMART LOGIC usage analytics"""
        
        try:
            with open(self.log_file, 'r') as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "total_executions": 0,
                "unique_subscribers": 0,
                "most_active_subscriber": None,
                "kit_usage": {},
                "subscriber_activity": {},
                "daily_activity": {},
                "system_health": {
                    "tracking_active": True,
                    "version": "v3.7", 
                    "features_active": ["Swiss Ephemeris", "Personalized Scoring", "MMFSN Integration", "Course Correction"]
                }
            }
        
        # Analytics calculations
        total_executions = len(log_data)
        
        # Subscriber activity
        subscriber_activity = defaultdict(int)
        kit_usage = defaultdict(int)
        daily_activity = defaultdict(int)
        
        for record in log_data:
            subscriber = record.get('subscriber_initials', 'Unknown')
            kit = record.get('kit_name', 'Unknown')
            date = record.get('timestamp', '')[:10]  # Extract date portion
            
            subscriber_activity[subscriber] += 1
            kit_usage[kit] += 1
            daily_activity[date] += 1
        
        return {
            "total_executions": total_executions,
            "unique_subscribers": len(subscriber_activity),
            "most_active_subscriber": max(subscriber_activity.items(), key=lambda x: x[1]) if subscriber_activity else None,
            "kit_usage": dict(kit_usage),
            "subscriber_activity": dict(subscriber_activity),
            "daily_activity": dict(sorted(daily_activity.items())[-30:]),  # Last 30 days
            "system_health": {
                "tracking_active": True,
                "version": "v3.7",
                "features_active": ["Swiss Ephemeris", "Personalized Scoring", "MMFSN Integration", "Course Correction"]
            }
        }
    
    def generate_usage_report(self) -> str:
        """Generate comprehensive SMART LOGIC usage report"""
        
        analytics = self.get_usage_analytics()
        
        report_lines = [
            "=" * 80,
            "🎯 SMART LOGIC SYSTEM USAGE REPORT",
            "=" * 80,
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"System Version: v3.7 - Adaptive Learning Engine",
            "",
            "📊 USAGE STATISTICS:",
            f"   Total Kit Executions: {analytics['total_executions']}",
            f"   Active Subscribers: {analytics['unique_subscribers']}",
            ""
        ]
        
        # Most active subscriber
        if analytics['most_active_subscriber']:
            subscriber, count = analytics['most_active_subscriber']
            report_lines.append(f"🏆 Most Active User: {subscriber} ({count} executions)")
            report_lines.append("")
        
        # Kit usage breakdown
        if analytics['kit_usage']:
            report_lines.append("📋 KIT USAGE BREAKDOWN:")
            for kit, count in sorted(analytics['kit_usage'].items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"   {kit}: {count} executions")
            report_lines.append("")
        
        # Subscriber activity
        if analytics['subscriber_activity']:
            report_lines.append("👥 SUBSCRIBER ACTIVITY (Top 10):")
            sorted_subscribers = sorted(analytics['subscriber_activity'].items(), key=lambda x: x[1], reverse=True)
            for subscriber, count in sorted_subscribers[:10]:
                report_lines.append(f"   {subscriber}: {count} kit runs")
            report_lines.append("")
        
        # System status
        report_lines.extend([
            "🚀 SYSTEM STATUS:",
            f"   Tracking: {'✅ Active' if analytics['system_health']['tracking_active'] else '❌ Inactive'}",
            f"   Version: {analytics['system_health']['version']}",
            "   Active Features:",
        ])
        
        for feature in analytics['system_health']['features_active']:
            report_lines.append(f"     ✅ {feature}")
        
        report_lines.extend([
            "",
            "📈 SMART LOGIC SYSTEM INSIGHTS:",
            "   • Each kit execution is automatically tracked",
            "   • System learns from every prediction and result",
            "   • Personalized scoring adapts to individual subscribers",
            "   • MMFSN weights adjust based on performance",
            "   • Comprehensive analytics enable system optimization"
        ])
        
        return "\n".join(report_lines)
    
    def _extract_subscriber_initials(self, subscriber_file: str) -> str:
        """Extract subscriber initials from file path"""
        
        # Handle various path formats
        if '/' in subscriber_file:
            filename = subscriber_file.split('/')[-1]
        elif '\\' in subscriber_file:
            filename = subscriber_file.split('\\')[-1]
        else:
            filename = subscriber_file
        
        # Remove extension and extract initials
        base_name = filename.replace('.json', '')
        
        # Common patterns: "JDS_BOOK3", "AJS_BOOK3", "Joseph_Smith", etc.
        if '_' in base_name:
            return base_name.split('_')[0]
        
        return base_name
    
    def _determine_date_range(self) -> str:
        """Determine date range for current execution"""
        # Could be enhanced to read from config or parameters
        # For now, return current date range format
        today = datetime.now()
        end_date = today.replace(day=31) if today.month == 12 else today
        return f"{today.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}"
    
    def _append_to_log(self, record: Dict):
        """Append record to execution log"""
        
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = []
            
            log_data.append(record)
            
            # Keep only last 2000 records to prevent file bloat
            if len(log_data) > 2000:
                log_data = log_data[-2000:]
            
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Could not save execution log: {e}")

# Global tracker instance
smart_logic_tracker = SmartLogicTracker()

def track_kit_execution(subscriber_file: str, kit_name: str, output_dir: str = "outputs"):
    """Convenience function to track kit execution"""
    smart_logic_tracker.log_kit_execution(subscriber_file, kit_name, output_dir)

def track_batch_execution(subscriber_count: int, kit_name: str, description: str = ""):
    """Convenience function to track batch execution"""
    smart_logic_tracker.log_batch_execution(subscriber_count, kit_name, description)

def generate_analytics_report():
    """Generate and print analytics report"""
    report = smart_logic_tracker.generate_usage_report()
    print(report)
    
    # Save to file
    report_file = os.path.join(PROJECT_ROOT, "outputs", f"smart_logic_usage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    try:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📋 Full report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️ Could not save report file: {e}")

if __name__ == "__main__":
    # Generate usage report
    generate_analytics_report()