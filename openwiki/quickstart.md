---
type: Quickstart
title: WA School Compare wiki quickstart
description: Entry point to the OpenWiki for the WA School Compare Streamlit app - overview, page map, task-routing table with source entry points, tests and validation commands, and the backlog of undocumented areas.
tags: [quickstart, streamlit, ospi, navigation]
openwiki:
  roles: [repository]
  validation_commands: ["pytest tests/ -q"]
---

# WA School Compare - wiki quickstart

WA School Compare is a Streamlit app that compares Washington State schools and districts (achievement, demographics, graduation, staffing, district spending) using public OSPI data from the data.wa.gov Socrata API and local F-196 spending files. It has a Gemini-powered chat page and an offline analysis toolkit. Source of truth is code and tests; the project README is the human intro.

## Wiki map

- [Architecture overview](architecture/overview.md): layers, data flow, caching, session state, constraints.
- [Streamlit pages and charts](workflows/streamlit-pages.md): Comparison, Explorer, Correlations, home.
- [Chat agent](workflows/chat-agent.md): Gemini function-calling loop and the eight tools.
- [Dataset IDs and query vocabulary](domain/dataset-vocabulary.md): grade codes, student-group spellings, year aliases.
- [Improvement benchmarks analysis](domain/improvement-benchmarks-analysis.md): offline `analysis/` scripts and findings.
- [Setup, deployment and CI](operations/deployment-and-ci.md): env vars, Streamlit Cloud, workflows.
- [Testing](testing/testing.md): test map and narrow commands.

## Task routing

| Change area | Page | Entry points | Key symbols | Tests | Minimal validation |
|---|---|---|---|---|---|
| Add/change a chat tool | [Chat agent](workflows/chat-agent.md) | `src/chat/tools.py`, `src/chat/prompts.py` | `TOOL_SCHEMAS`, `execute_tool`, `GEMINI_TOOLS`, `SYSTEM_PROMPT` | `tests/test_tools.py` | `pytest tests/test_tools.py -q` |
| Change chat loop / session context | [Chat agent](workflows/chat-agent.md) | `src/chat/agent.py`, `pages/3_chat.py` | `ChatAgent.chat`, `_build_page_context` | none (manual) | `streamlit run app.py` |
| Grade/group/subgroup values, dataset IDs, new school year | [Dataset vocabulary](domain/dataset-vocabulary.md) | `config/settings.py`, `config/datasets.yaml` | `DATASET_IDS`, `GRADE_LEVELS`, `STUDENT_GROUP_YEAR_ALIASES`, `grade_code` | `tests/test_grade_levels.py` | `pytest tests/test_grade_levels.py -q` |
| Comparison / Explorer UI | [Streamlit pages](workflows/streamlit-pages.md) | `pages/1_comparison.py`, `pages/2_explorer.py` | `selected_entities`, `st.query_params` | none (manual) | `streamlit run app.py` |
| Correlation metrics / scatter | [Streamlit pages](workflows/streamlit-pages.md), [Chat agent](workflows/chat-agent.md) | `pages/4_correlations.py`, `src/viz/charts.py`, `src/data/combined.py` (excluded) | `METRICS`, `SCHOOL_METRICS`, `create_correlation_scatter` | `tests/test_combined.py` | `pytest tests/test_combined.py -q` |
| Chart functions | [Streamlit pages](workflows/streamlit-pages.md) | `src/viz/charts.py` | `create_*`, `add_suppression_footnote` | none (manual) | `streamlit run app.py` |
| Data client behavior, models | [Architecture](architecture/overview.md), [Testing](testing/testing.md) | `src/data/` (excluded from wiki) | `OSPIClient`, `_query`, `_paginated_get` | `tests/test_data_resilience.py`, `tests/test_client_helpers.py`, `tests/test_models.py` | `pytest tests/test_data_resilience.py -q` |
| Home page stats / cache warming | [Architecture](architecture/overview.md) | `app.py` | `_get_homepage_stats`, `main` | none | `streamlit run app.py` |
| Benchmark analysis | [Improvement benchmarks](domain/improvement-benchmarks-analysis.md) | `analysis/benchmarks.py`, `analysis/fetch.py` | `cells`, `ASSESSMENT_DATASETS` | none | `python analysis/benchmarks.py summary` |
| Env vars, deploy, CI, dev container | [Deployment and CI](operations/deployment-and-ci.md) | `pyproject.toml`, `.streamlit/config.toml`, `.devcontainer/devcontainer.json`, `.github/workflows/` | - | - | `ruff check .` |

Expensive/conditional: `analysis/benchmarks.py ... --refresh` re-downloads ~200k rows (only after OSPI publishes a new year). Live-API behavior is not covered by tests.

## Key facts

- Spending (F-196) exists only for districts; the Spending code paths are gated on `org_level == "District"`.
- Query values must be literal dataset strings (`"03"`, `"Hispanic/ Latino of any race(s)"`); use `Settings` helpers for labels.
- Suppressed data (small n) is shown as `*`/N/A, not zero.

## Backlog

- `src/data/` (`client.py`, `models.py`, `combined.py`): excluded by `.openwikiignore` (`data/` pattern matches `src/data/`), so the Socrata client, dataclasses and `METRICS` registry are documented only through their consumers and tests. Un-ignore (e.g. anchor the pattern as `/data/`) to document them.

