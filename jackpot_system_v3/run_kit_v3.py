# run_kit_v3.py

import sys
import os

# Ensure local project root is in Python's import path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.subscriber_normalizer import normalize_subscriber_files

# Run auto normalization BEFORE anything else
normalize_subscriber_files()

import argparse
from kits.kit_runner import run_30_day_kit

# SMART LOGIC tracking integration
try:
    from smart_logic_tracker_v3_7 import track_kit_execution
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False
    def track_kit_execution(*args, **kwargs):
        pass  # Fallback if tracker not available

def main():
    parser = argparse.ArgumentParser(description="Run Jackpot Engine V3 kit")
    parser.add_argument("subscriber_file", help="JSON file in data/subscribers (e.g. JDS.json)")
    parser.add_argument("kit_name", help="Kit name (e.g. BOSK, BOOK, BOOK3)")
    parser.add_argument("--output", default="outputs", help="Output directory (default: outputs)")
    args = parser.parse_args()

    # Track this kit execution in SMART LOGIC system
    if TRACKING_AVAILABLE:
        track_kit_execution(args.subscriber_file, args.kit_name, args.output)
    
    run_30_day_kit(
        subscriber_file=args.subscriber_file,
        kit_name=args.kit_name,
        output_dir=args.output
    )

if __name__ == "__main__":
    main()
