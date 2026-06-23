"""Synthetic telemetry for ``vitel demo`` — a degrading service then its fix. No API key, no network.

The degrading service burns its error budget (rising error rate against a 99.9% target) and blows
its latency SLO; the fixed service is back within budget.
"""

from __future__ import annotations

import json

from ..slo import SLO

_TARGET = 99.9  # availability %, i.e. a 0.1% error budget


def _series(error_points: list[float], latency_points: list[float]) -> str:
    step = 60
    return json.dumps(
        {
            "series": [
                {
                    "name": "error_rate",
                    "unit": "ratio",
                    "points": [[i * step, v] for i, v in enumerate(error_points)],
                },
                {
                    "name": "latency_ms",
                    "unit": "ms",
                    "points": [[i * step, v] for i, v in enumerate(latency_points)],
                },
            ],
            "window_s": step * (len(error_points) - 1),
        }
    )


def degrading_source() -> str:
    """A service whose error rate climbs far past its 0.1% budget and whose latency regresses."""
    return _series(
        error_points=[0.0008, 0.004, 0.012, 0.03, 0.05],
        latency_points=[180, 240, 360, 480, 620],
    )


def healthy_source() -> str:
    """The same service after the fix — comfortably within budget."""
    return _series(
        error_points=[0.0006, 0.0004, 0.0005, 0.0003, 0.0004],
        latency_points=[150, 165, 180, 170, 160],
    )


def demo_slo() -> SLO:
    return SLO.from_inputs(
        text="demo service: 99.9% availability, p99 latency under 300ms",
        expect=[
            f"availability {_TARGET}%",
            "must: error_budget_remaining > 20%",
            "should: p99(latency_ms) < 300ms",
        ],
    )
