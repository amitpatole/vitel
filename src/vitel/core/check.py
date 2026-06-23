"""``check`` — the deterministic main path: threshold / SLO evaluation, no LLM, no egress."""

from __future__ import annotations

import time

from ..backends import resolve_backend
from ..config import Settings
from ..models import Report
from ..slo import SLO
from ._assemble import assemble_report


async def check(
    source: str,
    *,
    slo: SLO | None = None,
    settings: Settings | None = None,
    backend: str | None = None,
    window_s: float | None = None,
) -> Report:
    """Grade a telemetry source deterministically against ``slo`` (thresholds / SLO / budget)."""
    settings = settings or Settings()
    started = time.perf_counter()

    be = resolve_backend(backend, settings)
    series = await be.fetch(source, window_s=window_s)

    return assemble_report(
        series,
        slo,
        backend=be.name,
        source=source,
        window_s=window_s,
        capabilities=["check"],
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
