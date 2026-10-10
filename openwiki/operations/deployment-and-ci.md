---
type: Operations Guide
title: Setup, deployment and CI
description: How to install and run the app, which environment variables and secrets it reads, Streamlit Community Cloud deployment, and the GitHub Actions workflows (Claude review, security scan, scheduled OpenWiki update).
tags: [deployment, ci, streamlit-cloud, configuration]
openwiki:
  roles: [operations, delivery]
  change_kinds: [config, ci, dependencies]
  source_paths: [pyproject.toml, requirements.txt, README.md, .github/workflows/openwiki-update.yml, .github/workflows/security-scan.yml, .github/workflows/claude-review.yml]
  validation_commands: ["pytest tests/ -q", "ruff check ."]
---

# Setup, deployment and CI

## Run locally

Python 3.11+ (`requires-python` in `pyproject.toml`). `pip install -e ".[dev]"` (dev extras: pytest, pytest-cov, ruff), copy `.env.example` to `.env`, then `streamlit run app.py`. Ruff config: line length 100, rules `E,F,I,UP`, `E501` ignored. `requirements.txt` exists for hosted installs; dependencies in `pyproject.toml` are streamlit, pandas, plotly, sodapy, google-genai, python-dotenv, pyyaml, openpyxl. `analysis/` additionally uses numpy (transitively via pandas).

## Configuration

| Name | Needed for | Behavior when absent |
|---|---|---|
| `SOCRATA_APP_TOKEN` | data.wa.gov rate limits | works, rate limited |
| `GOOGLE_API_KEY` | Chat page | page shows an error and returns; see [Chat agent](../workflows/chat-agent.md) |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | none (reserved) | ignored |

Read by `config/settings.py` (see [Dataset vocabulary](../domain/dataset-vocabulary.md#settings-and-secrets)). `.env*` and `.streamlit/secrets.toml*` are secret-bearing and must not be committed or documented; a template exists at `.streamlit/secrets.toml.example` per README. The F-196 spending files live in `data/f196/` and are not covered by this wiki.

## Deployment

Hosted on Streamlit Community Cloud (main file `app.py`; secrets set in Advanced settings). The app may be asleep after inactivity. First load triggers cache warming and dataset validation in `app.py` ([architecture](../architecture/overview.md)).

## CI (`.github/workflows/`)

All three call org-owned reusable workflows in `PSD401/.github` at `@main` (deliberate, per comments):
- `claude-review.yml`: on PR opened/ready/reopened, skipped for dependabot; needs `id-token: write`; uses `BEDROCK_API_KEY`.
- `security-scan.yml`: on PRs, push to main, weekly (Monday 09:00 UTC), manual; read-only permissions.
- `openwiki-update.yml`: on push to main, weekly Monday 08:00 UTC, manual; regenerates this wiki with contents/PR write permission; concurrency group `openwiki` cancels superseded runs.

No workflow runs `pytest`; run tests locally ([Testing](../testing/testing.md)). Do not hand-edit generated OpenWiki pages unless asked (see `AGENTS.md`).

## Troubleshooting pointers

Wrong Python version, rate-limit/timeouts (add Socrata token), chat unavailable (missing Google key), stale-data warnings on first load (refresh). From README.
