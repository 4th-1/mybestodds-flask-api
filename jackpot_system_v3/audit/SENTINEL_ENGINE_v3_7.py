import os
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------
# SENTINEL v3.7 (Option B Mode)
# Auto-repair safe issues + Fail critical
# ---------------------------------------

REQUIRED_GA_COLUMNS = [
    "draw_date", "draw_time", "result", "sum", "type"
]

REQUIRED_JACKPOT_COLUMNS = [
    "draw_date", "w1", "w2", "w3", "w4", "w5",
    "special", "jackpot"
]

GA_FOLDER = "data/results/ga_results/"
JACKPOT_FOLDER = "data/results/jackpot_results/"
REPORT_PATH = "output/sentinel/sentinel_report.json"


def log(msg):
    print(f"[SENTINEL] {msg}")


def ensure_output_folder():
    folder = os.path.dirname(REPORT_PATH)
    if not os.path.exists(folder):
        os.makedirs(folder)


def validate_columns(df, required_cols, filename, issues, critical_issues):
    """Check for required columns and enforce correct schema."""
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        critical_issues.append({
            "file": filename,
            "error": f"Missing columns: {missing}"
        })
        return False
    return True


def detect_duplicates(df, filename, issues, critical_issues):
    """Detect duplicate draw_date rows."""
    if "draw_date" not in df.columns:
        return

    duplicates = df[df.duplicated("draw_date", keep=False)]
    if len(duplicates) > 0:
        critical_issues.append({
            "file": filename,
            "error": "Duplicate draw_date entries detected",
            "rows": duplicates.to_dict(orient="records")
        })


def detect_malformed_values(df, filename, issues, critical_issues):
    """Check number formatting for Cash3, Cash4, and jackpot values."""
    
    for idx, row in df.iterrows():
        try:
            date_ok = datetime.strptime(str(row["draw_date"]), "%Y-%m-%d")
        except:
            critical_issues.append({
                "file": filename,
                "row": idx,
                "error": f"Malformed draw_date: {row['draw_date']}"
            })

        if "result" in df.columns:
            # Cash3 should be length 3, Cash4 length 4
            r = str(row["result"]).strip()
            if not r.isdigit():
                critical_issues.append({
                    "file": filename,
                    "row": idx,
                    "error": f"Non-numeric result: {row['result']}"
                })
            if len(r) not in (3, 4):
                critical_issues.append({
                    "file": filename,
                    "row": idx,
                    "error": f"Unexpected result length: {r}"
                })

        if "jackpot" in df.columns:
            try:
                _ = float(row["jackpot"])
            except:
                critical_issues.append({
                    "file": filename,
                    "row": idx,
                    "error": f"Malformed jackpot value: {row['jackpot']}"
                })


def auto_repair(df, filename, issues):
    """Perform safe auto-repair actions (Option B)."""

    repaired = []

    # Trim whitespace
    for col in df.columns:
        if df[col].dtype == object:
            new_series = df[col].astype(str).str.strip()
            if not new_series.equals(df[col]):
                df[col] = new_series
                repaired.append(f"Trimmed whitespace in column {col}")

    # Normalize draw_time (Midday, Mid, Evening, Night)
    if "draw_time" in df.columns:
        df["draw_time"] = df["draw_time"].str.lower().replace({
            "mid": "midday",
            "mid day": "midday",
            "night": "evening"
        })

        repaired.append("Normalized draw_time values")

    if repaired:
        issues.append({
            "file": filename,
            "auto_repairs": repaired
        })

    return df


def process_folder(folder, required_cols):
    """Process all CSVs in a folder."""
    issues = []
    critical_issues = []
    processed_files = []

    for file in os.listdir(folder):
        if not file.endswith(".csv"):
            continue

        filepath = os.path.join(folder, file)
        df = pd.read_csv(filepath)

        processed_files.append(file)

        # Column validation
        if not validate_columns(df, required_cols, file, issues, critical_issues):
            continue

        # Auto-repair
        df = auto_repair(df, file, issues)

        # Duplicates
        detect_duplicates(df, file, issues, critical_issues)

        # Malformed values
        detect_malformed_values(df, file, issues, critical_issues)

        # Save repaired version (safe changes only)
        df.to_csv(filepath, index=False)

    return processed_files, issues, critical_issues


def run_sentinel():
    ensure_output_folder()

    log("Starting Sentinel v3.7 (Option B Mode)...")

    ga_files, ga_issues, ga_critical = process_folder(GA_FOLDER, REQUIRED_GA_COLUMNS)
    jackpot_files, jp_issues, jp_critical = process_folder(JACKPOT_FOLDER, REQUIRED_JACKPOT_COLUMNS)

    all_issues = ga_issues + jp_issues
    all_critical = ga_critical + jp_critical

    status = "FAIL" if len(all_critical) > 0 else "PASS"

    report = {
        "timestamp": str(datetime.now()),
        "status": status,
        "ga_files_checked": ga_files,
        "jackpot_files_checked": jackpot_files,
        "issues": all_issues,
        "critical_issues": all_critical
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=4)

    if status == "FAIL":
        log("❌ Sentinel FAILED — critical issues detected. See sentinel_report.json.")
    else:
        log("✅ Sentinel PASS — data integrity confirmed.")

    return status


if __name__ == "__main__":
    run_sentinel()
