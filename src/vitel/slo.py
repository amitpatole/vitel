"""``SLO`` / ``BudgetSpec`` — the vitals analog of ``agentsensory.Brief``.

A telemetry artifact is graded against a set of thresholds parsed from human expectations like
``"must: p99(latency_ms) < 300ms"`` or ``"should: error_rate < 1%"``. Importance (must/should/nice)
is parsed by the contract's :func:`agentsensory.IntentClaim.parse`; the threshold expression is
parsed here.
"""

from __future__ import annotations

import re

from agentsensory import Importance, IntentClaim
from pydantic import BaseModel, Field

# agg(metric) OP number[unit]   e.g.  p99(latency_ms) < 300ms
_AGG = re.compile(
    r"^\s*([A-Za-z][\w]*)\s*\(\s*([A-Za-z_][\w.:]*)\s*\)\s*(<=|>=|==|!=|<|>)\s*"
    r"([+-]?[0-9.]+)\s*([A-Za-z%/]*)\s*$"
)
# metric OP number[unit]        e.g.  error_rate < 1%
_BARE = re.compile(
    r"^\s*([A-Za-z_][\w.:]*)\s*(<=|>=|==|!=|<|>)\s*([+-]?[0-9.]+)\s*([A-Za-z%/]*)\s*$"
)

_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class Threshold(BaseModel):
    """One parsed, checkable requirement."""

    raw: str
    importance: Importance = Importance.MUST
    metric: str
    agg: str = "last"
    op: str
    value: float
    unit: str = ""

    @property
    def expr(self) -> str:
        lhs = self.metric if self.agg == "last" else f"{self.agg}({self.metric})"
        return f"{lhs} {self.op} {self.value}{self.unit}".strip()

    def satisfied_by(self, observed: float) -> bool:
        return _OPS[self.op](observed, self.value)


def parse_threshold(text: str, *, importance: Importance = Importance.MUST) -> Threshold | None:
    """Parse a single threshold expression. ``None`` if it is not a recognizable threshold."""
    m = _AGG.match(text)
    if m:
        agg, metric, op, num, unit = m.groups()
    else:
        m = _BARE.match(text)
        if not m:
            return None
        metric, op, num, unit = m.groups()
        agg = "last"
    value = float(num)
    if unit == "%":  # percent → ratio, so "error_rate < 1%" compares against 0.01
        value /= 100.0
        unit = "ratio"
    return Threshold(
        raw=text.strip(), importance=importance, metric=metric, agg=agg.lower(), op=op,
        value=value, unit=unit,
    )


class SLO(BaseModel):
    """A service-level objective / error-budget spec: the intent vitals are graded against."""

    text: str | None = None
    thresholds: list[Threshold] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.text and not self.thresholds

    @classmethod
    def from_inputs(
        cls,
        *,
        text: str | None = None,
        expect: list[str] | None = None,
    ) -> SLO:
        """Build from CLI/REST-style inputs (``--slo`` text + repeated ``--expect``).

        Each ``expect`` string is parsed for a ``must:``/``should:``/``nice:`` prefix (via the
        contract) and then for a threshold expression. Unparseable expectations are skipped.
        """
        thresholds: list[Threshold] = []
        for raw in expect or []:
            if not raw or not raw.strip():
                continue
            claim = IntentClaim.parse(raw)
            th = parse_threshold(claim.text, importance=claim.importance)
            if th is not None:
                thresholds.append(th)
        return cls(text=text, thresholds=thresholds)
