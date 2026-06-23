"""Trend statistics: slope, relative change, monotonic growth — the basis of degradation detection."""

from __future__ import annotations

from .series import TimeSeries


def linear_slope(points: list[tuple[float, float]]) -> float | None:
    """Least-squares slope (value per second). ``None`` for fewer than 2 points or zero time span."""
    n = len(points)
    if n < 2:
        return None
    mean_t = sum(t for t, _ in points) / n
    mean_v = sum(v for _, v in points) / n
    num = sum((t - mean_t) * (v - mean_v) for t, v in points)
    den = sum((t - mean_t) ** 2 for t, _ in points)
    return num / den if den else None


def relative_change(ts: TimeSeries, *, head_frac: float = 0.34) -> float | None:
    """Relative change from the early window mean to the late window mean (e.g. 0.5 = +50%)."""
    vals = ts.values
    n = len(vals)
    if n < 3:
        return None
    k = max(1, int(n * head_frac))
    early = sum(vals[:k]) / k
    late = sum(vals[-k:]) / k
    if early == 0:
        return None if late == 0 else float("inf")
    return (late - early) / abs(early)


def is_monotonic_increasing(ts: TimeSeries, *, tolerance: float = 0.0) -> bool:
    """True if the series never meaningfully decreases (the shape of a resource leak)."""
    vals = ts.values
    if len(vals) < 3:
        return False
    return all(b >= a - tolerance for a, b in zip(vals, vals[1:], strict=False))
