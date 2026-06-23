"""``analyze`` — ``check`` plus anomaly detection and an optional (fail-soft) LLM critique.

Deterministic first: the verdict comes from the same SLO grade and temporal detectors as ``check`` /
``watch``. The LLM only adds a non-deterministic note to the summary; if it is unreachable the
verdict is unaffected.
"""

from __future__ import annotations

import time

from ..backends import resolve_backend
from ..config import Settings
from ..eval import analyze_trends, detect_spikes
from ..llm import critique
from ..models import Issue, Report
from ..signals.stats import summarize
from ..slo import SLO
from ._assemble import assemble_report


async def analyze(
    source: str,
    *,
    slo: SLO | None = None,
    settings: Settings | None = None,
    backend: str | None = None,
    window_s: float | None = None,
    use_llm: bool = True,
) -> Report:
    """Grade deterministically, add anomaly/trend issues, and (optionally) an LLM critique."""
    settings = settings or Settings()
    started = time.perf_counter()

    be = resolve_backend(backend, settings)
    series = await be.fetch(source, window_s=window_s)

    extra: list[Issue] = []
    extra += analyze_trends(series, window_s=window_s)
    extra += detect_spikes(series, window_s=window_s)

    note: str | None = None
    model: str | None = None
    if use_llm:
        from ..models import RenderResult

        render = RenderResult(backend=be.name, series=[summarize(s) for s in series])
        try:
            note, model = critique(render, settings=settings)
        except Exception:
            # Defense in depth: the LLM critique must never affect the deterministic verdict.
            note, model = "", None
        note = note or None

    return assemble_report(
        series,
        slo,
        backend=be.name,
        source=source,
        window_s=window_s,
        capabilities=["check", "analyze"],
        extra_issues=extra,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        note=note,
        model=model,
    )
