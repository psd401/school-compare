---
type: Operations Guide
title: Setup, deployment and CI
description: How to install and run the app, which environment variables and secrets it reads, Streamlit Community Cloud deployment, dev container and Streamlit server settings, and the GitHub Actions workflows (Claude review, security scan, scheduled OpenWiki update).
tags: [deployment, ci, streamlit-cloud, configuration]
openwiki:
  roles: [operations, delivery]
  change_kinds: [config, ci, dependencies]
  source_paths: [pyproject.toml, requirements.txt, README.md, .streamlit/config.toml, .devcontainer/devcontainer.json, .github/workflows/openwiki-update.yml, .github/workflows/security-scan.yml, .github/workflows/claude-review.yml]
  validation_commands: ["pytest tests/ -q", "ruff check ."]
---

# Setup, deployment and CI

## Run locally

Python 3.11+ (`requires-python` in `pyproject.toml`). `pip install -e ".[dev]"` (dev extras: pytest, pytest-cov, ruff), copy `.env.example` to `.env`, then `streamlit run app.py`. Ruff config: line length 100, rules `E,F,I,UP`, `E501` ignored. `requirements.txt` exists for hosted installs; dependencies in `pyproject.toml` are streamlit, pandas, plotly, sodapy, google-genai, python-dotenv, pyyaml, openpyxl. `analysis/` additionally uses numpy (transitively via pandas).

The dev container (`.devcontainer/devcontainer.json`, `python:1-3.11-bookworm` image) installs `requirements.txt` on creation and starts `streamlit run app.py` on port 8501 after attach, with `--server.enableCORS false --server.enableXsrfProtection false`. `.streamlit/config.toml` sets theme colours and `server.headless = true`; these are the only Streamlit server settings in the repo.

## Configuration

| Name | Needed for | Behavior when absent |
|---|---|---|
| `SOCRATA_APP_TOKEN` | data.wa.gov rate limits | works, rate limited |
| `GOOGLE_API_KEY` | Chat page | page shows an error and returns; see [Chat agent](../workflows/chat-agent.md) |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | none (reserved) | ignored |

Read by `config/settings.py` (see [Dataset vocabulary](../domain/dataset-vocabulary.md#settings-and-secrets)). `.env*` and `.streamlit/secrets.toml*` are secret-bearing and must not be committed or documented. The README points to `.env.example` and `.streamlit/secrets.toml.example` as templates; both paths match the `.openwikiignore` rules, so this wiki does not inspect them. The F-196 spending files live in `data/f196/` and are not covered by this wiki.

## Deployment

Hosted on Streamlit Community Cloud (main file `app.py`; secrets set in Advanced settings). The app may be asleep after inactivity. First load triggers cache warming and dataset validation in `app.py` ([architecture](../architecture/overview.md)).

## CI (`.github/workflows/`)

All three call org-owned reusable workflows in `PSD401/.github`, each pinned to a full commit SHA with a `# v1.0.0` comment (not `@main`). `.github/dependabot.yml` (github-actions ecosystem, weekly, 7-day cooldown) proposes updates to those SHA pins, so a pin bump is a reviewed change rather than a silent upstream change:
- `claude-review.yml`: on PR `opened`, `synchronize`, `ready_for_review` and `reopened`; skipped when the actor is `dependabot[bot]`; needs `id-token: write`; passes `BEDROCK_API_KEY`.
- `security-scan.yml`: on PRs, push to main, weekly (Monday 09:00 UTC), manual; read-only permissions.
- `openwiki-update.yml`: on push to main, weekly Monday 08:00 UTC, manual; regenerates this wiki with `contents: write` and `pull-requests: write` permissions; passes the `BEDROCK_API_KEY` and `PSD_AUTOMATION_APP_PRIVATE_KEY` secrets; concurrency group `openwiki` cancels superseded runs.

No workflow runs `pytest`; run tests locally ([Testing](../testing/testing.md)). Do not hand-edit generated OpenWiki pages unless asked (see `AGENTS.md`).

## Troubleshooting pointers

Wrong Python version, rate-limit/timeouts (add Socrata token), chat unavailable (missing Google key), stale-data warnings on first load (refresh). From README.
