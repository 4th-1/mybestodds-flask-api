"""
backfill_ga_results.py
======================
Fetches recent Cash3 and Cash4 results from lotterypost.com past results
pages and ingests any missing draws into the live Railway API.

Covers approximately the last 20 days (all sessions available on the page).
Safe to run multiple times — ingest is idempotent.

Usage:
    python backfill_ga_results.py [--dry-run]

Required env var (or pass via --secret):
    PREDICTIONS_API_SECRET
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

INGEST_URL = "https://mybestodds-flask-api-production.up.railway.app/api/results/ingest"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# lotterypost.com past results URLs
_PAST_URLS = {
    "Cash3": "https://www.lotterypost.com/results/ga/cash3/past",
    "Cash4": "https://www.lotterypost.com/results/ga/cash4/past",
}

# Session label text → ingest API value
_SESSION_MAP = {
    "midday":  "midday",
    "evening": "evening",
    "night":   "night",
}


# ── Fetch ──────────────────────────────────────────────────────────────────────

def _fetch(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=20, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        print(f"[fetch] HTTP {resp.status_code} for {url}", file=sys.stderr)
    except requests.RequestException as e:
        print(f"[fetch] {e}", file=sys.stderr)
    return None


# ── Parser ─────────────────────────────────────────────────────────────────────

def _parse_past_results(html: str, game: str) -> List[Dict]:
    """
    Parse lotterypost.com/results/ga/{cash3|cash4}/past HTML.

    Page structure (per day group):
      <div class="resultsgame">
        <div class="resultscontent nologo">
          <!-- First draw of the day has a <time> element -->
          <div class="resultsdrawing horiz">
            <time datetime="2026-04-27T12:29-05:00">...</time>
            <div class="drawWrap withTOD">
              <div class="TOD"><i class="TODmid"></i><br />Midday</div>
              <ul class="resultsnums"><li>7</li><li>4</li><li>0</li></ul>
            </div>
          </div>
          <!-- Evening / Night share the same day — no <time> here -->
          <div class="resultsdrawing horiz">
            <div class="drawWrap withTOD">
              <div class="TOD"><i class="TODeve"></i><br />Evening</div>
              <ul class="resultsnums">...</ul>
            </div>
          </div>
        </div>
      </div>

    Strategy: walk "resultsdrawing horiz" blocks; update current_date whenever
    a <time datetime="YYYY-MM-DD..."> is found; extract TOD text for session.
    """
    results = []
    expected_digits = 4 if game == "Cash4" else 3

    # Split on each draw block
    draw_blocks = re.split(r'(?=<div\s+class="resultsdrawing\s+horiz">)', html)

    current_date: Optional[str] = None

    for block in draw_blocks:
        # Update date if this block has a <time> element
        date_m = re.search(r'<time\s+datetime="(\d{4}-\d{2}-\d{2})T', block)
        if date_m:
            current_date = date_m.group(1)

        if not current_date:
            continue

        # Extract session from TOD text: Midday / Evening / Night
        tod_m = re.search(r'<div\s+class="TOD">.*?<br\s*/?>([^<]+)', block, re.DOTALL)
        if not tod_m:
            continue
        session_text = tod_m.group(1).strip().lower()
        session = _SESSION_MAP.get(session_text)
        if not session:
            continue

        # Extract digits
        nums_m = re.search(r'<ul\s+class="resultsnums">(.*?)</ul>', block, re.DOTALL)
        if not nums_m:
            continue
        digits = re.findall(r'<li>(\d)</li>', nums_m.group(1))
        if len(digits) != expected_digits:
            continue

        results.append({
            "game":           game,
            "session":        session,
            "date":           current_date,
            "winning_number": "".join(digits),
        })

    return results


# ── Ingest ─────────────────────────────────────────────────────────────────────

def _ingest_row(row: Dict, secret: str, dry_run: bool) -> Dict:
    headers = {
        "Content-Type":        "application/json",
        "X-Prediction-Secret": secret,
    }
    payload = {
        "game":           row["game"],
        "session":        row["session"],
        "date":           row["date"],
        "winning_number": row["winning_number"],
        "dryRun":         dry_run,
    }
    try:
        resp = requests.post(INGEST_URL, json=payload, headers=headers, timeout=12)
        data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
        data["_http"] = resp.status_code
        data["_row"]  = row
        return data
    except requests.RequestException as e:
        return {"error": str(e), "_row": row}


# ── Main ───────────────────────────────────────────────────────────────────────

def run(secret: str, dry_run: bool = False) -> None:
    total_fetched = 0
    total_wrote = 0
    total_skip = 0
    total_err = 0

    for game, url in _PAST_URLS.items():
        print(f"\n[backfill] Fetching {game} past results …")
        html = _fetch(url)
        if not html:
            print(f"[backfill] SKIP {game} — no HTML")
            continue

        rows = _parse_past_results(html, game)
        print(f"[backfill] Parsed {len(rows)} {game} draws")
        total_fetched += len(rows)

        for row in rows:
            result = _ingest_row(row, secret, dry_run)
            http   = result.get("_http", 0)
            label  = f"{row['game']} {row['session']:7s} {row['date']} → {row['winning_number']}"

            if result.get("error"):
                print(f"  ERROR   {label} : {result['error']}", file=sys.stderr)
                total_err += 1
            elif http == 403:
                print(f"  AUTH    {label} : 403 Unauthorized", file=sys.stderr)
                total_err += 1
            elif result.get("already_present") or not result.get("would_write", True):
                print(f"  SKIP    {label} (already present)")
                total_skip += 1
            elif dry_run:
                print(f"  DRY-RUN {label} (would_write={result.get('would_write')})")
                total_wrote += 1
            elif result.get("success"):
                print(f"  OK      {label}")
                total_wrote += 1
            else:
                print(f"  FAIL    {label} : http={http} {result}", file=sys.stderr)
                total_err += 1

    mode = "dry-run" if dry_run else "live"
    print(f"\n[backfill] {mode} done — fetched={total_fetched} wrote={total_wrote} skip={total_skip} err={total_err}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill GA Lottery missing draws")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--secret",  default=os.environ.get("PREDICTIONS_API_SECRET", ""),
                        help="X-Prediction-Secret value")
    args = parser.parse_args()

    if not args.secret:
        print("ERROR: --secret or PREDICTIONS_API_SECRET env var required", file=sys.stderr)
        sys.exit(1)

    run(args.secret, dry_run=args.dry_run)
