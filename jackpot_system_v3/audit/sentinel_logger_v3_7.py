import os
import csv
from datetime import datetime
from typing import List, Dict

def write_sentinel_rejections(rejected_rows: List[Dict]) -> None:
    """
    Writes rejected Sentinel rows to an audit log with reason codes.
    """
    if not rejected_rows:
        return

    audit_dir = os.path.join("audit", "logs")
    os.makedirs(audit_dir, exist_ok=True)

    filename = f"sentinel_rejections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(audit_dir, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "forecast_date",
                "game_code",
                "number",
                "engine_side",
                "reason_code",
            ],
        )
        writer.writeheader()
        for row in rejected_rows:
            writer.writerow(row)

    print(f"[SENTINEL] Logged {len(rejected_rows)} rejected rows → {path}")
