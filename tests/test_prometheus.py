"""Prometheus range-response parsing (pure, no network)."""

from __future__ import annotations

import pytest

from vitel.backends.prometheus import parse_range_response
from vitel.errors import SourceError


def _ok(result):
    return {"status": "success", "data": {"resultType": "matrix", "result": result}}


def test_parse_named_series() -> None:
    body = _ok([
        {"metric": {"__name__": "error_rate", "job": "api"}, "values": [[0, "0.01"], [60, "0.02"]]}
    ])
    series = parse_range_response(body)
    assert len(series) == 1
    assert series[0].name == "error_rate{job=api}"
    assert series[0].values == [0.01, 0.02]


def test_parse_unnamed_series() -> None:
    body = _ok([{"metric": {"job": "api"}, "values": [[0, "1"]]}])
    assert parse_range_response(body)[0].name == "{job=api}"


def test_parse_skips_bad_values() -> None:
    body = _ok([{"metric": {"__name__": "x"}, "values": [[0, "nan?"], [60, "2.0"]]}])
    series = parse_range_response(body)
    assert series[0].values == [2.0]


def test_error_status_raises() -> None:
    with pytest.raises(SourceError):
        parse_range_response({"status": "error", "error": "bad query"})
