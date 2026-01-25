"""
Complete 1000 subscriber validation pipeline.
Generates subscribers, runs predictions, and analyzes results in one command.
"""
import os
import sys
import subprocess
import time
from datetime import datetime

def run_command(script_name, description):
    """Run a command and return success status."""
    print(f"\n🚀 {description}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, text=True)
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} completed in {elapsed/60:.1f} minutes")
            return True
        else:
            print(f"❌ {description} failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {description} error after {elapsed/60:.1f} minutes: {e}")
        return False

def main():
    """Run complete validation pipeline."""
    print("🎯 MY BEST ODDS v3.7 - 1000 SUBSCRIBER VALIDATION")
    print("=" * 60)
    print("This will:")
    print("1. Generate 1000 diverse test subscribers")
    print("2. Run predictions for all subscribers")
    print("3. Analyze results against actual winning numbers")
    print("4. Generate comprehensive validation report")
    print()
    
    input("Press Enter to begin validation (this may take 1-2 hours)...")
    
    pipeline_start = datetime.now()
    
    # Step 1: Generate test subscribers
    if not run_command("generate_1000_test_subscribers.py", 
                       "Step 1: Generating 1000 test subscribers"):
        return
    
    # Step 2: Run batch predictions
    if not run_command("batch_run_1000_test.py",
                       "Step 2: Running predictions for 1000 subscribers"):
        return
    
    # Step 3: Analyze results
    if not run_command("analyze_1000_validation.py",
                       "Step 3: Analyzing results against actual winners"):
        return
    
    # Final summary
    total_time = (datetime.now() - pipeline_start).total_seconds()
    
    print(f"\n🎉 VALIDATION PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"⏱️  Total pipeline time: {total_time/60:.1f} minutes")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📂 Check these files for results:")
    print("   • test_1000_subscribers_summary.json - Subscriber generation summary")
    print("   • TEST_RESULTS_*/batch_run_results.json - Batch run results")  
    print("   • VALIDATION_ANALYSIS_*.json - Full validation analysis")
    print("   • outputs/ directory - Individual subscriber predictions")
    print()
    print("🔄 Your system validation is complete!")

if __name__ == "__main__":
    main()