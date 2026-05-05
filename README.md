# 🏏 IPL Phase Score Predictor

A Streamlit dashboard that predicts the runs scored in any over range of an IPL T20 match, based on the average across the last 7 IPL matches in the tournament. Also shows live IPL match scores via the CricAPI.

- **Historical data:** [cricsheet.org](https://cricsheet.org) — every IPL match ball-by-ball, free, no auth
- **Live scores:** [cricketdata.org](https://cricketdata.org) — free API key, ~100 calls/day

---

## What it does

1. Downloads ball-by-ball IPL data from Cricsheet on first boot
2. Sorts matches by date, takes the most recent 7
3. For each phase of an innings (powerplay / middle / death), averages the runs scored across all 14 innings from those 7 matches
4. That average is the prediction
5. On top of that, fetches currently-running IPL matches from CricAPI and shows their live scores

---

## Quickstart (local)

```bash
git clone <your-repo-url>
cd cricket-streamlit
python -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: add your free CricAPI key for live matches
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and paste your key

streamlit run streamlit_app.py
```

First run downloads ~30MB from Cricsheet (one-time, cached afterwards). Then the app opens at http://localhost:8501.

The live-matches section is optional — without an API key, the rest of the dashboard still works.

---

## Deploy to Streamlit Community Cloud (free)

This is the fast path. Free hosting, GitHub-integrated, takes 5 minutes.

### 1. Push the repo to GitHub

```bash
cd cricket-streamlit
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

The repo can be public or private — Streamlit Community Cloud supports both.

### 2. Get a free CricAPI key

1. Sign up at https://cricketdata.org/signup.aspx
2. Verify your email
3. Copy the API key from your dashboard

### 3. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with your GitHub account
2. Click **New app**
3. Pick your repository, branch (`main`), and main file (`streamlit_app.py`)
4. Before clicking Deploy, click **Advanced settings → Secrets** and paste:

   ```toml
   CRIC_API_KEY = "your-cricapi-key-here"
   ```

5. Click **Deploy**. First deploy takes ~3 minutes (installs deps + downloads Cricsheet zip).

You'll get a URL like `https://<your-app>.streamlit.app` — public, shareable.

### 4. Updating the app

Push to `main` and Streamlit Cloud auto-redeploys. To re-fetch fresh Cricsheet data without redeploying, click "Re-fetch all data" in the sidebar.

---

## Project structure

```
cricket-streamlit/
├── streamlit_app.py              # main app
├── predictor.py                  # historical predictor (stdlib-only)
├── live_api.py                   # CricAPI client
├── requirements.txt              # streamlit + pandas + altair + requests
├── .streamlit/
│   ├── config.toml               # theme
│   └── secrets.toml.example      # template (real one is gitignored)
├── .gitignore
└── README.md
```

---

## Customizing

- **Use last N instead of 7**: in `streamlit_app.py`, change `n=7` in `build_dashboard_payload(...)`.
- **Custom over ranges**: edit the `PHASES` constant near the bottom of `predictor.py`.
- **Add a venue filter**: filter the `matches` list in `build_dashboard_payload()` by venue before passing to `get_last_n`.
- **Use 1st innings only**: in `predict_phase()`, change `m["innings"]` to `m["innings"][:1]`.

---

## Troubleshooting

**"Live API error"** — usually means you've hit the daily quota (~100 free calls). Wait a day, or upgrade to a paid CricAPI plan.

**Slow first load** — the Cricsheet zip is ~30MB and downloads on first run. Subsequent loads use the cache.

**App goes to sleep** — Streamlit Community Cloud puts free apps to sleep after inactivity. First request after wake takes ~30 seconds.

---

## What this app deliberately doesn't do

It doesn't filter by team, venue, opposition, toss, or weather. It's a tournament-wide rolling baseline — the simplest thing that could possibly work. To actually beat this baseline with a smarter model, you'd want to add features one at a time and measure MAE on a holdout.
