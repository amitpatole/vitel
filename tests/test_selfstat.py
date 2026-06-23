"""psutil self-vitals backend (skipped when psutil absent)."""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("psutil")

from agentsensory import Verdict  # noqa: E402

from vitel import check  # noqa: E402
from vitel.backends.selfstat import SelfStatBackend  # noqa: E402
from vitel.slo import SLO  # noqa: E402


def test_self_vitals_returns_core_series() -> None:
    series = {s.name for s in asyncio.run(SelfStatBackend().fetch("self"))}
    assert {"cpu", "mem", "rss_bytes", "num_threads"} <= series


def test_check_self_vitals() -> None:
    # mem ratio is always <= 1.0, so this must pass
    slo = SLO.from_inputs(expect=["must: mem < 1.5"])
    r = asyncio.run(check("self", slo=slo, backend="psutil"))
    assert r.verdict == Verdict.PASS
