"""
usage_limiter.py - a simple daily cap on how many agent queries the app will
run. Gemini's free tier has no cost risk, but it does share one daily request
quota (per API key) across every visitor to this public app - without a cap,
one enthusiastic visitor could exhaust the day's quota for everyone else.
Not bulletproof (a redeploy resets the counter, and it's per-container, not
per-visitor) - it's a friendly speed bump, not a security system.
"""

import os
import json
from datetime import date
from pathlib import Path

COUNTER_FILE = Path(__file__).parent / "data_cache" / "usage_counter.json"
DEFAULT_DAILY_LIMIT = 100  # each question uses ~2 API calls; Gemini free tier allows ~1500/day total


def _load():
    if COUNTER_FILE.exists():
        try:
            with open(COUNTER_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"date": "", "count": 0}


def _save(data):
    COUNTER_FILE.parent.mkdir(exist_ok=True)
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)


def check_and_increment():
    """
    Returns (allowed: bool, remaining: int).
    Call this BEFORE running a query. If allowed is False, don't call the API.
    """
    limit = int(os.environ.get("MAX_DAILY_QUERIES", DEFAULT_DAILY_LIMIT))
    today = str(date.today())
    data = _load()

    if data.get("date") != today:
        data = {"date": today, "count": 0}

    if data["count"] >= limit:
        return False, 0

    data["count"] += 1
    _save(data)
    return True, limit - data["count"]
