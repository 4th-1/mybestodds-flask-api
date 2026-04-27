"""
fetch_ga_results.py
===================
Fetches the latest Georgia Lottery Cash3 and Cash4 draw results from
galottery.com and ingests them via the local /api/results/ingest endpoint.

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

# Headers that mimic a real browser so galottery.com returns HTML instead of
# redirecting to an ad-sync pixel.
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

_GA_LOTTERY_BASE = "https://www.galottery.com"

# Maps session label text → ingest API session value
_SESSION_LABELS = {
    "midday":  "midday",
    "mid":     "midday",
    "evening": "evening",
    "eve":     "evening",
    "night":   "night",
}

# Eastern Time offset (UTC-5, no DST handling needed for cron accuracy)
_ET = timezone(timedelta(hours=-5))


# ── GA Lottery HTML Fetcher ───────────────────────────────────────────────────

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


def _extract_digits_from_span(html_block: str) -> str:
    """Extract individual digit <span> values from a result block and join them."""
    # GA Lottery renders each digit in its own element, e.g.:
    # <span class="winningNumber">4</span>
    # <li class="ball">7</li>
    # Various class names across page versions — capture all single-digit elements
    digits = re.findall(
        r'<(?:span|li|div)[^>]*class=["\'][^"\']*(?:winning.?number|ball|digit|number)[^"\']*["\'][^>]*>\s*(\d)\s*</(?:span|li|div)>',
        html_block,
        re.IGNORECASE,
    )
    return "".join(digits)


def _parse_galottery_page(html: str, game: str) -> List[Dict]:
    """
    Parse galottery.com winning-numbers page for a specific game.

    Returns list of dicts:
        {"game": "Cash3", "session": "midday", "date": "2026-04-27", "winning_number": "184"}
    """
    game_key = game.lower().replace(" ", "")  # "cash3" or "cash4"
    results = []

    # --- Strategy 1: structured JSON-LD or data attributes ------------------
    # GA Lottery sometimes embeds draw data in JSON-LD scripts
    json_blocks = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    # (Parse attempts omitted — JSON-LD on galottery.com doesn't include draw numbers)

    # --- Strategy 2: HTML section parsing -----------------------------------
    # Look for game sections: find blocks containing the game name heading
    # then pull date, session, and digit elements from within each block.

    # Normalize game name for matching
    game_display = "Cash 3" if game_key == "cash3" else "Cash 4"
    alt_display  = game_key.replace("cash", "Cash ").strip()  # fallback

    # Split page into candidate result rows by known section patterns.
    # GA Lottery uses divs/li items per draw; we look for date + session context.
    draw_pattern = re.compile(
        r'(\d{1,2}/\d{1,2}/\d{4}|\w+ \d{1,2},?\s*\d{4})'   # date
        r'.*?'
        r'(midday|evening|night|mid)'                          # session
        r'.*?'
        r'(?:'
            r'(?:<[^>]+class=["\'][^"\']*(?:winning.?number|ball|digit)[^"\']*["\'][^>]*>\s*(\d)\s*</[^>]+>\s*){3,4}'  # digit spans
        r')',
        re.IGNORECASE | re.DOTALL,
    )

    # --- Strategy 3: Line-by-line reconstruction (most robust) --------------
    # Walk through all text nodes: collect (date, session, number) triples
    # by tracking context across lines.

    lines = html.split("\n")
    current_date  = None
    current_session = None
    digit_buffer: List[str] = []
    date_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2})'                          # YYYY-MM-DD
        r'|(\w+,?\s+\w+\s+\d{1,2},?\s*\d{4})'          # "Sunday, April 26, 2026"
        r'|(\d{1,2}/\d{1,2}/\d{4})'                     # M/D/YYYY
    )
    session_pattern = re.compile(r'\b(midday|mid|evening|eve|night)\b', re.IGNORECASE)
    single_digit    = re.compile(r'^\s*(\d)\s*$')

    # Also parse the page for game-section boundaries so we only collect digits
    # inside the right game section.
    inside_game_section = False
    # Simple check: if the page is a single-game page (URL contained game name), always inside
    inside_game_section = True  # We fetch per-game URL, so all results are for this game

    def _normalise_date(raw: str) -> Optional[str]:
        raw = raw.strip().rstrip(",")
        for fmt in (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%B %d %Y",   # "April 26 2026"
            "%B %d, %Y",  # "April 26, 2026"
            "%A, %B %d, %Y",  # "Sunday, April 26, 2026"
            "%A %B %d %Y",
        ):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    prev_line = ""
    for line in lines:
        stripped = line.strip()

        # Date detection
        dm = date_pattern.search(stripped)
        if dm:
            raw = dm.group(1) or dm.group(2) or dm.group(3) or ""
            # Clean up "Sunday, April 26, 2026" style
            raw = re.sub(r'^[A-Za-z]+,?\s*', '', raw).strip()
            nd = _normalise_date(raw) or _normalise_date(stripped)
            if nd:
                # Flush any pending record before moving to new date
                if current_date and current_session and len(digit_buffer) >= 3:
                    num = "".join(digit_buffer[:4 if game_key == "cash4" else 3])
                    if len(num) in (3, 4):
                        results.append({
                            "game":           game_display.replace(" ", ""),
                            "session":        _SESSION_LABELS.get(current_session.lower(), current_session.lower()),
                            "date":           current_date,
                            "winning_number": num,
                        })
                current_date = nd
                current_session = None
                digit_buffer = []

        # Session detection
        sm = session_pattern.search(stripped)
        if sm and current_date:
            sess = sm.group(1).lower()
            if sess != current_session:
                # Flush pending
                if current_session and len(digit_buffer) >= 3:
                    num = "".join(digit_buffer[:4 if game_key == "cash4" else 3])
                    if len(num) in (3, 4):
                        results.append({
                            "game":           game_display.replace(" ", ""),
                            "session":        _SESSION_LABELS.get(current_session.lower(), current_session.lower()),
                            "date":           current_date,
                            "winning_number": num,
                        })
                current_session = sess
                digit_buffer = []

        # Digit detection — raw text content of digit elements
        dm2 = single_digit.match(stripped)
        if dm2 and current_date and current_session:
            digit_buffer.append(dm2.group(1))
            expected = 4 if game_key == "cash4" else 3
            if len(digit_buffer) == expected:
                num = "".join(digit_buffer)
                results.append({
                    "game":           game_display.replace(" ", ""),
                    "session":        _SESSION_LABELS.get(current_session.lower(), current_session.lower()),
                    "date":           current_date,
                    "winning_number": num,
                })
                digit_buffer = []
                current_session = None  # consumed — wait for next session marker

        prev_line = stripped

    return results


def fetch_latest_results() -> Dict[str, List[Dict]]:
    """
    Fetch today's (and yesterday's) Cash3 and Cash4 results from galottery.com.
    Returns {"cash3": [...], "cash4": [...]}
    """
    urls = {
        "cash3": f"{_GA_LOTTERY_BASE}/en-us/results/winning-numbers/cash-3.html",
        "cash4": f"{_GA_LOTTERY_BASE}/en-us/results/winning-numbers/cash-4.html",
    }

    all_results: Dict[str, List[Dict]] = {"cash3": [], "cash4": []}

    for game_key, url in urls.items():
        print(f"[fetch] Fetching {url}")
        html = _fetch_page(url)
        if not html:
            print(f"[fetch] No HTML returned for {game_key}", file=sys.stderr)
            continue
        parsed = _parse_galottery_page(html, game_key)
        all_results[game_key] = parsed
        print(f"[fetch] Parsed {len(parsed)} {game_key} results")

    return all_results


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
                print(f"[ingest] {status} {game_name} {row.get('session')} {row.get('date')} → {row.get('winning_number')}")
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
