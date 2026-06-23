"""Temporal detectors: latency regression, resource leak, error spike — over a window of samples.

These run in ``watch`` (and ``analyze``) on top of the deterministic ``check``. They are heuristic
and grounded in a Metric, so a brain can act on them but treat them as WARN-level signals unless a
hard SLO also trips.
"""

from __future__ import annotations

from agentsensory import Confidence, Severity

from ..models import Issue, IssueKind, IssueSource, Metric
from ..signals.series import TimeSeries
from ..signals.stats import percentile
from ..signals.trend import is_monotonic_increasing, linear_slope, relative_change

_LATENCY_HINTS = ("latency", "duration", "_ms", "response_time", "resp_time")
_MEMORY_HINTS = ("mem", "rss", "heap", "memory")

# A regression/leak must rise by at least this fraction across the window to be flagged.
REGRESSION_MIN_INCREASE = 0.25
LEAK_MIN_INCREASE = 0.20
SPIKE_Z = 3.0


def _is_latency(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _LATENCY_HINTS)


def _is_memory(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _MEMORY_HINTS)


def _metric(ts: TimeSeries, observed: float, *, window_s: float | None) -> Metric:
    return Metric(name=ts.name, observed=observed, unit=ts.unit, window_s=window_s)


def analyze_trends(series: list[TimeSeries], *, window_s: float | None = None) -> list[Issue]:
    """Flag slow latency regressions and monotonic resource leaks across the window."""
    issues: list[Issue] = []
    for ts in series:
        rel = relative_change(ts)
        slope = linear_slope(ts.points)
        if rel is None or slope is None:
            continue

        if _is_latency(ts.name) and slope > 0 and rel >= REGRESSION_MIN_INCREASE:
            sev = Severity.ERROR if rel >= 1.0 else Severity.WARNING
            issues.append(
                Issue.vital(
                    IssueKind.LATENCY_REGRESSION,
                    sev,
                    f"latency regression in '{ts.name}': +{rel * 100:.0f}% across the window "
                    f"(last {ts.last():g}{ts.unit})",
                    source=IssueSource.TREND,
                    metric=_metric(ts, ts.last() or 0.0, window_s=window_s),
                    confidence=Confidence.MEDIUM,
                )
            )
        elif _is_memory(ts.name) and rel >= LEAK_MIN_INCREASE and is_monotonic_increasing(ts):
            issues.append(
                Issue.vital(
                    IssueKind.RESOURCE_LEAK,
                    Severity.WARNING,
                    f"possible resource leak in '{ts.name}': monotonic +{rel * 100:.0f}% across the window",
                    source=IssueSource.TREND,
                    metric=_metric(ts, ts.last() or 0.0, window_s=window_s),
                    confidence=Confidence.MEDIUM,
                )
            )
    return issues


def detect_flatline(series: list[TimeSeries], *, min_points: int = 5) -> list[Issue]:
    """Liveness signal: a metric that should vary but is perfectly flat across many samples (INFO)."""
    issues: list[Issue] = []
    for ts in series:
        vals = ts.values
        if len(vals) >= min_points and len(set(vals)) == 1:
            issues.append(
                Issue.vital(
                    IssueKind.FLATLINE,
                    Severity.INFO,
                    f"'{ts.name}' is flat at {vals[0]:g} across {len(vals)} samples (liveness?)",
                    source=IssueSource.TREND,
                    metric=_metric(ts, vals[0], window_s=None),
                    confidence=Confidence.LOW,
                )
            )
    return issues


def detect_spikes(series: list[TimeSeries], *, window_s: float | None = None) -> list[Issue]:
    """Flag a latest-sample anomaly: the final point is a >Zσ outlier above the window mean."""
    issues: list[Issue] = []
    for ts in series:
        vals = ts.values
        if len(vals) < 5:
            continue
        body = vals[:-1]
        mean = sum(body) / len(body)
        var = sum((v - mean) ** 2 for v in body) / len(body)
        std = var**0.5
        if std == 0:
            continue
        z = (vals[-1] - mean) / std
        if z >= SPIKE_Z:
            p95 = percentile(body, 95) or mean
            issues.append(
                Issue.vital(
                    IssueKind.ERROR_SPIKE,
                    Severity.WARNING,
                    f"anomaly in '{ts.name}': latest {vals[-1]:g} is {z:.1f}σ above the window "
                    f"(p95 {p95:g})",
                    source=IssueSource.ANOMALY,
                    metric=_metric(ts, vals[-1], window_s=window_s),
                    confidence=Confidence.MEDIUM,
                )
            )
    return issues
