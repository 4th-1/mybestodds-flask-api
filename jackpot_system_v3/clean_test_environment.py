import shutil
from pathlib import Path

# Clean up all test outputs and forecast.csv files for a fresh run
def clean_outputs():
    outputs_dir = Path('C:/MyBestOdds/jackpot_system_v3/outputs')
    if outputs_dir.exists():
        for d in outputs_dir.iterdir():
            if d.is_dir() and ("BOOK3_TEST" in d.name or "BOOK_TEST" in d.name or "BOSK_TEST" in d.name):
                shutil.rmtree(d)
    print("All test output directories removed.")

def clean_subscribers():
    subs_dir = Path('C:/MyBestOdds/jackpot_system_v3/data/subscribers')
    for kit in ["BOOK3_TEST", "BOOK_TEST", "BOSK_TEST"]:
        kit_dir = subs_dir / kit
        if kit_dir.exists():
            for f in kit_dir.glob("*.json"):
                f.unlink()
    print("All test subscriber files removed.")

if __name__ == "__main__":
    clean_outputs()
    clean_subscribers()
    print("Test environment cleaned. Ready for fresh generation.")
