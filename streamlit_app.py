"""
IPL Phase Score Predictor — Streamlit app

Combines:
  - Algorithmic prediction (Cricsheet, last 7 matches average)
  - Manual expert predictions (predictions.toml)
  - Live IPL match scores (CricAPI / cricketdata.org)
"""

import tomllib
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import live_api
from predictor import (
    DEFAULT_DATA_DIR,
    build_dashboard_payload,
    ensure_data,
)

# ---------- Page config ----------
st.set_page_config(
    page_title="IPL Phase Score Predictor",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Style ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300..600&family=DM+Sans:wght@400;500&display=swap');

    .stApp { font-family: 'DM Sans', system-ui, sans-serif; }

    .stApp h1, .stApp h2, .stApp h3 {
        font-family: 'Fraunces', serif !important;
        font-weight: 500 !important;
        letter-spacing: -0.01em !important;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Fraunces', serif !important;
        font-weight: 400 !important;
        font-size: 56px !important;
        color: #1f4422 !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stMetricLabel"] {
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        font-size: 11px !important;
        color: #76705f !important;
    }

    .live-card {
        background: #fbf6ec;
        border: 1px solid #d8cfb9;
        border-radius: 6px;
        padding: 14px 18px;
    }

    .small-caps {
        font-family: 'DM Sans', sans-serif;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #76705f;
    }

    /* Expert comparison table */
    .expert-wrap { margin: 8px 0 24px; }
    .expert-table { width: 100%; border-collapse: collapse; }
    .expert-table th {
        text-align: right;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #76705f;
        padding: 14px 18px;
        border-bottom: 1px solid #d8cfb9;
    }
    .expert-table th:first-child { text-align: left; }
    .expert-table th .th-sub {
        display: block;
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: #b9af96;
        font-size: 10px;
        margin-top: 3px;
    }
    .expert-table td {
        padding: 18px;
        border-bottom: 1px solid #e8dcc0;
    }
    .expert-table tr:last-child td { border-bottom: none; }
    .expert-table .name-main {
        font-family: 'Fraunces', serif;
        font-size: 17px;
        color: #1a1d17;
    }
    .expert-table .name-sub {
        font-size: 11px;
        color: #76705f;
        margin-top: 2px;
    }
    .expert-table .num {
        text-align: right;
        font-family: 'Fraunces', serif;
        font-size: 26px;
        font-weight: 400;
        color: #1a1d17;
        width: 110px;
        letter-spacing: -0.01em;
    }
    .expert-table .algo-row { background: rgba(31, 68, 34, 0.05); }
    .expert-table .algo-row .num { color: #1f4422; }
    .expert-table .algo-row .name-main { font-weight: 500; color: #1f4422; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Caches ----------
@st.cache_resource(show_spinner="Downloading IPL data from Cricsheet (~30MB, one-time)...")
def setup_data():
    ensure_data(DEFAULT_DATA_DIR)
    return True


@st.cache_data(ttl=600, show_spinner=False)
def get_predictions():
    return build_dashboard_payload(DEFAULT_DATA_DIR, n=7)


@st.cache_data(ttl=60, show_spinner=False)
def get_live_matches(api_key):
    return live_api.current_matches(api_key)


@st.cache_data(ttl=60, show_spinner=False)
def load_experts():
    """Load manual expert predictions from predictions.toml."""
    path = Path("predictions.toml")
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data.get("experts", [])
    except Exception as e:
        st.warning(f"Could not parse predictions.toml: {e}")
        return []


# ---------- Helpers ----------
TEAM_ALIASES = {
    "Mumbai Indians": "MI",
    "Chennai Super Kings": "CSK",
    "Royal Challengers Bengaluru": "RCB",
    "Royal Challengers Bangalore": "RCB",
    "Delhi Capitals": "DC",
    "Kolkata Knight Riders": "KKR",
    "Punjab Kings": "PBKS",
    "Rajasthan Royals": "RR",
    "Sunrisers Hyderabad": "SRH",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG",
}


def short(team):
    return TEAM_ALIASES.get(team, team)


def render_live_match(m):
    teams = m.get("teams") or []
    name = m.get("name") or " vs ".join(teams)
    status = m.get("status") or ""
    venue = m.get("venue") or ""
    score_lines = []
    for s in m.get("score") or []:
        inning = s.get("inning", "")
        score_lines.append(f"{inning}: <b>{s.get('r', 0)}/{s.get('w', 0)}</b> ({s.get('o', 0)} ov)")

    body = (
        f"<div class='live-card'>"
        f"<div class='small-caps'>{venue}</div>"
        f"<div style='font-family: Fraunces, serif; font-size: 17px; margin: 4px 0 8px;'>{name}</div>"
        + "".join(f"<div style='font-size: 13px;'>{line}</div>" for line in score_lines)
        + f"<div style='font-size: 12px; color: #76705f; margin-top: 8px; font-style: italic;'>{status}</div>"
        + f"</div>"
    )
    st.markdown(body, unsafe_allow_html=True)


def render_comparison_table(algo_phases, experts):
    """Algorithm + experts side by side."""
    rows = [{
        "name": "Algorithm",
        "subtitle": "avg of last 7 IPL matches",
        "is_algo": True,
        "powerplay": algo_phases["powerplay"]["predicted"],
        "middle": algo_phases["middle"]["predicted"],
        "death": algo_phases["death"]["predicted"],
    }]
    for e in experts:
        rows.append({
            "name": e.get("name", "Expert"),
            "subtitle": "expert call",
            "is_algo": False,
            "powerplay": e.get("powerplay", "—"),
            "middle": e.get("middle", "—"),
            "death": e.get("death", "—"),
        })

    html = [
        "<div class='expert-wrap'><table class='expert-table'>",
        "<thead><tr>",
        "<th>Predictor</th>",
        "<th>Powerplay<span class='th-sub'>overs 1\u20136</span></th>",
        "<th>Middle<span class='th-sub'>overs 7\u201315</span></th>",
        "<th>Death<span class='th-sub'>overs 16\u201320</span></th>",
        "</tr></thead><tbody>",
    ]
    for r in rows:
        cls = " class='algo-row'" if r["is_algo"] else ""
        html.append(
            f"<tr{cls}>"
            f"<td><div class='name-main'>{r['name']}</div>"
            f"<div class='name-sub'>{r['subtitle']}</div></td>"
            f"<td class='num'>{r['powerplay']}</td>"
            f"<td class='num'>{r['middle']}</td>"
            f"<td class='num'>{r['death']}</td>"
            f"</tr>"
        )
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def matches_to_df(payload, phase_key):
    rows = []
    for m in payload["matches"]:
        scores = m["scores"][phase_key]
        rows.append({
            "Match": m["date"][5:],
            "Date": m["date"],
            "Teams": " v ".join(short(t) for t in m["teams"]),
            "Venue": m["venue"],
            "1st innings": scores[0] if len(scores) >= 1 else None,
            "2nd innings": scores[1] if len(scores) >= 2 else None,
            "Average": round(sum(scores) / len(scores)) if scores else 0,
        })
    return pd.DataFrame(rows)


# ---------- Main ----------
def main():
    setup_data()

    st.title("🏏 IPL Phase Score Predictor")
    st.caption("Algorithm vs experts — predicting runs in any over range from the last 7 matches in the tournament.")

    # Sidebar
    with st.sidebar:
        st.markdown("### About")
        st.markdown(
            "A simple cricket score predictor: takes the average of the last "
            "7 IPL matches' scores in any over range. Compared head-to-head "
            "with predictions entered by 3 cricket experts."
        )
        st.markdown("### Refresh")
        if st.button("Re-fetch all data", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
        st.markdown("### Data sources")
        st.markdown(
            "- Historical: [cricsheet.org](https://cricsheet.org)\n"
            "- Live scores: [cricketdata.org](https://cricketdata.org)\n"
            "- Expert calls: `predictions.toml` in repo"
        )
        st.markdown("### API key")
        if "CRIC_API_KEY" in st.secrets:
            st.success("CricAPI key configured ✓")
        else:
            st.warning("No CricAPI key — live matches disabled")

    # ---------- Live matches ----------
    st.divider()
    st.subheader("Live IPL matches")

    api_key = st.secrets.get("CRIC_API_KEY")
    if not api_key:
        st.info(
            "Add your CricAPI key in Streamlit secrets to see live matches. "
            "Free key: https://cricketdata.org/signup.aspx"
        )
    else:
        live = get_live_matches(api_key)
        if live.get("error"):
            st.warning(f"Live API error: {live['error']}")
        else:
            ipl = live_api.filter_ipl(live)
            if not ipl:
                st.write("No IPL matches currently live.")
            else:
                cols = st.columns(min(len(ipl), 3))
                for col, m in zip(cols, ipl[:3]):
                    with col:
                        render_live_match(m)

    # ---------- Predictions ----------
    st.divider()
    st.subheader("Phase score predictions")

    payload = get_predictions()
    if payload.get("error"):
        st.error(f"Could not load predictions: {payload['error']}")
        return

    phases = payload["phases"]
    cols = st.columns(3)
    for col, key in zip(cols, ["powerplay", "middle", "death"]):
        p = phases[key]
        with col:
            st.metric(
                label=f"{p['label']} ({p['range_label']})",
                value=f"{p['predicted']}",
            )
    st.caption(
        f"Algorithmic prediction. Average across {len(payload['matches']) * 2} innings "
        f"from the {len(payload['matches'])} most recent matches "
        f"(as of {payload.get('as_of', 'today')})."
    )

    # ---------- Algorithm vs experts ----------
    experts = load_experts()
    if experts:
        st.divider()
        st.subheader("Algorithm vs experts")
        st.caption(
            f"Comparison of the algorithm's prediction with manual calls from "
            f"{len(experts)} cricket experts. Edit `predictions.toml` in the repo to update."
        )
        render_comparison_table(phases, experts)
    else:
        st.divider()
        st.info(
            "To compare against expert predictions, add a `predictions.toml` "
            "file at the root of the repo. See README for the format."
        )

    # ---------- Last 7 detail ----------
    st.divider()
    st.subheader("Last 7 matches")

    selected = st.radio(
        "Phase",
        options=["powerplay", "middle", "death"],
        format_func=lambda k: phases[k]["label"],
        horizontal=True,
        label_visibility="collapsed",
    )

    df = matches_to_df(payload, selected)
    avg = phases[selected]["predicted"]

    bars = (
        alt.Chart(df)
        .mark_bar(color="#2d6131", cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("Match:N", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Average:Q", title=f"Average runs in {phases[selected]['range_label']}"),
            tooltip=["Date", "Teams", "Venue", "1st innings", "2nd innings", "Average"],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame({"y": [avg]}))
        .mark_rule(color="#1f4422", strokeDash=[5, 4], size=2)
        .encode(y="y:Q")
    )
    rule_label = (
        alt.Chart(pd.DataFrame({"y": [avg], "label": [f"avg {avg}"]}))
        .mark_text(color="#1f4422", align="right", dx=-4, dy=-6)
        .encode(y="y:Q", text="label")
    )
    st.altair_chart(bars + rule + rule_label, use_container_width=True)

    st.dataframe(
        df.drop(columns=["Match"]),
        use_container_width=True,
        hide_index=True,
    )

    # Footer
    st.divider()
    st.caption(
        "🏏 Built with Streamlit. Data: cricsheet.org (historical) + cricketdata.org (live) + predictions.toml (experts)."
    )


if __name__ == "__main__":
    main()
