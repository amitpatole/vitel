"""The demo must trip an error-budget burn then pass after the fix — no API key."""

from __future__ import annotations

import asyncio

from agentsensory import Verdict

from vitel import check
from vitel.adapters._demo_assets import degrading_source, demo_slo, healthy_source
from vitel.models import IssueKind


def test_demo_degrading_fails_on_budget_burn() -> None:
    r = asyncio.run(check(degrading_source(), slo=demo_slo()))
    assert r.verdict == Verdict.FAIL
    assert any(i.kind == IssueKind.ERROR_BUDGET_BURN for i in r.issues)


def test_demo_fixed_passes() -> None:
    r = asyncio.run(check(healthy_source(), slo=demo_slo()))
    assert r.verdict == Verdict.PASS
