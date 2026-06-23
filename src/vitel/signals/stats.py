"""Deterministic statistics over a :class:`TimeSeries` — no numpy in the light base."""

from __future__ import annotations

from ..models import SeriesStat
from .series import TimeSeries


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolation percentile (``q`` in 0..100). ``None`` for an empty series."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    rank = (q / 100.0) * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def _rate_per_s(ts: TimeSeries) -> float | None:
    if len(ts.points) < 2:
        return None
    (t0, v0), (t1, v1) = ts.points[0], ts.points[-1]
    span = t1 - t0
    return (v1 - v0) / span if span > 0 else None


def summarize(ts: TimeSeries) -> SeriesStat:
    """Reduce a series to its summary statistics."""
    vals = ts.values
    if not vals:
        return SeriesStat(name=ts.name, unit=ts.unit, count=0)
    return SeriesStat(
        name=ts.name,
        unit=ts.unit,
        count=len(vals),
        first_ts=ts.timestamps[0],
        last_ts=ts.timestamps[-1],
        last=vals[-1],
        min=min(vals),
        max=max(vals),
        mean=sum(vals) / len(vals),
        p50=percentile(vals, 50),
        p90=percentile(vals, 90),
        p99=percentile(vals, 99),
        rate_per_s=_rate_per_s(ts),
    )


# Aggregators usable in SLO metric expressions, e.g. ``p99(latency_ms)`` or ``max(cpu)``.
def aggregate(ts: TimeSeries, agg: str) -> float | None:
    vals = ts.values
    if not vals:
        return None
    agg = agg.lower()
    if agg == "last":
        return vals[-1]
    if agg in ("min",):
        return min(vals)
    if agg in ("max",):
        return max(vals)
    if agg in ("mean", "avg"):
        return sum(vals) / len(vals)
    if agg == "sum":
        return sum(vals)
    if agg == "rate":
        return _rate_per_s(ts)
    if agg.startswith("p"):
        try:
            q = float(agg[1:])
        except ValueError:
            return None
        return percentile(vals, q)
    return None
