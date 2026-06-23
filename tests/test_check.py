"""check() verdicts: PASS / WARN / FAIL and no-data fail-closed."""

from __future__ import annotations

import asyncio

from agentsensory import Verdict

from vitel import check
from vitel.models import IssueKind
from vitel.slo import SLO


def _run(coro):
    return asyncio.run(coro)


def test_good_service_passes(series_files) -> None:
    slo = SLO.from_inputs(expect=["must: error_rate < 1%", "must: p99(latency_ms) < 300ms"])
    r = _run(check(series_files["good"], slo=slo))
    assert r.verdict == Verdict.PASS
    assert not r.issues
    assert r.conformance and r.conformance.satisfied == 2


def test_violating_must_fails(series_files) -> None:
    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = _run(check(series_files["violating"], slo=slo))
    assert r.verdict == Verdict.FAIL
    assert any(i.kind == IssueKind.SLO_VIOLATION for i in r.issues)
    viol = next(i for i in r.issues if i.kind == IssueKind.SLO_VIOLATION)
    assert viol.metric is not None and viol.metric.name == "error_rate"
    assert viol.metric.observed > viol.metric.threshold


def test_violating_should_only_warns(series_files) -> None:
    slo = SLO.from_inputs(expect=["should: cpu < 70%"])
    r = _run(check(series_files["violating"], slo=slo))
    assert r.verdict == Verdict.WARN


def test_missing_must_metric_fails_closed(series_files) -> None:
    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = _run(check(series_files["nodata"], slo=slo))
    assert r.verdict == Verdict.FAIL
    assert any(i.kind == IssueKind.NO_DATA for i in r.issues)


def test_csv_source_parses(series_files) -> None:
    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = _run(check(series_files["good_csv"], slo=slo))
    assert r.verdict == Verdict.PASS


def test_inline_json_source() -> None:
    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = _run(check('{"metrics": {"error_rate": 0.5}}', slo=slo))
    assert r.verdict == Verdict.FAIL


def test_check_exit_report_round_trips(series_files) -> None:
    from vitel.models import Report

    r = _run(check(series_files["good"], slo=SLO.from_inputs(expect=["must: error_rate < 1%"])))
    assert Report.model_validate_json(r.model_dump_json()).verdict == r.verdict
