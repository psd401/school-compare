---
type: Analysis Tooling
title: Improvement benchmarks analysis (offline)
description: The offline analysis scripts under analysis/ and the docs/improvement-benchmarks.md note they regenerate - method, data traps, headline findings on how much proficiency moves per year, and how to rerun or extend them.
tags: [analysis, benchmarks, statistics, ospi]
openwiki:
  roles: [domain, workflow]
  change_kinds: [analysis, data-vocabulary]
  source_paths: [analysis/fetch.py, analysis/benchmarks.py, analysis/artifact_data.py, analysis/stats_lite.py, docs/improvement-benchmarks.md, analysis/README.md]
  symbols: [ASSESSMENT_DATASETS, YEAR_ALIASES, _sanity_check_ids, cells, entity_scores, five_number, spearman_p, build_rows]
  invariants:
    - Cells need a tested cohort of at least 20 in both years; rows missing either count are dropped.
    - Suppressed rows hold the string "NULL" and are removed by numeric coercion.
    - Nothing under analysis/ is imported by the app.
  validation_commands: ["python analysis/benchmarks.py summary"]
---

# Improvement benchmarks analysis (offline)

Purpose: set improvement targets against the observed distribution of year-over-year proficiency change in Washington, and document statistical traps in ranking schools by improvement. `docs/improvement-benchmarks.md` is the human-readable result; `analysis/` regenerates every figure in it. `analysis/README.md` is the canonical run guide. The app never imports this code (`README.md` project structure says so).

## Pipeline

- **`fetch.py`**: paginated Socrata pulls (batch 5000, 5 retries with backoff, `X-App-Token` header when `Settings.has_socrata_token`) of four assessment datasets (`ASSESSMENT_DATASETS`: 2021-22 `v928-8kke`, 2022-23 `xh7m-utwp`, 2023-24 `x73g-mrqp`, 2024-25 `h5d9-vgwi`) plus enrollment, cached as CSV in the gitignored `analysis/out/`. SBAC ELA/Math, grades 03-08 and 10, nine student groups. `_sanity_check_ids()` raises if the 2023-24/2024-25 IDs disagree with `DATASET_IDS` in [config/settings.py](dataset-vocabulary.md). `refresh=True` / `--refresh` re-pulls.
- **`benchmarks.py`**: `cells()` is the shared filter (floor of 20 in both years); `entity_scores`, `profile`, then six section functions (`summary`, `size`, `quartile`, `persistence`, `validity`, `threeyear`) invoked via `python analysis/benchmarks.py all|<sections> [--refresh]`.
- **`stats_lite.py`**: numpy-only `spearman`, `spearman_p` (permutation), `auc`, `wilson`, `binom_sf`, `five_number`; the project deliberately has no scipy dependency.
- **`artifact_data.py`**: `build_rows`/`build_panel` write `data.json` and `topq.json` for the interactive "Typical Year" artifact (`--out <dir>`), reusing `cells()` so numbers agree. Transition names must keep the arrow character and band labels verbatim because the artifact page reads them.

## Findings worth knowing (from `docs/improvement-benchmarks.md`, analysis date there)

- Median year-over-year change is under one point; roughly 46-47% of schools decline in a year.
- Spread is driven by tested cohort size (IQR 18.2 for 20-40 students vs 7.2 above 150), so compare within size bands.
- One-year top-quartile rankings repeat at or below chance; "gained three years running" must be judged against year-specific base rates.
- ELA/Math agreement is not independent evidence (same students).
- Three-year change shows signal within a grade band (elementary, middle) but not across bands.

Treat the numbers as snapshot results; regenerate rather than hand-editing figures.

## Pitfalls

Each school year is a separate non-cumulative dataset; suppressed values are the string `"NULL"`; `DataFrame.min(axis=1)` skips NaN (so `cells()` drops missing counts first); grade codes are `"03"` not labels; group names drift between years (`YEAR_ALIASES`). The 2019-20 and 2020-21 years have no assessments. Grade 11 is excluded.

## Change navigation

- Add a new school year: add its dataset ID to `ASSESSMENT_DATASETS`, update `YEAR_ALIASES` if group spellings shift, run `python analysis/benchmarks.py all --refresh`, then update the tables in `docs/improvement-benchmarks.md` and the aliases in the app settings (see [vocabulary](dataset-vocabulary.md)).
- Validation: there are no tests for `analysis/`; run `python analysis/benchmarks.py summary` after cache exists (a first run downloads ~200k rows; slower without a Socrata token).
- Related: it shares the Socrata domain and token handling with the app, per [Deployment and CI](../operations/deployment-and-ci.md).
