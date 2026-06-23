"""Shared fixtures: synthetic JSON/CSV telemetry series written to a temp dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_SERIES = {
    # healthy service: low error rate, latency under budget
    "good": {
        "series": [
            {"name": "error_rate", "unit": "ratio", "points": [[0, 0.004], [60, 0.005], [120, 0.003]]},
            {"name": "latency_ms", "unit": "ms", "points": [[0, 120], [60, 150], [120, 200], [180, 240]]},
            {"name": "cpu", "unit": "ratio", "points": [[0, 0.40], [60, 0.55], [120, 0.50]]},
        ],
        "window_s": 180,
    },
    # broken service: error rate and latency blown past budget
    "violating": {
        "series": [
            {"name": "error_rate", "unit": "ratio", "points": [[0, 0.02], [60, 0.04], [120, 0.05]]},
            {"name": "latency_ms", "unit": "ms", "points": [[0, 300], [60, 450], [120, 520]]},
            {"name": "cpu", "unit": "ratio", "points": [[0, 0.60], [60, 0.85], [120, 0.92]]},
        ],
        "window_s": 180,
    },
    # source that returned an empty series for a metric we must check
    "nodata": {"series": [{"name": "error_rate", "unit": "ratio", "points": []}]},
}


@pytest.fixture(scope="session")
def series_files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    d = tmp_path_factory.mktemp("series")
    out: dict[str, str] = {}
    for name, payload in _SERIES.items():
        p: Path = d / f"{name}.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        out[name] = str(p)
    # a CSV variant of the good service
    csv = "timestamp,error_rate,latency_ms,cpu\n0,0.004,120,0.40\n60,0.005,150,0.55\n120,0.003,200,0.50\n"
    cp = d / "good.csv"
    cp.write_text(csv, encoding="utf-8")
    out["good_csv"] = str(cp)
    return out
