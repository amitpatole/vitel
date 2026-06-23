"""vitel domain models — built on the ``agentsensory`` contract, never redefining it.

``Issue`` narrows ``IssueBase`` to vitals issue kinds/sources; ``Report`` extends ``ReportBase`` with
the measured signal. Every issue is grounded in a :class:`Metric` (name, window, observed vs
threshold, burn-rate), carried both on the issue (via ``detail_json``) and on ``Report.metrics``.
"""

from __future__ import annotations

import json
from enum import Enum

from agentsensory import Confidence, IssueBase, ReportBase, Severity
from pydantic import BaseModel, Field


class IssueKind(str, Enum):
    """Vitals issue kinds (grounded in a Metric)."""

    SLO_VIOLATION = "slo_violation"
    ERROR_BUDGET_BURN = "error_budget_burn"
    SATURATION = "saturation"
    LATENCY_REGRESSION = "latency_regression"
    ERROR_SPIKE = "error_spike"
    CRASHLOOP = "crashloop"
    RESOURCE_LEAK = "resource_leak"
    FLATLINE = "flatline"
    NO_DATA = "no_data"
    QUOTA_EXHAUSTION = "quota_exhaustion"
    INTENT_MISMATCH = "intent_mismatch"
    OTHER = "other"


class IssueSource(str, Enum):
    """What produced an issue."""

    THRESHOLD = "threshold"
    SLO = "slo"
    BURN_RATE = "burn_rate"
    TREND = "trend"
    ANOMALY = "anomaly"
    VITALS_LLM = "vitals_llm"


class Metric(BaseModel):
    """The grounding object behind every vitals finding."""

    name: str
    observed: float
    threshold: float | None = None
    comparator: str | None = Field(default=None, description="The SLO operator, e.g. '<', '>='.")
    unit: str = ""
    window_s: float | None = None
    burn_rate: float | None = Field(default=None, description="Error-budget burn multiple, if computed.")


class SeriesStat(BaseModel):
    """Summary statistics for one normalized time series (the trustworthy signal)."""

    name: str
    unit: str = ""
    count: int = 0
    first_ts: float | None = None
    last_ts: float | None = None
    last: float | None = None
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    p50: float | None = None
    p90: float | None = None
    p99: float | None = None
    rate_per_s: float | None = Field(default=None, description="(last-first)/(t_last-t_first).")


class RenderResult(BaseModel):
    """Normalized series + computed stats — what every grade is derived from."""

    backend: str = "unknown"
    source_label: str = ""
    window_s: float | None = None
    series: list[SeriesStat] = Field(default_factory=list)

    def stat(self, name: str) -> SeriesStat | None:
        return next((s for s in self.series if s.name == name), None)


class Issue(IssueBase):
    """A vitals issue: narrows ``kind``/``source`` to vitel enums."""

    kind: IssueKind  # type: ignore[assignment]
    source: IssueSource = IssueSource.THRESHOLD  # type: ignore[assignment]

    @classmethod
    def vital(
        cls,
        kind: IssueKind,
        severity: Severity,
        message: str,
        *,
        source: IssueSource,
        metric: Metric | None = None,
        confidence: Confidence = Confidence.HIGH,
        detail: dict | None = None,
    ) -> Issue:
        """Build a grounded vitals issue; the Metric is serialized into ``detail_json``."""
        payload = dict(detail or {})
        if metric is not None:
            payload["metric"] = metric.model_dump()
        return cls(
            kind=kind,
            severity=severity,
            message=message,
            source=source,
            confidence=confidence,
            detail_json=json.dumps(payload),
        )

    @property
    def metric(self) -> Metric | None:
        raw = self.detail.get("metric")
        return Metric.model_validate(raw) if isinstance(raw, dict) else None


class Report(ReportBase):
    """A vitals report: ``ReportBase`` + the measured signal."""

    issues: list[Issue] = Field(default_factory=list)  # type: ignore[assignment]
    metrics: list[Metric] = Field(default_factory=list)
    window_s: float | None = None
    source_label: str = ""
    capabilities: list[str] = Field(default_factory=list)


__all__ = [
    "IssueKind",
    "IssueSource",
    "Metric",
    "SeriesStat",
    "RenderResult",
    "Issue",
    "Report",
]
