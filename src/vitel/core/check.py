"""``check`` — the deterministic main path: threshold / SLO evaluation, no LLM, no egress."""

from __future__ import annotations

import time

from agentsensory import Verdict, verdict_from_issues

from ..backends import resolve_backend
from ..config import Settings
from ..eval import evaluate
from ..models import Report
from ..slo import SLO


def _summary(verdict: Verdict, n_issues: int, conformance) -> str:
    if verdict == Verdict.PASS:
        base = "vitals nominal"
    elif verdict == Verdict.WARN:
        base = "vitals degraded"
    else:
        base = "vitals failing"
    parts = [base]
    if n_issues:
        parts.append(f"{n_issues} issue{'s' if n_issues != 1 else ''}")
    if conformance is not None and conformance.total:
        parts.append(f"{conformance.satisfied}/{conformance.total} SLO checks met")
    return " — ".join(parts)


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

    graded = evaluate(series, slo)
    # graded.issues is list[Issue] (an IssueBase subclass); list is invariant for the type checker.
    verdict = verdict_from_issues(list(graded.issues))  # type: ignore[arg-type]

    return Report(
        verdict=verdict,
        summary=_summary(verdict, len(graded.issues), graded.conformance),
        issues=graded.issues,
        conformance=graded.conformance,
        metrics=graded.metrics,
        backend=be.name,
        window_s=window_s,
        source_label="<inline>" if source.strip()[:1] in ("{", "[") else source,
        capabilities=["check"],
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
