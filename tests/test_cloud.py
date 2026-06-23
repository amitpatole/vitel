"""Cloud response parsing (pure, no network/creds)."""

from __future__ import annotations

from datetime import UTC, datetime

from vitel.backends.cloud import parse_cloudwatch, parse_datadog


def test_parse_datadog() -> None:
    data = {
        "series": [
            {"metric": "system.cpu.user", "scope": "host:web1", "pointlist": [[1000, 0.4], [2000, 0.6]]},
            {"metric": "noise", "pointlist": [[1000, None]]},
        ]
    }
    series = {s.name: s for s in parse_datadog(data)}
    assert series["system.cpu.user{host:web1}"].values == [0.4, 0.6]
    assert series["system.cpu.user{host:web1}"].points[0][0] == 1.0  # ms → s
    assert series["noise"].values == []  # None skipped


def test_parse_cloudwatch_epoch_and_datetime() -> None:
    data = {
        "MetricDataResults": [
            {"Label": "CPUUtilization", "Timestamps": [1000.0, 2000.0], "Values": [10.0, 20.0]},
            {
                "Label": "Errors",
                "Timestamps": [datetime.fromtimestamp(5, tz=UTC)],
                "Values": [3.0],
            },
        ]
    }
    series = {s.name: s for s in parse_cloudwatch(data)}
    assert series["CPUUtilization"].values == [10.0, 20.0]
    assert series["Errors"].points == [(5.0, 3.0)]
