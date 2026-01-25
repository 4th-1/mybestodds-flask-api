# cleanup_test_outputs.py
"""
Clean up all test outputs to prepare for a fresh 1,500 per KIT run.
This removes:
- All BOOK3_TEST output directories
- All BOOK_TEST output directories  
- All BOSK_TEST output directories
"""

from pathlib import Path
import shutil


def cleanup_test_outputs():
    """Remove all test output directories"""
    outputs_dir = Path('C:/MyBestOdds/jackpot_system_v3/outputs')
    
    if not outputs_dir.exists():
        print(f"Outputs directory doesn't exist: {outputs_dir}")
        return
    
    # Find all test output directories
    book3_dirs = list(outputs_dir.glob('BOOK3_TEST*'))
    book_dirs = list(outputs_dir.glob('BOOK_TEST*'))
    bosk_dirs = list(outputs_dir.glob('BOSK_TEST*'))
    
    total_dirs = book3_dirs + book_dirs + bosk_dirs
    
    print(f"\nFound {len(total_dirs)} test output directories:")
    print(f"  - BOOK3_TEST: {len(book3_dirs)}")
    print(f"  - BOOK_TEST: {len(book_dirs)}")
    print(f"  - BOSK_TEST: {len(bosk_dirs)}")
    
    if not total_dirs:
        print("\nNo test outputs to clean up.")
        return
    
    # Confirm before deleting
    print("\n" + "="*60)
    print("WARNING: This will DELETE all test output directories!")
    print("="*60)
    response = input("\nType 'DELETE' to confirm: ")
    
    if response != "DELETE":
        print("Cleanup cancelled.")
        return
    
    print("\nDeleting directories...")
    deleted = 0
    
    for dir_path in total_dirs:
        try:
            shutil.rmtree(dir_path)
            deleted += 1
            if deleted % 100 == 0:
                print(f"  Deleted {deleted}/{len(total_dirs)}...")
        except Exception as e:
            print(f"  Error deleting {dir_path.name}: {e}")
    
    print(f"\nCleanup complete! Deleted {deleted}/{len(total_dirs)} directories.")


if __name__ == "__main__":
    cleanup_test_outputs()
