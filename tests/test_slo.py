"""SLO parsing + conformance grading."""

from __future__ import annotations

from agentsensory import Importance

from vitel.signals.series import TimeSeries
from vitel.signals.stats import aggregate, percentile
from vitel.slo import SLO, parse_threshold


def test_parse_percent_to_ratio() -> None:
    th = parse_threshold("error_rate < 1%")
    assert th is not None
    assert th.metric == "error_rate" and th.op == "<" and abs(th.value - 0.01) < 1e-9


def test_parse_aggregate_expression() -> None:
    th = parse_threshold("p99(latency_ms) <= 300ms")
    assert th is not None
    assert th.agg == "p99" and th.metric == "latency_ms" and th.value == 300.0


def test_from_inputs_importance_prefixes() -> None:
    slo = SLO.from_inputs(
        expect=["must: error_rate < 1%", "should: cpu < 70%", "nice: p90(latency_ms) < 100"]
    )
    imps = {t.metric: t.importance for t in slo.thresholds}
    assert imps["error_rate"] == Importance.MUST
    assert imps["cpu"] == Importance.SHOULD
    assert imps["latency_ms"] == Importance.NICE


def test_from_inputs_skips_unparseable() -> None:
    slo = SLO.from_inputs(expect=["must: be fast", "must: error_rate < 1%"])
    assert len(slo.thresholds) == 1


def test_percentile_interpolation() -> None:
    assert percentile([10, 20, 30, 40], 50) == 25.0
    assert percentile([], 99) is None
    assert percentile([42], 99) == 42


def test_aggregate_functions() -> None:
    ts = TimeSeries(name="x", points=[(0, 1.0), (1, 3.0), (2, 2.0)])
    assert aggregate(ts, "last") == 2.0
    assert aggregate(ts, "max") == 3.0
    assert aggregate(ts, "min") == 1.0
    assert aggregate(ts, "mean") == 2.0
