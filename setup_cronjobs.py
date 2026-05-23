"""
setup_cronjobs.py — Configure cron-job.org jobs for the EV observation window.

Creates 3 daily jobs that call the ev-observe-cron endpoint before each GA
Cash3 draw.  Run this once after getting your cron-job.org API key.

Usage:
    python setup_cronjobs.py --api-key YOUR_CRONJOB_ORG_KEY

Get your API key from: https://cron-job.org/en/ → Account → API

Jobs created:
    11:30 AM ET — MIDDAY  (before 12:29 PM draw)
    6:30  PM ET — EVENING (before 6:59 PM draw)
    11:00 PM ET — NIGHT   (before 11:34 PM draw)

All times are Eastern (UTC-4 during May–June EDT).
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config — edit if Railway URL or secret ever changes
# ---------------------------------------------------------------------------
API_BASE_URL   = "https://mybestodds-flask-api-production.up.railway.app"
PREDICT_SECRET = "EOl1gIdvZRUjKu8ReGtCixtr5BiLJThbaTyXefCvIzs"
CRONJOB_API    = "https://api.cron-job.org"

# Each job: (label, session_param, hour_utc, minute_utc)
# ET (EDT, UTC-4): 11:30 AM → 15:30 UTC, 6:30 PM → 22:30 UTC, 11:00 PM → 03:00 UTC
JOBS = [
    ("MBO - Cash3 MIDDAY observe",   "MIDDAY",  15, 30),
    ("MBO - Cash3 EVENING observe",  "EVENING", 22, 30),
    ("MBO - Cash3 NIGHT observe",    "NIGHT",    3,  0),
]

# ---------------------------------------------------------------------------


def _cronjob_request(method: str, path: str, api_key: str, body=None) -> dict:
    url  = CRONJOB_API + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from cron-job.org: {body_text}") from e


def list_jobs(api_key: str) -> list:
    return _cronjob_request("GET", "/jobs", api_key).get("jobs", [])


def create_job(api_key: str, title: str, session: str, hour: int, minute: int) -> dict:
    url = f"{API_BASE_URL}/api/admin/ev-observe-cron?session={session}"
    payload = {
        "job": {
            "url":           url,
            "title":         title,
            "enabled":       True,
            "saveResponses": True,
            "requestMethod": 0,          # GET
            "schedule": {
                "timezone": "America/New_York",
                "hours":    [hour],
                "minutes":  [minute],
                "mdays":    [-1],        # every day of month
                "months":   [-1],        # every month
                "wdays":    [-1],        # every weekday
            },
            "extendedData": {
                "headers": [
                    {
                        "name":  "X-Prediction-Secret",
                        "value": PREDICT_SECRET,
                    }
                ]
            },
        }
    }
    return _cronjob_request("PUT", "/jobs", api_key, payload)


def delete_job(api_key: str, job_id: int) -> dict:
    return _cronjob_request("DELETE", f"/jobs/{job_id}", api_key)


def main():
    parser = argparse.ArgumentParser(description="Setup cron-job.org jobs for MBO EV observation")
    parser.add_argument("--api-key",  required=True, help="cron-job.org API Bearer token")
    parser.add_argument("--list",     action="store_true", help="List existing jobs and exit")
    parser.add_argument("--teardown", action="store_true", help="Delete all MBO jobs and exit")
    args = parser.parse_args()

    # ── List mode ──────────────────────────────────────────────────────────
    if args.list:
        jobs = list_jobs(args.api_key)
        if not jobs:
            print("No jobs found.")
        for j in jobs:
            print(f"  [{j['jobId']}] {j.get('title', '(untitled)')}  enabled={j.get('enabled')}  url={j.get('url')}")
        return

    # ── Teardown mode ──────────────────────────────────────────────────────
    if args.teardown:
        jobs = list_jobs(args.api_key)
        mbo_jobs = [j for j in jobs if "MBO" in (j.get("title") or "")]
        if not mbo_jobs:
            print("No MBO jobs found to delete.")
            return
        for j in mbo_jobs:
            delete_job(args.api_key, j["jobId"])
            print(f"  Deleted [{j['jobId']}] {j.get('title')}")
        return

    # ── Create mode (default) ──────────────────────────────────────────────
    # Check for duplicates first
    existing = list_jobs(args.api_key)
    existing_titles = {j.get("title") for j in existing}

    for title, session, hour, minute in JOBS:
        if title in existing_titles:
            print(f"  SKIP (already exists): {title}")
            continue
        result = create_job(args.api_key, title, session, hour, minute)
        job_id = result.get("jobId") or result.get("job", {}).get("jobId", "?")
        print(f"  CREATED [{job_id}]: {title}  ({hour:02d}:{minute:02d} UTC / {session})")

    print()
    print("Done. Jobs will fire daily. Verify at https://cron-job.org/en/members/jobs/")
    print()
    print("To verify the endpoint manually:")
    print(f"  Invoke-WebRequest -Uri '{API_BASE_URL}/api/admin/ev-observe-cron?session=MIDDAY' "
          f"-Headers @{{'X-Prediction-Secret'='{PREDICT_SECRET}'}}")


if __name__ == "__main__":
    main()
