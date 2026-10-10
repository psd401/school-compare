---
type: Domain Reference
title: Dataset IDs and query vocabulary
description: Socrata dataset IDs per school year, the literal grade-level codes and student-group spellings the OSPI datasets store, display-label maps, and year-based aliasing, all owned by config/settings.py.
tags: [ospi, socrata, settings, vocabulary]
openwiki:
  roles: [domain]
  change_kinds: [config, data-vocabulary]
  source_paths: [config/settings.py, config/datasets.yaml, analysis/fetch.py]
  symbols: [Settings, get_settings, DATASET_IDS, GRADE_LEVELS, GRADE_LABELS, STUDENT_GROUPS_CORE, STUDENT_GROUPS_EXTENDED, STUDENT_GROUP_LABELS, STUDENT_GROUP_YEAR_ALIASES, grade_code, grade_label, student_group_for_year]
  test_paths: [tests/test_grade_levels.py]
  invariants:
    - GRADE_LEVELS and student-group lists hold literal API values, never display labels.
    - Two student-group names use older spellings in older years.
  validation_commands: ["pytest tests/test_grade_levels.py -q"]
---

# Dataset IDs and query vocabulary

`config/settings.py` is the single source of truth for how the app talks to OSPI datasets. Getting a string wrong here does not raise: Socrata just returns zero rows (e.g. querying `"3rd Grade"` matches nothing).

## Datasets

`DATASET_IDS` (in `config/settings.py`; `config/datasets.yaml` mirrors it with field lists, plus a `directory` dataset `fhxx-d5zv` and group/subject/suppression lists, and the code comment calls Python the fallback):

| Key | ID | Notes |
|---|---|---|
| `assessment` | `x73g-mrqp` | 2023-24 only despite the "through 2023-24" comment; each year is its own dataset |
| `assessment_2024_25` | `h5d9-vgwi` | 2024-25+ |
| `enrollment` | `2rwv-gs2e` | demographics/headcounts |
| `graduation` / `graduation_2024_25` | `76iv-8ed4` / `isxb-523t` | split by year like assessment |
| `teachers` | `yp28-ks6d` | staffing |

Spending (F-196) is not on Socrata; it comes from local files under `data/f196/` (ignored from this wiki). Domain is `SOCRATA_DOMAIN = "data.wa.gov"`. Historical assessment IDs for 2021-22 (`v928-8kke`) and 2022-23 (`xh7m-utwp`) appear only in `analysis/fetch.py` because the app queries only the two newest datasets; `_sanity_check_ids()` there fails loudly if the two sources drift. See [Improvement benchmarks analysis](improvement-benchmarks-analysis.md).

Defaults: `DEFAULT_YEAR = "2023-24"` for assessment/graduation, but README states demographics and staffing default to 2024-25 (released earlier). `MAX_COMPARISON_ENTITIES = 5`.

## Literal values vs display labels

- **Grades**: `GRADE_LEVELS = ["All Grades","03","04","05","06","07","08","10","11"]`. `GRADE_LABELS` maps to `"3rd Grade"` etc. for display only. `Settings.grade_label(code)` and `Settings.grade_code(label)` convert both ways and pass unknown values through. The chat tool calls `grade_code` because Gemini may emit a display label.
- **Student groups**: `STUDENT_GROUPS_CORE` (8) and `STUDENT_GROUPS_EXTENDED` (10) hold the dataset's literal spellings, including irregular spacing like `"Hispanic/ Latino of any race(s)"`. `STUDENT_GROUP_LABELS` / `student_group_label()` tidy them for display.
- **Year aliases**: `STUDENT_GROUP_YEAR_ALIASES` maps `"Two Or More Races"` to `"TwoorMoreRaces"` through 2022-23 and `"Native Hawaiian/Pacific Islander"` to `"Native Hawaiian/ Other Pacific Islander"` through 2023-24. `student_group_for_year(group, school_year)` resolves using string comparison `school_year <= alias[0]`. `analysis/fetch.py` keeps its own `YEAR_ALIASES` for the multi-year series.
- **Spending years** use `"YY-YY"` (`"24-25"`); the app derives them with `school_year[2:]`. F-196 coverage per the chat tool schema is 14-15 through 24-25.

## Settings and secrets

`Settings` reads `SOCRATA_APP_TOKEN`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` from env (`load_dotenv()` at import; Streamlit Cloud secrets per README). Properties `has_socrata_token`, `has_google_key`, `has_anthropic_key` gate behavior. Anthropic/OpenAI keys are reserved and unused. LLM settings: `LLM_MODEL = "gemini-3-flash-preview"`, `LLM_MAX_TOKENS = 4096`, `LLM_TEMPERATURE = 0.3`. `get_settings()` is `lru_cache`d, so env changes after first call are not seen. Never commit values; see [Deployment and CI](../operations/deployment-and-ci.md).

## Change navigation

- Consult when adding a student group, grade, school year, or dataset.
- Adding a new school year: add dataset ID(s) to `DATASET_IDS` and `config/datasets.yaml`, extend `analysis/fetch.py` `ASSESSMENT_DATASETS`, and check alias cut-offs in `STUDENT_GROUP_YEAR_ALIASES`. Year-routing in `src/data/client.py` is not visible to this wiki (excluded).
- Adding a student group: put the literal API spelling in the core or extended list, add a tidy label only if it differs, update the enum text in the `get_assessment_data` tool description in `src/chat/tools.py` ([Chat agent](../workflows/chat-agent.md)).
- Tests: `tests/test_grade_levels.py` (classes covering code/label round trip, no overlap between core and extended, alias spelling by year). Validate: `pytest tests/test_grade_levels.py -q`.
- Pages that render these lists: [Streamlit pages](../workflows/streamlit-pages.md).
