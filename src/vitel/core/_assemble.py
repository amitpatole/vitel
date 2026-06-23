"""Shared Report assembly for check / watch / analyze."""

from __future__ import annotations

from agentsensory import Verdict, verdict_from_issues

from ..eval import evaluate
from ..models import Issue, Report
from ..signals.series import TimeSeries
from ..slo import SLO


def summarize_verdict(verdict: Verdict, n_issues: int, conformance) -> str:
    base = {Verdict.PASS: "vitals nominal", Verdict.WARN: "vitals degraded"}.get(
        verdict, "vitals failing"
    )
    parts = [base]
    if n_issues:
        parts.append(f"{n_issues} issue{'s' if n_issues != 1 else ''}")
    if conformance is not None and conformance.total:
        parts.append(f"{conformance.satisfied}/{conformance.total} SLO checks met")
    return " — ".join(parts)


def assemble_report(
    series: list[TimeSeries],
    slo: SLO | None,
    *,
    backend: str,
    source: str,
    window_s: float | None,
    capabilities: list[str],
    extra_issues: list[Issue] | None = None,
    elapsed_ms: int = 0,
    note: str | None = None,
    model: str | None = None,
) -> Report:
    """Grade ``series`` against ``slo`` and fold in any extra (trend/anomaly/LLM) issues."""
    graded = evaluate(series, slo)
    issues: list[Issue] = list(graded.issues) + list(extra_issues or [])
    verdict = verdict_from_issues(list(issues))  # type: ignore[arg-type]
    summary = summarize_verdict(verdict, len(issues), graded.conformance)
    if note:
        summary = f"{summary} — {note}"
    return Report(
        verdict=verdict,
        summary=summary,
        issues=issues,
        conformance=graded.conformance,
        metrics=graded.metrics,
        backend=backend,
        model=model,
        window_s=window_s,
        source_label="<inline>" if source.strip()[:1] in ("{", "[") else source,
        capabilities=capabilities,
        elapsed_ms=elapsed_ms,
    )
