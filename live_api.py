"""
Thin client for the CricAPI / cricketdata.org REST API.

Get a free API key at https://cricketdata.org/signup.aspx — the free tier
allows ~100 requests/day, which is plenty for a personal dashboard.
"""

import requests

BASE_URL = "https://api.cricapi.com/v1"
TIMEOUT = 10


def _get(path, api_key, **params):
    """GET helper with API key and basic error handling."""
    params["apikey"] = api_key
    try:
        r = requests.get(f"{BASE_URL}/{path}", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        if body.get("status") == "failure":
            return {"error": body.get("reason", "api error"), "data": []}
        return body
    except requests.RequestException as e:
        return {"error": str(e), "data": []}


def current_matches(api_key, offset=0):
    """Live and currently-running matches across all formats and competitions."""
    return _get("currentMatches", api_key, offset=offset)


def matches(api_key, offset=0):
    """Recent + upcoming matches (broader than current)."""
    return _get("matches", api_key, offset=offset)


def match_info(api_key, match_id):
    """Detailed info for a single match by id."""
    return _get("match_info", api_key, id=match_id)


def filter_ipl(matches_response):
    """Return only matches that look like IPL matches."""
    out = []
    for m in matches_response.get("data", []) or []:
        series = (m.get("seriesName") or m.get("name") or "").lower()
        if "indian premier league" in series or "ipl" in series:
            out.append(m)
    return out
