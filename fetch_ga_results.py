"""
fetch_ga_results.py
===================
Fetches the latest Georgia Lottery Cash3 and Cash4 draw results from
lotterypost.com and ingests them via the local /api/results/ingest endpoint.

galottery.com was fully migrated to a JS-rendered SPA (as of early 2026) and
is no longer scraped. lotterypost.com returns server-rendered HTML with all GA
results on a single page.

Usage (standalone):
    python fetch_ga_results.py [--dry-run] [--ingest-url URL]

Usage (called from Flask endpoint /api/results/fetch-latest):
    results = fetch_and_ingest(ingest_url, secret, dry_run=False)

Draw schedule (Eastern Time):
    Midday : 12:29 PM  → fetch at 12:45 PM
    Evening:  6:59 PM  → fetch at  7:15 PM
    Night  : 11:34 PM  → fetch at 11:50 PM

Cron trigger (cron-job.org, free):
    GET https://mybestodds-flask-api-production.up.railway.app/api/results/fetch-latest
    Schedule: 3× daily at 12:45, 19:15, 23:50 ET
"""

import argparse
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests

# ── Constants ─────────────────────────────────────────────────────────────────

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

_LP_URL = "https://www.lotterypost.com/results/ga"

# lotterypost.com assigns stable data-id values to each GA draw session.
# Confirmed 2026-04-28 by parsing /results/ga HTML.
_DRAW_SESSIONS = [
    {"data_id": "42",  "game": "Cash3", "session": "midday"},
    {"data_id": "38",  "game": "Cash3", "session": "evening"},
    {"data_id": "510", "game": "Cash3", "session": "night"},
    {"data_id": "43",  "game": "Cash4", "session": "midday"},
    {"data_id": "511", "game": "Cash4", "session": "evening"},
    {"data_id": "39",  "game": "Cash4", "session": "night"},
]

# Eastern Time offset (UTC-5; DST not required for cron-fire accuracy)
_ET = timezone(timedelta(hours=-5))


# ── Fetcher ───────────────────────────────────────────────────────────────────

