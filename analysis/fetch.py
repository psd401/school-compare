"""Paginated Socrata pulls for the multi-year benchmark analysis.

The app only ever queries the two most recent assessment datasets, so
`config.settings.DATASET_IDS` only names those. Year-over-year work needs the
historical series as well; it lives here rather than in app config because
nothing at runtime reads it.

Results are cached as CSV under `out/` so re-runs are cheap and offline.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATASET_IDS, get_settings  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out"

# One Socrata dataset per school year — these are NOT cumulative tables.
# 2019-20 and 2020-21 are absent statewide; no assessment was administered.
ASSESSMENT_DATASETS = {
    "2021-22": "v928-8kke",
    "2022-23": "xh7m-utwp",
    "2023-24": "x73g-mrqp",
    "2024-25": "h5d9-vgwi",
}
ENROLLMENT_DATASET = DATASET_IDS["enrollment"]

# Verified identical across all four datasets. Grade 11 is a retake population
# and does not survive the cell-size floor, so it is excluded throughout.
GRADES = ["03", "04", "05", "06", "07", "08", "10"]

# Literal `studentgroup` values. Note the space after the slash in several, and
# that two were respelled partway through the series (see YEAR_ALIASES).
STUDENT_GROUPS = [
    "All Students",
    "Low-Income",
    "English Language Learners",
    "Students with Disabilities",
    "Hispanic/ Latino of any race(s)",
    "Black/ African American",
    "Asian",
    "Two Or More Races",
    "White",
]
YEAR_ALIASES = {
    "Two Or More Races": {"2021-22": "TwoorMoreRaces", "2022-23": "TwoorMoreRaces"},
}

_ASSESSMENT_SELECT = (
    "schoolyear,organizationlevel,county,esdname,districtcode,districtname,"
    "schoolcode,schoolname,gradelevel,testsubject,studentgroup,"
    "percentlevel3,percentlevel4,count_of_students_expected"
)
_ENROLLMENT_SELECT = (
    "schoolyear,organizationlevel,districtcode,schoolcode,county,esdname,"
    "all_students,low_income,english_language_learners,"
    "students_with_disabilities,white"
)


def _sanity_check_ids() -> None:
    """Fail loudly if app config and this module drift apart."""
    for year, key in (("2023-24", "assessment"), ("2024-25", "assessment_2024_25")):
        if ASSESSMENT_DATASETS[year] != DATASET_IDS[key]:
            raise RuntimeError(
                f"{year} dataset id disagrees with config.settings.DATASET_IDS "
                f"({ASSESSMENT_DATASETS[year]} vs {DATASET_IDS[key]})"
            )


def _get(dataset_id: str, where: str, select: str, batch: int = 5000) -> list[dict]:
    """Fetch every row matching `where`, paging until the source runs dry."""
    settings = get_settings()
    rows: list[dict] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "$select": select,
                "$where": where,
                "$limit": batch,
                "$offset": offset,
                "$order": ":id",
            }
        )
        url = f"https://{settings.SOCRATA_DOMAIN}/resource/{dataset_id}.json?{query}"
        request = urllib.request.Request(url)
        if settings.has_socrata_token:
            request.add_header("X-App-Token", settings.SOCRATA_APP_TOKEN)

        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    page = json.load(response)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(4 * (attempt + 1))

        rows.extend(page)
        if len(page) < batch:
            return rows
        offset += batch


def _numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce to numbers, which is also what drops suppressed rows.

    OSPI stores suppressed cells as the literal string "NULL", so Socrata's own
    `IS NOT NULL` does not filter them out. They become NaN here instead.
    """
    for column in columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def assessment(refresh: bool = False) -> pd.DataFrame:
    """All four years of school- and district-level SBAC results."""
    _sanity_check_ids()
    cache = OUT_DIR / "assessment.csv"
    if cache.exists() and not refresh:
        return _numeric(
            pd.read_csv(cache, dtype={"districtcode": str, "schoolcode": str, "gradelevel": str}),
            ["percentlevel3", "percentlevel4", "count_of_students_expected", "proficiency"],
        )

    OUT_DIR.mkdir(exist_ok=True)
    grades = ",".join(f"'{g}'" for g in GRADES)
    frames = []
    for year, dataset_id in ASSESSMENT_DATASETS.items():
        names = [YEAR_ALIASES.get(g, {}).get(year, g) for g in STUDENT_GROUPS]
        groups = ",".join("'" + n.replace("'", "''") + "'" for n in names)
        where = (
            "testadministration='SBAC' "
            "AND (testsubject='ELA' OR testsubject='Math') "
            "AND (organizationlevel='School' OR organizationlevel='District') "
            "AND percentlevel3 IS NOT NULL "
            f"AND gradelevel in({grades}) AND studentgroup in({groups})"
        )
        frame = pd.DataFrame(_get(dataset_id, where, _ASSESSMENT_SELECT))
        # Normalise the respelled group names back to the current vocabulary.
        for canonical, aliases in YEAR_ALIASES.items():
            frame["studentgroup"] = frame["studentgroup"].replace(
                {alias: canonical for alias in aliases.values()}
            )
        print(f"  {year} ({dataset_id}): {len(frame):,} rows", flush=True)
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = _numeric(df, ["percentlevel3", "percentlevel4", "count_of_students_expected"])
    df["proficiency"] = (df["percentlevel3"] + df["percentlevel4"]) * 100
    df = df.dropna(subset=["proficiency", "count_of_students_expected"])
    df.to_csv(cache, index=False)
    print(f"  cached {len(df):,} usable rows -> {cache.relative_to(Path.cwd())}")
    return df


def enrollment(refresh: bool = False) -> pd.DataFrame:
    """Entity demographics used to band and filter, most recent year available."""
    cache = OUT_DIR / "enrollment.csv"
    if cache.exists() and not refresh:
        return pd.read_csv(cache, dtype={"districtcode": str, "schoolcode": str})

    OUT_DIR.mkdir(exist_ok=True)
    where = (
        "gradelevel='All Grades' "
        "AND (organizationlevel='School' OR organizationlevel='District')"
    )
    df = pd.DataFrame(_get(ENROLLMENT_DATASET, where, _ENROLLMENT_SELECT))
    df = _numeric(
        df,
        [
            "all_students",
            "low_income",
            "english_language_learners",
            "students_with_disabilities",
            "white",
        ],
    )
    latest = sorted(df.schoolyear.dropna().unique())[-1]
    df = df[df.schoolyear == latest]
    print(f"  enrollment ({ENROLLMENT_DATASET}, {latest}): {len(df):,} rows")
    df.to_csv(cache, index=False)
    return df


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    print("Fetching assessment data...")
    assessment(refresh=refresh)
    print("Fetching enrollment data...")
    enrollment(refresh=refresh)
