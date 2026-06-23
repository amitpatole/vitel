"""``watch`` — grade a source over time: trend, ongoing degradation, liveness.

For a live source (scrape / psutil / cloud) with an ``interval``, watch polls and accumulates a
series before analyzing. For a source that already carries a window of samples (file / OTLP /
Prometheus range), it analyzes those directly. On top of the SLO grade it runs temporal detectors:
slow latency regression, monotonic resource leak, error spike, and flatline (liveness).
"""

from __future__ import annotations

import asyncio
import time

from ..backends import resolve_backend
from ..config import Settings
from ..eval import analyze_trends, detect_flatline, detect_spikes
from ..models import Issue, Report
from ..signals.series import TimeSeries
from ..slo import SLO
from ._assemble import assemble_report

_LIVE_BACKENDS = {"scrape", "prometheus", "psutil", "datadog", "cloudwatch"}


async def _poll(be, source: str, window_s: float, interval: float, settings: Settings) -> list[TimeSeries]:
    """Poll a single-snapshot backend every ``interval`` seconds, accumulating a series."""
    polls = max(2, int(window_s / interval))
    polls = min(polls, settings.max_points)
    acc: dict[str, TimeSeries] = {}
    start = time.monotonic()
    for i in range(polls):
        snap = await be.fetch(source, window_s=interval)
        t = time.monotonic() - start
        for s in snap:
            v = s.last()
            if v is None:
                continue
            acc.setdefault(s.name, TimeSeries(name=s.name, unit=s.unit)).points.append((t, v))
        if i < polls - 1:
            await asyncio.sleep(interval)
    return list(acc.values())


async def watch(
    source: str,
    *,
    window: float | None = None,
    interval: float | None = None,
    slo: SLO | None = None,
    settings: Settings | None = None,
    backend: str | None = None,
) -> Report:
    """Grade ``source`` over a window, flagging temporal degradation."""
    settings = settings or Settings()
    started = time.perf_counter()
    be = resolve_backend(backend, settings)

    if interval and interval > 0 and be.name in _LIVE_BACKENDS:
        series = await _poll(be, source, window or interval * 5, interval, settings)
    else:
        series = await be.fetch(source, window_s=window)

    extra: list[Issue] = []
    extra += analyze_trends(series, window_s=window)
    extra += detect_spikes(series, window_s=window)
    extra += detect_flatline(series)

    return assemble_report(
        series,
        slo,
        backend=be.name,
        source=source,
        window_s=window,
        capabilities=["watch"],
        extra_issues=extra,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
