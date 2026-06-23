"""analyze(): deterministic grade + anomaly, with a fail-soft LLM critique."""

from __future__ import annotations

import asyncio
import importlib
import json

from agentsensory import Verdict

from vitel import analyze
from vitel.models import IssueKind
from vitel.slo import SLO

# the submodule object (the package re-exports the function under the same name)
analyze_mod = importlib.import_module("vitel.core.analyze")


def _run(coro):
    return asyncio.run(coro)


def test_analyze_matches_check_verdict_without_llm() -> None:
    src = '{"metrics": {"error_rate": 0.05}}'
    r = _run(analyze(src, slo=SLO.from_inputs(expect=["must: error_rate < 1%"]), use_llm=False))
    assert r.verdict == Verdict.FAIL
    assert "analyze" in r.capabilities


def test_analyze_adds_trend_issue() -> None:
    src = json.dumps(
        {"series": [{"name": "latency_ms", "points": [[i * 30, v] for i, v in enumerate([120, 160, 220, 300, 380])]}]}
    )
    r = _run(analyze(src, use_llm=False))
    assert any(i.kind == IssueKind.LATENCY_REGRESSION for i in r.issues)


def test_analyze_llm_failsoft(monkeypatch) -> None:
    # Even if critique raises, analyze must still return a deterministic verdict.
    def boom(*_a, **_k):
        raise RuntimeError("ollama down")

    monkeypatch.setattr(analyze_mod, "critique", boom)
    src = '{"metrics": {"error_rate": 0.05}}'
    try:
        r = _run(analyze(src, slo=SLO.from_inputs(expect=["must: error_rate < 1%"]), use_llm=True))
    except RuntimeError:
        raise AssertionError("analyze must not propagate LLM errors") from None
    assert r.verdict == Verdict.FAIL


def test_analyze_llm_note_appended(monkeypatch) -> None:
    monkeypatch.setattr(analyze_mod, "critique", lambda *a, **k: ("latency looks unstable", "llama3.2"))
    src = '{"metrics": {"error_rate": 0.0001}}'
    r = _run(analyze(src, use_llm=True))
    assert "latency looks unstable" in r.summary
    assert r.model == "llama3.2"
