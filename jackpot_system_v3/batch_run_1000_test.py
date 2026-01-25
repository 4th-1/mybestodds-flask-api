"""
Batch runner for 1000 test subscribers with progress tracking and error handling.
Runs all TEST_BOOK3 subscribers and collects results for analysis.
"""
import os
import sys
import json
import time
from datetime import datetime
import subprocess
import glob

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def run_single_kit(subscriber_file):
    """Run a single kit and return success status."""
    try:
        result = subprocess.run([
            sys.executable, "run_kit_v3.py", 
            subscriber_file, "BOOK3"
        ], capture_output=True, text=True, timeout=60)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "subscriber": subscriber_file
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "timeout",
            "subscriber": subscriber_file
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "subscriber": subscriber_file
        }

def main():
    """Run all 1000 test subscribers."""
    print("🚀 Starting batch run of 1000 test subscribers...")
    start_time = datetime.now()
    
    # Find all test subscriber files
    test_files = glob.glob("data/subscribers/TEST_BOOK3/*.json")
    
    if not test_files:
        print("❌ No test subscriber files found. Run generate_1000_test_subscribers.py first.")
        return
    
    print(f"📂 Found {len(test_files)} test subscriber files")
    
    # Create results directory
    results_dir = f"TEST_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(results_dir, exist_ok=True)
    
    # Track results
    results = {
        "start_time": start_time.isoformat(),
        "total_files": len(test_files),
        "successful_runs": 0,
        "failed_runs": 0,
        "errors": [],
        "processing_times": [],
        "results_directory": results_dir
    }
    
    print(f"📊 Results will be saved to {results_dir}/")
    
    # Process each subscriber
    for i, subscriber_file in enumerate(test_files, 1):
        file_start = time.time()
        
        print(f"[{i:4d}/{len(test_files)}] Processing {os.path.basename(subscriber_file)}...", end="", flush=True)
        
        result = run_single_kit(subscriber_file)
        processing_time = time.time() - file_start
        
        if result["success"]:
            results["successful_runs"] += 1
            print(f" ✅ ({processing_time:.1f}s)")
        else:
            results["failed_runs"] += 1
            error_info = {
                "file": subscriber_file,
                "error": result.get("error", "unknown"),
                "stderr": result.get("stderr", ""),
                "processing_time": processing_time
            }
            results["errors"].append(error_info)
            print(f" ❌ ({processing_time:.1f}s) - {result.get('error', 'failed')}")
        
        results["processing_times"].append(processing_time)
        
        # Progress update every 100 files
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / i
            estimated_total = avg_time * len(test_files)
            remaining = estimated_total - elapsed
            
            print(f"\n📈 Progress Update:")
            print(f"   Completed: {i}/{len(test_files)} ({i/len(test_files)*100:.1f}%)")
            print(f"   Success rate: {results['successful_runs']}/{i} ({results['successful_runs']/i*100:.1f}%)")
            print(f"   Average time per kit: {avg_time:.1f}s")
            print(f"   Estimated time remaining: {remaining/60:.1f} minutes")
            print()
    
    # Final statistics
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    results["end_time"] = end_time.isoformat()
    results["total_processing_time_seconds"] = total_time
    results["average_time_per_kit"] = sum(results["processing_times"]) / len(results["processing_times"])
    results["success_rate"] = results["successful_runs"] / results["total_files"] * 100
    
    # Save detailed results
    with open(f"{results_dir}/batch_run_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n🎯 BATCH RUN COMPLETE")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📁 Total files processed: {results['total_files']}")
    print(f"✅ Successful runs: {results['successful_runs']}")
    print(f"❌ Failed runs: {results['failed_runs']}")
    print(f"📊 Success rate: {results['success_rate']:.1f}%")
    print(f"⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"⚡ Average time per kit: {results['average_time_per_kit']:.1f} seconds")
    print(f"💾 Results saved to: {results_dir}/batch_run_results.json")
    
    if results["failed_runs"] > 0:
        print(f"\n❌ Error Summary:")
        error_types = {}
        for error in results["errors"]:
            error_type = error["error"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in error_types.items():
            print(f"   {error_type}: {count} occurrences")
    
    # Find and summarize output files
    output_files = glob.glob("outputs/*.json") + glob.glob("outputs/*.csv")
    if output_files:
        print(f"\n📂 Generated {len(output_files)} output files in outputs/ directory")
    
    print(f"\n🔄 Ready for results analysis!")

if __name__ == "__main__":
    main()