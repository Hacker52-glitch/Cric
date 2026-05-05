"""
Core IPL phase score prediction — loads ball-by-ball data from Cricsheet and
computes average runs in any over range across the last N matches.

Stdlib-only so this module is portable across environments.
"""

import io
import json
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

CRICSHEET_IPL_URL = "https://cricsheet.org/downloads/ipl_json.zip"
DEFAULT_DATA_DIR = Path("ipl_data")


def ensure_data(data_dir=DEFAULT_DATA_DIR):
    data_dir = Path(data_dir)
    if data_dir.exists() and any(data_dir.glob("*.json")):
        return data_dir
    data_dir.mkdir(exist_ok=True)
    with urllib.request.urlopen(CRICSHEET_IPL_URL) as r:
        buf = r.read()
    with zipfile.ZipFile(io.BytesIO(buf)) as z:
        z.extractall(data_dir)
    return data_dir


def load_matches(data_dir=DEFAULT_DATA_DIR):
    matches = []
    for path in Path(data_dir).glob("*.json"):
        try:
            with open(path) as f:
                m = json.load(f)
            if not m.get("innings") or not m.get("info", {}).get("dates"):
                continue
            m["_date"] = datetime.strptime(m["info"]["dates"][-1], "%Y-%m-%d")
            matches.append(m)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return matches


def get_last_n(matches, n=7):
    return sorted(matches, key=lambda m: m["_date"], reverse=True)[:n]


def runs_in_range(innings, over_start, over_end):
    total = 0
    for over_obj in innings.get("overs", []):
        over_num = over_obj["over"] + 1
        if over_start <= over_num <= over_end:
            for delivery in over_obj["deliveries"]:
                total += delivery["runs"]["total"]
    return total


def predict_phase(matches, over_start, over_end):
    scores = []
    for m in matches:
        for innings in m["innings"]:
            scores.append(runs_in_range(innings, over_start, over_end))
    if not scores:
        return None, []
    return sum(scores) / len(scores), scores


PHASES = [
    ("powerplay", "Powerplay", "overs 1\u20136", 1, 6),
    ("middle", "Middle overs", "overs 7\u201315", 7, 15),
    ("death", "Death overs", "overs 16\u201320", 16, 20),
]


def build_dashboard_payload(data_dir=DEFAULT_DATA_DIR, n=7):
    matches = load_matches(data_dir)
    if not matches:
        return {"error": "no matches loaded", "matches": [], "phases": {}}
    last_n = get_last_n(matches, n)

    phases = {}
    for key, label, range_label, start, end in PHASES:
        avg, _ = predict_phase(last_n, start, end)
        phases[key] = {
            "label": label, "range_label": range_label,
            "start": start, "end": end,
            "predicted": round(avg) if avg is not None else None,
        }

    match_payload = []
    for m in last_n:
        innings_per_phase = {key: [] for key, *_ in PHASES}
        for innings in m["innings"]:
            for key, _, _, start, end in PHASES:
                innings_per_phase[key].append(runs_in_range(innings, start, end))
        match_payload.append({
            "date": m["_date"].strftime("%Y-%m-%d"),
            "teams": m["info"]["teams"],
            "venue": m["info"].get("venue", ""),
            "scores": innings_per_phase,
        })

    return {
        "tournament": "Indian Premier League",
        "as_of": last_n[0]["_date"].strftime("%Y-%m-%d") if last_n else None,
        "phases": phases,
        "matches": match_payload,
    }
