"""The deterministic grader: measured series + an SLO → grounded issues + conformance.

No LLM, no network. ``must`` violations and unverifiable ``must`` metrics fail closed (ERROR →
FAIL); ``should`` warns; ``nice`` never escalates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agentsensory import (
    ClaimResult,
    ClaimStatus,
    Confidence,
    Conformance,
    Importance,
    Severity,
)

from ..models import Issue, IssueKind, IssueSource, Metric
from ..signals.burnrate import derived_budget_series
from ..signals.series import TimeSeries
from ..signals.stats import aggregate
from ..slo import SLO, Threshold

# How a violated requirement's importance maps to issue severity.
_SEVERITY = {
    Importance.MUST: Severity.ERROR,
    Importance.SHOULD: Severity.WARNING,
    Importance.NICE: Severity.INFO,
}

# Derived budget metrics → an error-budget-burn issue (not a generic SLO violation).
_BUDGET_METRICS = {"burn_rate", "burn_rate_fast", "error_budget_remaining"}


def _issue_kind_for(metric: str) -> IssueKind:
    return IssueKind.ERROR_BUDGET_BURN if metric in _BUDGET_METRICS else IssueKind.SLO_VIOLATION


def _issue_source_for(metric: str) -> IssueSource:
    return IssueSource.BURN_RATE if metric in _BUDGET_METRICS else IssueSource.SLO


@dataclass
class GradeResult:
    issues: list[Issue] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    conformance: Conformance | None = None


def _no_data_issue(th: Threshold, detail: str) -> Issue:
    return Issue.vital(
        IssueKind.NO_DATA,
        _SEVERITY[th.importance],
        f"cannot verify '{th.expr}': {detail}",
        source=IssueSource.SLO,
        metric=Metric(name=th.metric, observed=0.0, threshold=th.value, comparator=th.op, unit=th.unit),
        confidence=Confidence.HIGH,
    )


def evaluate(series: list[TimeSeries], slo: SLO | None) -> GradeResult:
    """Grade the measured series against an SLO (if given)."""
    by_name = {ts.name: ts for ts in series}
    result = GradeResult()

    if slo is None or slo.is_empty():
        # No intent: only flag a source that delivered nothing at all.
        if not series or all(ts.is_empty() for ts in series):
            result.issues.append(
                Issue.vital(
                    IssueKind.NO_DATA,
                    Severity.ERROR,
                    "source contained no metric data",
                    source=IssueSource.THRESHOLD,
                    confidence=Confidence.HIGH,
                )
            )
        return result

    # Compute derived budget metrics (burn_rate, error_budget_remaining) when a target is set so
    # thresholds can reference them like any other metric.
    if slo.availability_target is not None:
        for d in derived_budget_series(
            by_name, target=slo.availability_target, error_metric=slo.error_metric,
            reducer=slo.budget_reducer,
        ):
            by_name[d.name] = d

    claims: list[ClaimResult] = []
    for th in slo.thresholds:
        ts = by_name.get(th.metric)
        if ts is None or ts.is_empty():
            detail = "metric not present in source" if ts is None else "metric has no data points"
            claims.append(
                ClaimResult(
                    text=th.expr,
                    importance=th.importance,
                    status=ClaimStatus.UNCERTAIN,
                    confidence=Confidence.HIGH,
                    evidence=detail,
                    source="slo",
                )
            )
            if th.importance != Importance.NICE:
                result.issues.append(_no_data_issue(th, detail))
            continue

        observed = aggregate(ts, th.agg)
        if observed is None:
            claims.append(
                ClaimResult(
                    text=th.expr,
                    importance=th.importance,
                    status=ClaimStatus.UNCERTAIN,
                    confidence=Confidence.HIGH,
                    evidence=f"could not compute {th.agg}({th.metric})",
                    source="slo",
                )
            )
            continue

        metric = Metric(
            name=th.metric,
            observed=observed,
            threshold=th.value,
            comparator=th.op,
            unit=th.unit or ts.unit,
        )
        result.metrics.append(metric)
        ok = th.satisfied_by(observed)
        evidence = f"observed {th.agg}({th.metric})={observed:g} {th.op} {th.value:g}{th.unit} → {'ok' if ok else 'violated'}"
        claims.append(
            ClaimResult(
                text=th.expr,
                importance=th.importance,
                status=ClaimStatus.SATISFIED if ok else ClaimStatus.VIOLATED,
                confidence=Confidence.HIGH,
                evidence=evidence,
                source="slo",
            )
        )
        if not ok:
            kind = _issue_kind_for(th.metric)
            label = "error budget burning" if kind == IssueKind.ERROR_BUDGET_BURN else "SLO violated"
            result.issues.append(
                Issue.vital(
                    kind,
                    _SEVERITY[th.importance],
                    f"{label}: {th.expr} (observed {observed:g})",
                    source=_issue_source_for(th.metric),
                    metric=metric,
                    confidence=Confidence.HIGH,
                )
            )

    result.conformance = Conformance(claims=claims)
    return result
