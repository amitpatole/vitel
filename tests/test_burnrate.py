"""Error-budget math + derived-metric grading."""

from __future__ import annotations

import asyncio

import pytest
from agentsensory import Verdict

from vitel import check
from vitel.models import IssueKind
from vitel.signals.burnrate import (
    budget_remaining,
    burn_rate,
    derived_budget_series,
    error_budget,
    multi_window_hot,
)
from vitel.signals.series import TimeSeries
from vitel.slo import SLO


def test_error_budget_and_rates() -> None:
    assert error_budget(0.999) == pytest.approx(0.001)
    assert burn_rate(0.999, 0.001) == pytest.approx(1.0)
    assert burn_rate(0.999, 0.014_4) == pytest.approx(14.4)
    assert budget_remaining(0.999, 0.0005) == pytest.approx(0.5)
    assert budget_remaining(0.999, 0.002) == pytest.approx(-1.0)  # blown


def test_invalid_target_rejected() -> None:
    with pytest.raises(ValueError):
        error_budget(1.0)
    with pytest.raises(ValueError):
        error_budget(0.0)


def test_multi_window_hot() -> None:
    # both windows must be hot to page
    assert multi_window_hot(0.999, slow_error=0.02, fast_error=0.02)
    assert not multi_window_hot(0.999, slow_error=0.02, fast_error=0.0001)


def test_derived_series_empty_when_metric_missing() -> None:
    assert derived_budget_series({}, target=0.999) == []
    empty = {"error_rate": TimeSeries(name="error_rate", points=[])}
    assert derived_budget_series(empty, target=0.999) == []


def test_derived_series_computes_burn_and_remaining() -> None:
    sm = {"error_rate": TimeSeries(name="error_rate", points=[(0, 0.001), (1, 0.003)])}
    out = {s.name: s.last() for s in derived_budget_series(sm, target=0.999)}
    assert out["burn_rate"] == pytest.approx(2.0)  # mean 0.002 / 0.001
    assert out["error_budget_remaining"] == pytest.approx(-1.0)


def test_budget_burn_fails_with_error_budget_burn_issue() -> None:
    src = '{"series": [{"name": "error_rate", "points": [[0, 0.01], [60, 0.02], [120, 0.03]]}]}'
    slo = SLO.from_inputs(expect=["availability 99.9%", "must: error_budget_remaining > 20%"])
    r = asyncio.run(check(src, slo=slo))
    assert r.verdict == Verdict.FAIL
    assert any(i.kind == IssueKind.ERROR_BUDGET_BURN for i in r.issues)


def test_within_budget_passes() -> None:
    src = '{"series": [{"name": "error_rate", "points": [[0, 0.0002], [60, 0.0003]]}]}'
    slo = SLO.from_inputs(expect=["availability 99.9%", "must: error_budget_remaining > 20%"])
    r = asyncio.run(check(src, slo=slo))
    assert r.verdict == Verdict.PASS
