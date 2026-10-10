---
type: Testing Guide
title: Test suite map and validation commands
description: Which pytest files cover which behavior (chat tools, settings vocabulary, data-client resilience, models, metric helpers), how to run them narrowly, and what is untested.
tags: [pytest, testing, validation]
openwiki:
  roles: [testing]
  change_kinds: [tests]
  test_paths: [tests/test_tools.py, tests/test_grade_levels.py, tests/test_combined.py, tests/test_data_resilience.py, tests/test_models.py, tests/test_client_helpers.py]
  validation_commands: ["pytest tests/ -q", "pytest tests/test_tools.py -q"]
---

# Test suite map and validation commands

pytest config (`pyproject.toml`): `testpaths = ["tests"]`, `pythonpath = ["."]`. Everything is offline: network access is mocked (`unittest.mock`, `PropertyMock` on `OSPIClient.client`). Full run: `pytest tests/ -q` (quiet; failures print in full). CI does not run tests ([Deployment and CI](../operations/deployment-and-ci.md)).

| Area / behavior | File and suites | Source under test |
|---|---|---|
| Chat tool schemas, Gemini conversion (enum preserved, `GEMINI_TOOLS` is a `types.Tool`), per-tool output formatting, unknown tool | `tests/test_tools.py`: `TestToolSchemas`, `TestGeminiToolConversion`, `TestExecuteTool` | [`src/chat/tools.py`](../workflows/chat-agent.md) |
| Grade codes vs labels, round-trip, student-group labels and per-year aliases | `tests/test_grade_levels.py`: `TestGradeLevelConstants`, `TestGradeLabel`, `TestGradeCode`, `TestStudentGroupForYear` | `config/settings.py` ([vocabulary](../domain/dataset-vocabulary.md)) |
| `METRICS` (19) / `SCHOOL_METRICS` (10) shape, label/format helpers, NaN -> "N/A" | `tests/test_combined.py` | `src/data/combined.py` ([Correlations](../workflows/streamlit-pages.md#correlations-pages4_correlationspy)) |
| `_query` returns `[]` on errors, zero/None enrollment gives `None` percent, dynamic year range, `_paginated_get`, `validate_datasets`, lookup by code | `tests/test_data_resilience.py` | `src/data/client.py`, `combined.py` |
| `_safe_float/_safe_percent/_safe_int` parsing | `tests/test_client_helpers.py` | `src/data/client.py` |
| Dataclass defaults, `display_name`, `proficiency_rate` fallback to levels | `tests/test_models.py` | `src/data/models.py` |

## Gaps

No tests for Streamlit pages, `src/viz/charts.py`, `ChatAgent`, or `analysis/`. UI and chart changes require running `streamlit run app.py` manually. The `analyze_correlation` branch of `execute_tool` (in `src/chat/tools.py`) is untested beyond its presence in the tool-name list; its correlation/R² output and top-5 formatting need a manual check or a new mocked test.

## Narrow checks by change

- Chat tool or schema: `pytest tests/test_tools.py -q`.
- Grade/group constants: `pytest tests/test_grade_levels.py -q` (it asserts query values are API codes, not display labels).
- Metric registry: `pytest tests/test_combined.py -q` (hard-coded counts 19 and 10 must be updated when adding metrics).
- Client/pagination: `pytest tests/test_data_resilience.py tests/test_client_helpers.py -q`.
