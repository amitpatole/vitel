"""V4: the afferent Handoff gates 'done', and the CI gate exit codes are correct."""

from __future__ import annotations

import asyncio
import json

from agentsensory import NextAction, Verdict

from vitel import perceive
from vitel.adapters._demo_assets import degrading_source, demo_slo, healthy_source
from vitel.adapters.cli import _gate_code


def _run(coro):
    return asyncio.run(coro)


def test_failing_vitals_withhold_done() -> None:
    # A failing post-deploy vitals verdict must NOT yield next_action == DONE.
    h = _run(perceive(degrading_source(), slo=demo_slo()))
    assert h.perceived == Verdict.FAIL
    assert h.next_action != NextAction.DONE
    assert h.next_action == NextAction.REVISE
    assert h.todo  # actionable remediation for the brain


def test_healthy_vitals_allow_done() -> None:
    h = _run(perceive(healthy_source(), slo=demo_slo()))
    assert h.perceived == Verdict.PASS
    assert h.next_action == NextAction.DONE


def test_perceive_handoff_round_trips() -> None:
    from agentsensory import Handoff

    h = _run(perceive('{"metrics": {"error_rate": 0.5}}', slo=demo_slo()))
    assert Handoff.model_validate_json(h.model_dump_json()).next_action == h.next_action


def test_gate_exit_codes() -> None:
    assert _gate_code("pass", warn_as_fail=False) == 0
    assert _gate_code("warn", warn_as_fail=False) == 0
    assert _gate_code("warn", warn_as_fail=True) == 1
    assert _gate_code("fail", warn_as_fail=False) == 1


def test_recipe_example_is_valid_json() -> None:
    from pathlib import Path

    recipe = Path(__file__).resolve().parents[1] / "examples" / "verel" / "post_deploy_vitals.recipe.json"
    data = json.loads(recipe.read_text())
    assert data["sense"] == "vitel"
    assert "fail" in data["gate"]["blocks_on"]
