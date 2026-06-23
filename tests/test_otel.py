"""OTLP/JSON metrics parsing."""

from __future__ import annotations

import asyncio

from agentsensory import Verdict

from vitel import check
from vitel.backends.otel import parse_otlp_json
from vitel.slo import SLO

_OTLP = {
    "resourceMetrics": [
        {
            "scopeMetrics": [
                {
                    "metrics": [
                        {
                            "name": "error_rate",
                            "gauge": {
                                "dataPoints": [
                                    {"asDouble": 0.02, "timeUnixNano": "1000000000"},
                                    {"asDouble": 0.05, "timeUnixNano": "2000000000"},
                                ]
                            },
                        },
                        {
                            "name": "requests",
                            "sum": {"dataPoints": [{"asInt": "42", "timeUnixNano": "2000000000"}]},
                        },
                    ]
                }
            ]
        }
    ]
}


def test_parse_gauge_and_sum() -> None:
    series = {s.name: s for s in parse_otlp_json(_OTLP)}
    assert series["error_rate"].values == [0.02, 0.05]
    assert series["requests"].values == [42.0]
    assert series["error_rate"].points[0][0] == 1.0  # nanos → seconds


def test_attributes_become_labels() -> None:
    data = {
        "resourceMetrics": [
            {
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "lat",
                                "gauge": {
                                    "dataPoints": [
                                        {"asDouble": 1.0, "attributes": [{"key": "route", "value": {"stringValue": "/a"}}]}
                                    ]
                                },
                            }
                        ]
                    }
                ]
            }
        ]
    }
    assert parse_otlp_json(data)[0].name == "lat{route=/a}"


def test_check_via_otel_backend() -> None:
    import json

    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = asyncio.run(check(json.dumps(_OTLP), slo=slo, backend="otel"))
    assert r.verdict == Verdict.FAIL
