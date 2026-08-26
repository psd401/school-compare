"""Regenerate every figure in docs/improvement-benchmarks.md.

    python analysis/benchmarks.py all
    python analysis/benchmarks.py summary size persistence
    python analysis/benchmarks.py all --refresh     # re-pull from data.wa.gov

Sections: summary, size, quartile, persistence, validity, threeyear.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402
from stats_lite import binom_sf, five_number, spearman, spearman_p, wilson  # noqa: E402

YEARS = list(fetch.ASSESSMENT_DATASETS)
PAIRS = list(zip(YEARS[:-1], YEARS[1:]))
TRANSITIONS = [f"{a}->{b}" for a, b in PAIRS]

# A cell must have this many tested students in BOTH years to be used at all.
MIN_COHORT = 20
# An entity needs this many surviving grade x subject cells before its weighted
# score means anything. Districts span more grades than a single school does.
MIN_CELLS = {"School": 2, "District": 4}

SIZE_BANDS = {
    "School": [("Under 250", 0, 250), ("250-500", 250, 500), ("500-750", 500, 750),
               ("750 or more", 750, np.inf)],
    "District": [("Under 1,500", 0, 1500), ("1,500-5,000", 1500, 5000),
                 ("5,000 or more", 5000, np.inf)],
}
COHORT_BANDS = [("20-40", 20, 40), ("41-60", 41, 60), ("61-100", 61, 100),
                ("101-150", 101, 150), ("Over 150", 151, np.inf)]
QUARTILE_BANDS = {
    "School": [("Under 250", 0, 250), ("250-500", 250, 500), ("500-750", 500, 750),
               ("750 or more", 750, np.inf)],
    "District": [("Under 600", 0, 600), ("600-1,500", 600, 1500),
                 ("1,500-4,000", 1500, 4000), ("4,000-12,000", 4000, 12000),
                 ("12,000+", 12000, np.inf)],
}


# --------------------------------------------------------------------------- #
# shaping
# --------------------------------------------------------------------------- #

def _key(df: pd.DataFrame) -> pd.Series:
    return np.where(df.organizationlevel == "School", df.schoolcode, df.districtcode)


def cells(assessment: pd.DataFrame, level: str, group: str = "All Students") -> pd.DataFrame:
    """One row per entity x grade x subject x transition, with the change."""
    df = assessment[
        (assessment.organizationlevel == level) & (assessment.studentgroup == group)
    ].copy()
    df["key"] = _key(df).astype(str)

    index = ["key", "gradelevel", "testsubject"]
    frames = []
    for year_a, year_b in PAIRS:
        a = df[df.schoolyear == year_a].set_index(index)[
            ["proficiency", "count_of_students_expected"]
        ]
        b = df[df.schoolyear == year_b].set_index(index)[
            ["proficiency", "count_of_students_expected"]
        ]
        a, b = a[~a.index.duplicated()], b[~b.index.duplicated()]
        joined = a.join(b, lsuffix="_prior", rsuffix="_curr", how="inner").reset_index()
        joined["cohort"] = joined[
            ["count_of_students_expected_prior", "count_of_students_expected_curr"]
        ].min(axis=1)
        joined["delta"] = joined.proficiency_curr - joined.proficiency_prior
        joined["transition"] = f"{year_a}->{year_b}"
        frames.append(joined)

    out = pd.concat(frames, ignore_index=True).dropna(subset=["delta", "cohort"])
    return out[out.cohort >= MIN_COHORT]


def _weighted(df: pd.DataFrame, value: str, weight: str, by: list[str]) -> pd.DataFrame:
    """Weighted mean of `value` by `weight`, grouped by `by`.

    Done with plain sums rather than groupby.apply, which changes behaviour
    across pandas versions.
    """
    work = df.copy()
    work["_wv"] = work[value] * work[weight]
    agg = work.groupby(by).agg(_wv=("_wv", "sum"), _w=(weight, "sum"), cells=(value, "size"))
    agg[value] = agg._wv / agg._w
    return agg.drop(columns=["_wv", "_w"]).reset_index()


def entity_scores(assessment: pd.DataFrame, level: str) -> pd.DataFrame:
    """One enrollment-weighted improvement score per entity per transition."""
    df = cells(assessment, level)
    scored = _weighted(df, "delta", "cohort", ["transition", "key"])
    return scored[scored.cells >= MIN_CELLS[level]]


def profile(enrollment: pd.DataFrame, level: str) -> pd.DataFrame:
    """Entity enrollment, keyed the same way as the scores."""
    df = enrollment[enrollment.organizationlevel == level].copy()
    df["key"] = (df.schoolcode if level == "School" else df.districtcode).astype(str)
    return df[["key", "all_students"]].drop_duplicates("key")


def names(assessment: pd.DataFrame, level: str) -> pd.Series:
    df = assessment[assessment.organizationlevel == level].copy()
    df["key"] = _key(df).astype(str)
    column = "schoolname" if level == "School" else "districtname"
    return df.drop_duplicates("key").set_index("key")[column]


# --------------------------------------------------------------------------- #
# output helpers
# --------------------------------------------------------------------------- #

def heading(text: str) -> None:
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def signed(value: float | None, places: int = 1) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    return f"{value:+.{places}f}"


def five_row(label: str, stats: dict | None, width: int = 26) -> str:
    if not stats:
        return f"{label:{width}}{'(too few observations)':>50}"
    return (
        f"{label:{width}}{stats['n']:>7,}"
        + "".join(
            f"{signed(stats[k]):>8}"
            for k in ("min", "p10", "q1", "median", "q3", "p90", "max")
        )
        + f"{stats['iqr']:>7.1f}"
    )


FIVE_HEADER = (
    f"{'':26}{'n':>7}{'min':>8}{'p10':>8}{'Q1':>8}{'median':>8}"
    f"{'Q3':>8}{'p90':>8}{'max':>8}{'IQR':>7}"
)


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #

def section_summary(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading("Five-number summary of one-year change (percentage points)")
    print(f"All Students, tested cohort >= {MIN_COHORT}, latest transition "
          f"({TRANSITIONS[-1]})\n")
    print(FIVE_HEADER)
    for level in ("School", "District"):
        df = cells(assessment, level)
        df = df[df.transition == TRANSITIONS[-1]]
        for subject in ("ELA", "Math"):
            subset = df[df.testsubject == subject]
            print(five_row(f"{level} / {subject}", five_number(subset.delta)))

    print("\nBy grade, schools, latest transition:\n")
    print(FIVE_HEADER)
    df = cells(assessment, "School")
    df = df[df.transition == TRANSITIONS[-1]]
    for subject in ("ELA", "Math"):
        for grade in fetch.GRADES:
            subset = df[(df.testsubject == subject) & (df.gradelevel == grade)]
            print(five_row(f"{subject} / grade {grade}", five_number(subset.delta)))
        print()

    print("Share of school observations clearing each threshold, latest transition:\n")
    df = cells(assessment, "School")
    df = df[df.transition == TRANSITIONS[-1]]
    for subject in ("ELA", "Math"):
        subset = df[df.testsubject == subject].delta
        parts = [f"declined {100 * (subset < 0).mean():.0f}%"]
        parts += [f">=+{t} {100 * (subset >= t).mean():.0f}%" for t in (3, 5, 10)]
        print(f"  {subject:6}" + "   ".join(parts))

    heading("Districts of 5,000 or more students, latest transition")
    big = set(profile(enrollment, "District").query("all_students >= 5000").key)
    df = cells(assessment, "District")
    df = df[(df.transition == TRANSITIONS[-1]) & (df.key.isin(big))]
    print(f"{len(df.key.unique())} districts\n")
    print(FIVE_HEADER)
    for subject in ("ELA", "Math"):
        print(five_row(f"{subject}, all grades", five_number(df[df.testsubject == subject].delta)))


def section_size(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading("Cohort size sets the spread (schools, both subjects, latest transition)")
    df = cells(assessment, "School")
    df = df[df.transition == TRANSITIONS[-1]]
    print(f"{'tested cohort':16}{'n':>7}{'Q1':>8}{'median':>8}{'Q3':>8}{'IQR':>7}")
    for label, low, high in COHORT_BANDS:
        band = df[(df.cohort >= low) & (df.cohort <= high)]
        stats = five_number(band.delta)
        if stats:
            print(f"{label:16}{stats['n']:>7,}{signed(stats['q1']):>8}"
                  f"{signed(stats['median']):>8}{signed(stats['q3']):>8}{stats['iqr']:>7.1f}")
    print("\nThe median barely moves; the spread more than halves.")


def section_quartile(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading("Who lands in the top quartile (weighted score, latest transition)")
    for level in ("School", "District"):
        scores = entity_scores(assessment, level)
        scores = scores[scores.transition == TRANSITIONS[-1]]
        scores = scores.merge(profile(enrollment, level), on="key", how="left").dropna(
            subset=["all_students"]
        )
        hi, lo = scores.delta.quantile(0.75), scores.delta.quantile(0.25)
        print(f"\n{level}s  (n={len(scores):,}, top-quartile cut {signed(hi)}, "
              f"rho(enrollment, change) = {spearman(scores.all_students, scores.delta):+.3f})")
        print(f"  {'size band':16}{'n':>6}{'% top':>8}{'% bottom':>10}{'median':>9}{'IQR':>7}")
        for label, low, high in QUARTILE_BANDS[level]:
            band = scores[(scores.all_students >= low) & (scores.all_students < high)]
            if len(band) < 5:
                continue
            iqr = band.delta.quantile(0.75) - band.delta.quantile(0.25)
            print(f"  {label:16}{len(band):>6,}{100 * (band.delta >= hi).mean():>8.1f}"
                  f"{100 * (band.delta <= lo).mean():>10.1f}"
                  f"{signed(band.delta.median()):>9}{iqr:>7.2f}")
    print("\nSmall entities fill both tails, which is what noise looks like.")


def section_persistence(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading("Does a top-quartile year carry into the next one?")
    print("Entities ranked against their own size peers, pooled over both year pairs.\n")
    for level in ("School", "District"):
        scores = entity_scores(assessment, level)
        wide = scores.pivot(index="key", columns="transition", values="delta")
        wide = wide.join(profile(enrollment, level).set_index("key")).dropna(
            subset=["all_students"]
        )
        print(f"\n{level}s")
        print(f"  {'size band':16}{'pool':>7}{'top':>6}{'repeat':>8}{'rate':>7}"
              f"{'95% CI':>14}{'P(>=k)':>9}{'rho':>8}")
        for label, low, high in [("All sizes", 0, np.inf)] + SIZE_BANDS[level]:
            repeats = total = fell = 0
            rhos, pool = [], 0
            for a, b in zip(TRANSITIONS[:-1], TRANSITIONS[1:]):
                subset = wide[[a, b, "all_students"]].dropna()
                subset = subset[
                    (subset.all_students >= low) & (subset.all_students < high)
                ]
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
            low_ci, high_ci = wilson(repeats, total)
            print(f"  {label:16}{pool:>7,}{total:>6}{repeats:>8}"
                  f"{100 * repeats / total:>6.0f}%{f'{low_ci:.0f}-{high_ci:.0f}%':>14}"
                  f"{binom_sf(repeats, total, 0.25):>9.3f}{np.mean(rhos):>+8.2f}")
    print("\n25% is the chance rate. Rates below it mean reversion, not progress.")


def section_validity(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading("What predicts improvement, and what only looks like it does")
    big = set(profile(enrollment, "District").query("all_students >= 5000").key)

    print("\n1. Starting proficiency against subsequent gain (districts)")
    for transition, (year_a, _) in zip(TRANSITIONS, PAIRS):
        df = cells(assessment, "District")
        df = df[df.transition == transition]
        prior = _weighted(df, "proficiency_prior", "cohort", ["key"])
        delta = _weighted(df, "delta", "cohort", ["key"])
        merged = prior.merge(delta[["key", "delta"]], on="key")
        merged = merged[merged.cells >= MIN_CELLS["District"]]
        print(f"   {transition:22} rho = "
              f"{spearman(merged.proficiency_prior, merged.delta):+.3f}   n={len(merged)}")
    print("   Effectively zero throughout: gains are comparable across starting points.")

    print("\n2. The statewide-drift trap (districts of 1,500+)")
    scores = entity_scores(assessment, "District")
    wide = scores.pivot(index="key", columns="transition", values="delta").dropna()
    wide = wide.join(profile(enrollment, "District").set_index("key")).dropna(
        subset=["all_students"]
    )
    wide = wide[wide.all_students >= 1500]
    rates = [float((wide[t] > 0).mean()) for t in TRANSITIONS]
    observed = int(np.logical_and.reduce([wide[t] > 0 for t in TRANSITIONS]).sum())
    print(f"   gained in every year: {observed} of {len(wide)}")
    print(f"   share gaining each year: " + ", ".join(f"{100 * r:.0f}%" for r in rates))
    print(f"   expected from a coin flip: {len(wide) * 0.125:.1f}  <-- the wrong null")
    print(f"   expected from those rates: {len(wide) * np.prod(rates):.1f}  <-- the right one")

    print("\n3. Do different students in the same district move together?")
    print("   (three-year gain, districts of 5,000+)")

    def gain(grades=None, subject=None, min_cells=2):
        df = assessment[(assessment.organizationlevel == "District")
                        & (assessment.studentgroup == "All Students")].copy()
        df["key"] = df.districtcode.astype(str)
        if grades:
            df = df[df.gradelevel.isin(grades)]
        if subject:
            df = df[df.testsubject == subject]
        index = ["key", "gradelevel", "testsubject"]
        a = df[df.schoolyear == YEARS[0]].set_index(index)[
            ["proficiency", "count_of_students_expected"]]
        b = df[df.schoolyear == YEARS[-1]].set_index(index)[
            ["proficiency", "count_of_students_expected"]]
        a, b = a[~a.index.duplicated()], b[~b.index.duplicated()]
        j = a.join(b, lsuffix="_p", rsuffix="_c", how="inner").reset_index()
        j["cohort"] = j[["count_of_students_expected_p", "count_of_students_expected_c"]].min(axis=1)
        j = j[j.cohort >= MIN_COHORT]
        start = _weighted(j, "proficiency_p", "cohort", ["key"])
        end = _weighted(j, "proficiency_c", "cohort", ["key"])
        merged = start.merge(end[["key", "proficiency_c"]], on="key")
        merged = merged[merged.cells >= min_cells]
        merged["gain"] = merged.proficiency_c - merged.proficiency_p
        return merged.set_index("key").gain

    def compare(left, right, label):
        joined = pd.concat([left.rename("a"), right.rename("b")], axis=1).dropna()
        joined = joined[joined.index.isin(big)]
        if len(joined) < 20:
            print(f"   {label:44} n={len(joined)}, too few")
            return
        rho = spearman(joined.a, joined.b)
        p = spearman_p(joined.a, joined.b, n=10000)
        flag = " *" if p < 0.05 else ""
        print(f"   {label:44} rho={rho:+.3f}  p={p:.4f}  n={len(joined)}{flag}")

    compare(gain(["03", "04"]), gain(["05"]), "elementary: grades 3+4 vs grade 5")
    compare(gain(["06", "07"]), gain(["08"]), "middle: grades 6+7 vs grade 8")
    compare(gain(["06", "07", "08"]), gain(["10"], min_cells=1), "middle 6-8 vs grade 10")
    compare(gain(["03", "04", "05"]), gain(["06", "07", "08"]),
            "elementary 3-5 vs middle 6-8")
    compare(gain(subject="ELA"), gain(subject="Math"),
            "ELA vs Math (SAME children -- inflated)")
    print("   Within a band, separate cohorts agree. Across bands they do not.")


def section_threeyear(assessment: pd.DataFrame, enrollment: pd.DataFrame) -> None:
    heading(f"Three-year total change, {YEARS[0]} to {YEARS[-1]}, districts of 5,000+")
    df = assessment[(assessment.organizationlevel == "District")
                    & (assessment.studentgroup == "All Students")].copy()
    df["key"] = df.districtcode.astype(str)

    def totals(grades, min_cells):
        subset = df[df.gradelevel.isin(grades)]
        index = ["key", "gradelevel", "testsubject"]
        a = subset[subset.schoolyear == YEARS[0]].set_index(index)[
            ["proficiency", "count_of_students_expected"]]
        b = subset[subset.schoolyear == YEARS[-1]].set_index(index)[
            ["proficiency", "count_of_students_expected"]]
        a, b = a[~a.index.duplicated()], b[~b.index.duplicated()]
        j = a.join(b, lsuffix="_p", rsuffix="_c", how="inner").reset_index()
        j["cohort"] = j[["count_of_students_expected_p", "count_of_students_expected_c"]].min(axis=1)
        j = j[j.cohort >= MIN_COHORT]
        start = _weighted(j, "proficiency_p", "cohort", ["key"])
        end = _weighted(j, "proficiency_c", "cohort", ["key"])
        merged = start.merge(end[["key", "proficiency_c"]], on="key")
        merged = merged[merged.cells >= min_cells].set_index("key")
        merged["total"] = merged.proficiency_c - merged.proficiency_p
        return merged

    overall = totals(fetch.GRADES, MIN_CELLS["District"])
    bands = {
        "elem": totals(["03", "04", "05"], 2).total,
        "mid": totals(["06", "07", "08"], 2).total,
        "hs": totals(["10"], 1).total,
    }
    table = overall.join(pd.DataFrame(bands))
    table = table.join(profile(enrollment, "District").set_index("key"))
    table = table.join(names(assessment, "District").rename("name"))
    table = table[table.all_students >= 5000].sort_values("total", ascending=False)

    stats = five_number(table.total)
    print(f"n={stats['n']} districts")
    print(f"  min {signed(stats['min'])}  Q1 {signed(stats['q1'])}  "
          f"median {signed(stats['median'])}  Q3 {signed(stats['q3'])}  "
          f"max {signed(stats['max'])}")
    for threshold in (4, 3, 2, 0):
        share = 100 * (table.total >= threshold).mean() if threshold else \
            100 * (table.total > 0).mean()
        label = "gained anything" if threshold == 0 else f"reached +{threshold}"
        print(f"  {label:18} {share:>4.0f}%")

    print(f"\nCleared +4.0, with the grade-band decomposition:\n")
    print(f"{'district':36}{'enroll':>8}{'total':>8}{'gr 3-5':>9}{'gr 6-8':>9}{'gr 10':>8}")
    for _, row in table[table.total >= 4].iterrows():
        print(f"{str(row['name'])[:35]:36}{int(row.all_students):>8,}"
              f"{signed(row.total, 2):>8}{signed(row.elem, 2):>9}"
              f"{signed(row['mid'], 2):>9}{signed(row.hs, 2):>8}")

    print("\nSustained annual gains -- has any district cleared +3 every year?")
    scores = entity_scores(assessment, "District")
    wide = scores.pivot(index="key", columns="transition", values="delta").dropna()
    wide = wide.join(profile(enrollment, "District").set_index("key")).dropna(
        subset=["all_students"])
    wide = wide[wide.all_students >= 5000]
    hits = (wide[TRANSITIONS] >= 3).sum(axis=1)
    print(f"  of {len(wide)} districts: "
          + ", ".join(f"{int((hits == k).sum())} hit +3 in {k} year(s)" for k in range(4)))
    consecutive = sum(
        int(((wide[a] >= 3) & (wide[b] >= 3)).any())
        for a, b in zip(TRANSITIONS[:-1], TRANSITIONS[1:])
    )
    print(f"  two consecutive years at +3 or better: {consecutive}")
    best = wide[TRANSITIONS].min(axis=1).sort_values(ascending=False)
    top_key = best.index[0]
    print(f"  best floor (smallest single-year gain): "
          f"{names(assessment, 'District').get(top_key, top_key)} at {signed(best.iloc[0], 2)}")


SECTIONS = {
    "summary": section_summary,
    "size": section_size,
    "quartile": section_quartile,
    "persistence": section_persistence,
    "validity": section_validity,
    "threeyear": section_threeyear,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sections", nargs="+", choices=list(SECTIONS) + ["all"])
    parser.add_argument("--refresh", action="store_true",
                        help="re-pull from data.wa.gov instead of using out/*.csv")
    args = parser.parse_args()

    assessment = fetch.assessment(refresh=args.refresh)
    enrollment = fetch.enrollment(refresh=args.refresh)

    chosen = list(SECTIONS) if "all" in args.sections else args.sections
    for name in chosen:
        SECTIONS[name](assessment, enrollment)
    print()


if __name__ == "__main__":
    main()
