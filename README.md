# Pragya (প্রজ্ঞা) — Bangladesh Socioeconomic Insight Agent

A bilingual (English/Bangla) AI agent that answers questions about Bangladesh's
economy by pulling real World Bank data, analyzing it, and writing a narrative
report — planned autonomously via Claude's tool-use.

Built entirely on a phone (Termux). No paid infrastructure required.

## How it works

1. You ask a question in plain English.
2. Claude (Haiku 4.5) decides which indicators to fetch — youth unemployment,
   inflation, GDP growth — and calls `fetch_indicator` for each.
3. Real data is pulled from the World Bank API and cached locally.
4. Claude writes a 2-4 sentence bilingual summary grounded in the actual numbers.
5. A chart + HTML report is generated and shown in the web app.

## Project structure

```
pragya_agent/
├── wb_fetcher.py        # World Bank API + local cache
├── analyzer.py          # trend/correlation helpers
├── chart_generator.py   # EN/BN chart rendering
├── report_writer.py     # self-contained HTML report builder
├── agent.py             # the Claude tool-use loop (core logic)
├── streamlit_app.py     # web interface (entry point for hosting)
├── requirements.txt
└── outputs/             # generated reports + charts land here
```

Note: Hugging Face Spaces now requires a paid plan to run Gradio or Docker
Spaces (Static-only is free there). Streamlit Community Cloud is the free
alternative that still runs a real Python backend — that's what this project
targets.

## 1. Run it locally on Termux

```bash
pkg install python
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
streamlit run streamlit_app.py
```

Termux will print a local URL — open it in your phone's browser to test
before deploying.

Never commit your API key to GitHub. Always load it from an environment
variable, as done above.

## 2. Push the code to GitHub (required for Streamlit Cloud)

Streamlit Community Cloud deploys directly from a GitHub repo — there's no
manual file upload, so this step is required, not optional.

```bash
git init
git add .
git commit -m "Pragya v1.0"
git remote add origin https://github.com/YOUR-USERNAME/pragya-agent.git
git branch -M main
git push -u origin main
```

Add a `.gitignore` first so you don't commit clutter or secrets:
```
__pycache__/
data_cache/*
outputs/*
.env
```

**Important:** never push your API key. If you ever paste it into a file by
mistake, rotate it immediately in the Anthropic Console.

## 3. Deploy on Streamlit Community Cloud (free, no card)

1. Go to share.streamlit.io and sign in with your GitHub account
2. Click **Create app** → **Deploy a public app from GitHub**
3. Pick your `pragya-agent` repo, branch `main`, main file path `streamlit_app.py`
4. Before clicking Deploy, open **Advanced settings → Secrets** and add:
   ```
   ANTHROPIC_API_KEY = "your-actual-key-here"
   ```
5. Click **Deploy**. Build takes a couple of minutes.

Your live app appears at a URL like:
`https://pragya-agent-YOUR-USERNAME.streamlit.app`

That's public, free, and shareable on your portfolio, LinkedIn, and college
applications. Free-tier apps sleep after ~12 hours of no traffic — visiting
the link wakes them back up in a few seconds, which is a fine tradeoff for a
portfolio demo.

## Notes on accuracy

- The World Bank's youth-unemployment series (`SL.UEM.1524.ZS`) has real gaps
  for some years — the agent handles missing years gracefully, but don't be
  surprised if a request for a very recent year comes back empty.
- Bengali text in chart titles may render as boxes unless a Bengali-capable
  font (e.g. "Noto Sans Bengali") is installed on the host. The HTML report's
  Bangla text always renders fine since browsers handle Unicode properly.
