# Tower Upgrade Advisor

Recommends the best next permanent upgrade in **The Tower** (idle tower defense mobile game). Calculates marginal benefit per coin for each upgrade and ranks them with adjustable category weights.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Nebulazer123/tower-upgrade-advisor)

## Features

- **Profile management** — create multiple build profiles to track different strategies
- **Upgrade dashboard** — view all upgrades grouped by category with inline-editable levels
- **Smart recommendations** — ranked by marginal benefit per coin with adjustable attack/defense/utility weights
- **Live updates** — htmx-powered UI updates without full page reloads

## Quick Start

```bash
pip install -e .
python app.py
```

Open http://localhost:5000 in your browser.

## Development

```bash
pip install -e ".[dev]"
pytest              # run tests
ruff check src/     # lint
mypy src/           # type check
```

## Deploy to Render

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) and create a new **Blueprint**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Click **Apply** — the app deploys in ~2 minutes

Or click the **Deploy to Render** button above.

## Tech Stack

- **Flask** + **Jinja2** — server-side rendering
- **htmx** — interactive updates without a JS framework
- **Pydantic v2** — data validation
- **Gunicorn** — production WSGI server
