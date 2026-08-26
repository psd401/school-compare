# Analysis

Regenerates every figure in [docs/improvement-benchmarks.md](../docs/improvement-benchmarks.md).
This is offline analysis tooling, not part of the Streamlit app — nothing here is
imported at runtime.

## Running it

```bash
python analysis/benchmarks.py all          # every section
python analysis/benchmarks.py summary size # just these
python analysis/benchmarks.py all --refresh # re-pull from data.wa.gov first
```

The first run downloads about 200k assessment rows and caches them as CSV under
`analysis/out/`, which is gitignored. Later runs read the cache, so they finish
in seconds. Pass `--refresh` after OSPI publishes a new school year, and add that
year to `ASSESSMENT_DATASETS` in `fetch.py` first.

Without a `SOCRATA_APP_TOKEN` in `.env` the pull still works but is rate-limited
and takes a few minutes.

## Sections

| Section | Answers |
|---|---|
| `summary` | What does a typical year of change look like, overall and by grade? |
| `size` | How much of the spread is explained by tested cohort size? |
| `quartile` | Who actually lands in the top and bottom quartile? |
| `persistence` | Does a top-quartile year carry into the next one? |
| `validity` | What predicts improvement, and what only appears to? |
| `threeyear` | Three-year totals, who cleared +4, and the grade-band split |

## Files

| File | Contents |
|---|---|
| `fetch.py` | Paginated Socrata pulls and the CSV cache. Holds the year → dataset map, the student-group vocabulary, and the per-year name aliases. |
| `benchmarks.py` | Shaping, the six sections, and the CLI. |
| `artifact_data.py` | Emits `data.json` and `topq.json` for the "Typical Year" artifact, using the same `cells()` filter as `benchmarks.py`. Output is deterministic. |
| `stats_lite.py` | Rank statistics and resampling tests on numpy alone — Spearman with a permutation p-value, Mann-Whitney AUC, Wilson intervals, exact binomial tail. The app has no scipy dependency and does not need one for this. |

Rebuilding the published artifact:

```bash
python analysis/artifact_data.py --out <dir>
```

Transition names must keep the arrow character and the band labels are rendered
verbatim — both are display contracts the page reads, not just data.

## Things that will bite you

- **Each school year is a separate Socrata dataset.** They are not cumulative.
  `fetch.ASSESSMENT_DATASETS` holds the map, and `_sanity_check_ids()` fails loudly
  if it drifts from `config.settings.DATASET_IDS`.
- **Suppressed rows store the literal string `"NULL"`**, so the API's own
  `IS NOT NULL` does not filter them. They are dropped on numeric conversion.
- **`DataFrame.min(axis=1)` skips NaN by default.** Taking the smaller of two
  years' tested counts that way lets a cell through on one year's count alone.
  `cells()` drops rows missing either count before applying the floor.
- **Grade-level codes are `"03"`, not `"3rd Grade"`**, and several student-group
  names carry a space after the slash. See `config/settings.py`.
- Vocabulary drifts between years — `TwoorMoreRaces` became `Two Or More Races`.
  `fetch.YEAR_ALIASES` reconciles it.

## Scope

Grades 3–8 and 10; grade 11 is a retake population that does not survive the
cell-size floor. Smarter Balanced only. Nine student groups, though the published
note uses All Students throughout.
