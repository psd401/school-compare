"""Rank statistics and resampling tests, implemented on numpy alone.

The app does not depend on scipy and should not start depending on it for a
handful of rank correlations. These are the pieces the benchmark analysis needs.
"""

from __future__ import annotations

import math

import numpy as np


def rankdata(x) -> np.ndarray:
    """Ranks of `x`, 1-based, with ties assigned their average rank."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1)

    sorted_x = x[order]
    i = 0
    while i < len(sorted_x):
        j = i
        while j + 1 < len(sorted_x) and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + 1 + j + 1) / 2
        i = j + 1
    return ranks


def spearman(x, y) -> float:
    """Spearman rank correlation."""
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def spearman_p(x, y, n: int = 10000, seed: int = 11) -> float:
    """Two-sided permutation p-value for `spearman`, shuffling y."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    observed = abs(spearman(x, y))
    hits = sum(1 for _ in range(n) if abs(spearman(x, rng.permutation(y))) >= observed)
    return (hits + 1) / (n + 1)


def auc(a, b) -> float:
    """P(random draw from `a` exceeds a random draw from `b`); ties count half.

    0.5 means the two samples are interchangeable. Equivalent to the
    Mann-Whitney U statistic scaled to [0, 1].
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ranks = rankdata(np.concatenate([a, b]))
    u = ranks[: len(a)].sum() - len(a) * (len(a) + 1) / 2
    return float(u / (len(a) * len(b)))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion, returned as percentages.

    Preferred over the normal approximation here because the counts are small
    (a size band may hold only 26 districts).
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half) * 100, min(1.0, centre + half) * 100)


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Exact, no scipy."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def five_number(values) -> dict | None:
    """Min, quartiles, max plus the 10th/90th percentiles and the mean.

    Quartiles use linear interpolation between order statistics, matching the
    NumPy and pandas default so the figures agree with the published tables.
    """
    v = np.asarray([x for x in values if x is not None and not np.isnan(x)], dtype=float)
    if len(v) < 5:
        return None
    q1, q3 = np.percentile(v, 25), np.percentile(v, 75)
    return {
        "n": len(v),
        "min": float(v.min()),
        "p10": float(np.percentile(v, 10)),
        "q1": float(q1),
        "median": float(np.median(v)),
        "q3": float(q3),
        "p90": float(np.percentile(v, 90)),
        "max": float(v.max()),
        "iqr": float(q3 - q1),
        "mean": float(v.mean()),
    }