def _fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a page with browser headers. Returns HTML or None on failure."""
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        print(f"[fetch] HTTP {resp.status_code} for {url}", file=sys.stderr)
        return None
    except requests.RequestException as e:
        print(f"[fetch] Request failed: {e}", file=sys.stderr)
        return None


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_lotterypost(html: str) -> List[Dict]:
    """
    Parse lotterypost.com/results/ga HTML and return one dict per draw session.

    HTML structure (confirmed 2026-04-28):
        <h2 data-id="42">Cash 3 Midday</h2>
        <time datetime="2026-04-28T12:29-05:00">...</time>
        <ul class="resultsnums"><li>1</li><li>0</li><li>1</li></ul>

    Returns list of:
        {"game": "Cash3", "session": "midday", "date": "2026-04-28", "winning_number": "101"}
    """
    results = []

    for draw in _DRAW_SESSIONS:
        did = draw["data_id"]

        # Locate the <section> block that starts with the known data-id heading.
        # Use a non-greedy match to stay within the section for this draw only.
        section_m = re.search(
            r'<h2\s+data-id="' + re.escape(did) + r'">[^<]+</h2>'
            r'(.*?)'
            r'(?:<h2\s+data-id="|</div>\s*</div>\s*</div>\s*<div\s+class="resultsdrawing">|<div\s+class="resultsbuttonrow">)',
            html,
            re.DOTALL,
        )
        if not section_m:
            print(f"[parse] data-id={did} ({draw['game']} {draw['session']}) not found", file=sys.stderr)
            continue

        block = section_m.group(1)

        # Extract draw date from <time datetime="YYYY-MM-DDThh:mm±hh:mm">
        date_m = re.search(r'<time\s+datetime="(\d{4}-\d{2}-\d{2})T[^"]*"', block)
        if not date_m:
            print(f"[parse] No <time> for data-id={did}", file=sys.stderr)
            continue
        draw_date = date_m.group(1)

        # Extract digits from <ul class="resultsnums"><li>D</li>...</ul>
        nums_m = re.search(r'<ul\s+class="resultsnums">(.*?)</ul>', block, re.DOTALL)
        if not nums_m:
            print(f"[parse] No resultsnums for data-id={did}", file=sys.stderr)
            continue
        digits = re.findall(r'<li>(\d)</li>', nums_m.group(1))

        expected = 4 if draw["game"] == "Cash4" else 3
        if len(digits) != expected:
            print(f"[parse] data-id={did}: expected {expected} digits, got {digits}", file=sys.stderr)
            continue

        results.append({
            "game":           draw["game"],
            "session":        draw["session"],
            "date":           draw_date,
            "winning_number": "".join(digits),
        })
        print(f"[parse] {draw['game']} {draw['session']} {draw_date} -> {''.join(digits)}")

    return results


def fetch_latest_results() -> Dict[str, List[Dict]]:
    """
    Fetch today's (and most-recent) Cash3 and Cash4 results from lotterypost.com.
    Returns {"cash3": [...], "cash4": [...]}
    """
    print(f"[fetch] Fetching {_LP_URL}")
    html = _fetch_page(_LP_URL)
    if not html:
        print("[fetch] No HTML returned", file=sys.stderr)
        return {"cash3": [], "cash4": []}

    all_rows = _parse_lotterypost(html)

    cash3 = [r for r in all_rows if r["game"] == "Cash3"]
    cash4 = [r for r in all_rows if r["game"] == "Cash4"]
    print(f"[fetch] Parsed {len(cash3)} Cash3, {len(cash4)} Cash4 results")
    return {"cash3": cash3, "cash4": cash4}


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest_results(
    results: Dict[str, List[Dict]],
    ingest_url: str,
    secret: str,
    dry_run: bool = False,
) -> List[Dict]:
    """
    POST each result row to /api/results/ingest.
    Returns list of ingest response dicts.
    """
    responses = []
    headers = {
        "Content-Type": "application/json",
        "X-Prediction-Secret": secret,
    }

    for game_key, rows in results.items():
        for row in rows:
            game_name = "Cash3" if game_key == "cash3" else "Cash4"
            payload = {
                "game":           game_name,
                "session":        row.get("session", ""),
                "date":           row.get("date", ""),
                "winning_number": row.get("winning_number", ""),
                "dryRun":         dry_run,
            }
            try:
                resp = requests.post(ingest_url, json=payload, headers=headers, timeout=10)
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
                data["_status_code"] = resp.status_code
                data["_payload"] = payload
                responses.append(data)
                status = "DRY-RUN" if dry_run else ("OK" if resp.status_code == 200 else "FAIL")
                print(f"[ingest] {status} {game_name} {row.get('session')} {row.get('date')} -> {row.get('winning_number')}")
            except requests.RequestException as e:
                err = {"error": str(e), "_payload": payload}
                responses.append(err)
                print(f"[ingest] ERROR {game_name}: {e}", file=sys.stderr)

    return responses


def fetch_and_ingest(
    ingest_url: str,
    secret: str,
    dry_run: bool = False,
) -> Dict:
    """
    Full pipeline: fetch galottery.com → parse → ingest.
    Called from the Flask /api/results/fetch-latest endpoint.
    """
    results   = fetch_latest_results()
    total     = sum(len(v) for v in results.values())
    responses = ingest_results(results, ingest_url, secret, dry_run=dry_run)
    successes = sum(1 for r in responses if r.get("success") or r.get("dryRun"))

    return {
        "fetched":   total,
        "ingested":  successes,
        "dry_run":   dry_run,
        "cash3_count": len(results["cash3"]),
        "cash4_count": len(results["cash4"]),
        "detail":    responses,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and ingest GA Lottery results")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    parser.add_argument("--ingest-url", default="http://localhost:5000/api/results/ingest",
                        help="Ingest endpoint URL")
    parser.add_argument("--secret", default="", help="X-Prediction-Secret header value")
    args = parser.parse_args()

    result = fetch_and_ingest(args.ingest_url, args.secret, dry_run=args.dry_run)
    print(f"\nSummary: fetched={result['fetched']} ingested={result['ingested']} dry_run={result['dry_run']}")
