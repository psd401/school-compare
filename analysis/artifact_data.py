"""Emit the two JSON payloads embedded in the "Typical Year" artifact.

    python analysis/artifact_data.py --out <dir>

Uses the same corrected `cells()` filter as benchmarks.py, so the page and
docs/improvement-benchmarks.md are built from one pipeline.

Band labels and the arrow in transition names are display strings the page reads
verbatim — changing them changes the rendered page, not just the data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402
from benchmarks import (  # noqa: E402
    MIN_CELLS,
    PAIRS,
    TRANSITIONS,
    _weighted,
    cells,
    entity_scores,
    profile,
)
from stats_lite import binom_sf, spearman, wilson  # noqa: E402

# The page splits on this character; "->" would render as literal text.
DISPLAY_TRANSITIONS = [f"{a}→{b}" for a, b in PAIRS]

GROUPS = fetch.STUDENT_GROUPS
GROUP_LABELS = {
    "Hispanic/ Latino of any race(s)": "Hispanic/Latino",
    "Black/ African American": "Black/African American",
    "Two Or More Races": "Two or More Races",
    "English Language Learners": "Multilingual learners",
    "Students with Disabilities": "Students with disabilities",
}
# Order the page shows them in.
GROUP_ORDER = [
    "All Students", "Low-Income", "English Language Learners",
    "Students with Disabilities", "Hispanic/ Latino of any race(s)",
    "Black/ African American", "Asian", "Two Or More Races", "White",
]

# Bands the panel renders. Kept separate from benchmarks.QUARTILE_BANDS, which
# follows the published note; these give districts a 5,000 cut that matters here.
PANEL_BANDS = {
    "School": [("Under 250", 0, 250), ("250 – 500", 250, 500),
               ("500 – 750", 500, 750), ("750 or more", 750, np.inf)],
    "District": [("Under 600", 0, 600), ("600 – 1,500", 600, 1500),
                 ("1,500 – 5,000", 1500, 5000),
                 ("5,000 – 15,000", 5000, 15000), ("15,000+", 15000, np.inf)],
}
PERSIST_BANDS = {
    "School": [("Under 250", 0, 250), ("250 – 500", 250, 500),
               ("500 – 750", 500, 750), ("750 or more", 750, np.inf)],
    "District": [("Under 1,500", 0, 1500), ("1,500 – 5,000", 1500, 5000),
                 ("5,000 or more", 5000, np.inf)],
}


def _pct(part, whole):
    return np.where(whole > 0, part / whole * 100, np.nan)


def build_rows(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> dict:
    """Entity table plus one compact row per observation."""
    frames = []
    for level_index, level in enumerate(("School", "District")):
        for group_index, group in enumerate(GROUP_ORDER):
            df = cells(assessment, level, group)
            if df.empty:
                continue
            df = df.assign(level=level_index, group=group_index, organizationlevel=level)
            frames.append(df)
    observations = pd.concat(frames, ignore_index=True)

    # Names and county come from the assessment extract; demographics from
    # enrollment. Both keyed the same way cells() keys entities.
    meta = assessment.copy()
    meta["key"] = np.where(
        meta.organizationlevel == "School", meta.schoolcode, meta.districtcode
    ).astype(str)
    meta["name"] = np.where(
        meta.organizationlevel == "School", meta.schoolname, meta.districtname
    )
    meta = meta.drop_duplicates(["organizationlevel", "key"])[
        ["organizationlevel", "key", "name", "districtname", "county"]
    ]

    demo = enrollment.copy()
    demo["key"] = np.where(
        demo.organizationlevel == "School", demo.schoolcode, demo.districtcode
    ).astype(str)
    demo["lowinc"] = _pct(demo.low_income, demo.all_students)
    demo["ell"] = _pct(demo.english_language_learners, demo.all_students)
    demo["swd"] = _pct(demo.students_with_disabilities, demo.all_students)
    demo["nonwhite"] = _pct(demo.all_students - demo.white, demo.all_students)
    demo = demo[["organizationlevel", "key", "all_students", "lowinc", "ell", "swd", "nonwhite"]]

    entities = meta.merge(demo, on=["organizationlevel", "key"], how="left")
    entities = entities[entities.name.notna()].reset_index(drop=True)
    entities["idx"] = entities.index
    lookup = {(r.organizationlevel, r.key): r.idx for r in entities.itertuples()}

    observations["ei"] = [
        lookup.get((lvl, key)) for lvl, key in zip(observations.organizationlevel, observations.key)
    ]
    observations = observations[observations.ei.notna()]

    def number(value, places=0):
        if pd.isna(value):
            return None
        return round(float(value), places) if places else int(round(float(value)))

    entity_payload = [
        [
            r.name,
            r.districtname if r.organizationlevel == "School" and pd.notna(r.districtname) else "",
            number(r.all_students),
            number(r.lowinc, 1), number(r.ell, 1), number(r.swd, 1), number(r.nonwhite, 1),
            "" if pd.isna(r.county) else str(r.county),
        ]
        for r in entities.itertuples()
    ]

    transition_index = {t: i for i, t in enumerate(TRANSITIONS)}
    grade_index = {g: i for i, g in enumerate(fetch.GRADES)}
    # Prior/current stored as integer tenths: compact and lossless at 0.1 pt.
    row_payload = [
        [
            int(r.ei), int(r.level), transition_index[r.transition], grade_index[r.gradelevel],
            0 if r.testsubject == "ELA" else 1, int(r.group),
            int(round(r.proficiency_prior * 10)), int(round(r.proficiency_curr * 10)),
            int(r.cohort),
        ]
        for r in observations.itertuples()
    ]

    return {
        "transitions": DISPLAY_TRANSITIONS,
        "grades": fetch.GRADES,
        "subjects": ["ELA", "Math"],
        "levels": ["School", "District"],
        "groups": [GROUP_LABELS.get(g, g) for g in GROUP_ORDER],
        "entities": entity_payload,
        "rows": row_payload,
        "meta": {
            "source": "OSPI Report Card Assessment Data via data.wa.gov",
            "datasets": fetch.ASSESSMENT_DATASETS,
            "generator": "analysis/artifact_data.py",
        },
    }


def build_panel(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> dict:
    """Precomputed figures for the top-quartile panel."""
    payload: dict = {}
    for level in ("School", "District"):
        scores = entity_scores(assessment, level)
        sizes = profile(enrollment, level).set_index("key")
        latest = scores[scores.transition == TRANSITIONS[-1]].join(sizes, on="key")
        latest = latest.dropna(subset=["all_students"])
        high, low = latest.delta.quantile(0.75), latest.delta.quantile(0.25)

        bands = []
        for label, lo, hi in PANEL_BANDS[level]:
            band = latest[(latest.all_students >= lo) & (latest.all_students < hi)]
            if len(band) < 5:
                continue
            bands.append({
                "label": label, "n": int(len(band)),
                "top": round(float((band.delta >= high).mean() * 100), 1),
                "bot": round(float((band.delta <= low).mean() * 100), 1),
                "med": round(float(band.delta.median()), 2),
                "iqr": round(float(band.delta.quantile(0.75) - band.delta.quantile(0.25)), 2),
            })

        wide = scores.pivot(index="key", columns="transition", values="delta").join(sizes)
        wide = wide.dropna(subset=["all_students"])
        persist = []
        for label, lo, hi in [("All sizes", 0, np.inf)] + PERSIST_BANDS[level]:
            repeats = total = fell = pool = 0
            rhos = []
            for a, b in zip(TRANSITIONS[:-1], TRANSITIONS[1:]):
                subset = wide[[a, b, "all_students"]].dropna()
                subset = subset[(subset.all_students >= lo) & (subset.all_students < hi)]
                if len(subset) < 20:
                    continue
                top = subset[a] >= subset[a].quantile(0.75)
                repeats += int((top & (subset[b] >= subset[b].quantile(0.75))).sum())
                fell += int((top & (subset[b] <= subset[b].quantile(0.25))).sum())
                total += int(top.sum())
                pool = max(pool, len(subset))
                rhos.append(spearman(subset[a], subset[b]))
            if not total:
                continue
            lo_ci, hi_ci = wilson(repeats, total)
            persist.append({
                "label": label, "pool": pool, "top": total, "rep": repeats, "fall": fell,
                "rate": round(100 * repeats / total, 1),
                "ci": [round(lo_ci, 1), round(hi_ci, 1)],
                "p": round(binom_sf(repeats, total, 0.25), 3),
                "rho": round(float(np.mean(rhos)), 3),
            })

        payload[level] = {
            "cut": round(float(high), 2),
            "n": int(len(latest)),
            "corr_size": round(spearman(latest.all_students, latest.delta), 3),
            "bands": bands,
            "persistBySize": persist,
        }

    prior_null = []
    for transition in TRANSITIONS:
        df = cells(assessment, "District")
        df = df[df.transition == transition]
        prior = _weighted(df, "proficiency_prior", "cohort", ["key"])
        delta = _weighted(df, "delta", "cohort", ["key"])
        merged = prior.merge(delta[["key", "delta"]], on="key")
        merged = merged[merged.cells >= MIN_CELLS["District"]]
        prior_null.append({
            "transition": transition.replace("->", "→"),
            "rho": round(spearman(merged.proficiency_prior, merged.delta), 3),
            "n": int(len(merged)),
        })
    payload["priorNull"] = prior_null
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="directory to write data.json and topq.json")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    assessment = fetch.assessment(refresh=args.refresh)
    enrollment = fetch.enrollment(refresh=args.refresh)

    data = build_rows(assessment, enrollment)
    json.dump(data, (out / "data.json").open("w"), separators=(",", ":"), allow_nan=False)
    print(f"data.json  {len(data['rows']):,} rows, {len(data['entities']):,} entities, "
          f"{(out / 'data.json').stat().st_size / 1e6:.2f} MB")

    panel = build_panel(assessment, enrollment)
    json.dump(panel, (out / "topq.json").open("w"), separators=(",", ":"), allow_nan=False)
    print(f"topq.json  {(out / 'topq.json').stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
