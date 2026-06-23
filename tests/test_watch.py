"""watch(): temporal degradation detection. Acceptance: flag a slow latency regression."""

from __future__ import annotations

import asyncio
import json

from agentsensory import Verdict

from vitel import watch
from vitel.models import IssueKind


def _run(coro):
    return asyncio.run(coro)


def _series(name: str, values: list[float], unit: str = "") -> dict:
    return {"name": name, "unit": unit, "points": [[i * 30, v] for i, v in enumerate(values)]}


def test_watch_flags_slow_latency_regression() -> None:
    # latency drifts up ~3x across the window — a slow regression, no single SLO threshold needed
    src = json.dumps({"series": [_series("latency_ms", [120, 140, 170, 220, 300, 360], "ms")]})
    r = _run(watch(src, window=150))
    kinds = {i.kind for i in r.issues}
    assert IssueKind.LATENCY_REGRESSION in kinds
    reg = next(i for i in r.issues if i.kind == IssueKind.LATENCY_REGRESSION)
    assert reg.metric is not None and reg.metric.name == "latency_ms"


def test_watch_stable_latency_is_clean() -> None:
    src = json.dumps({"series": [_series("latency_ms", [200, 198, 202, 199, 201], "ms")]})
    r = _run(watch(src, window=150))
    assert all(i.kind != IssueKind.LATENCY_REGRESSION for i in r.issues)
    assert r.verdict == Verdict.PASS


def test_watch_flags_resource_leak() -> None:
    src = json.dumps({"series": [_series("rss_bytes", [100, 120, 145, 170, 210, 260])]})
    r = _run(watch(src, window=150))
    assert any(i.kind == IssueKind.RESOURCE_LEAK for i in r.issues)


def test_watch_flags_error_spike() -> None:
    src = json.dumps({"series": [_series("error_rate", [0.01, 0.01, 0.012, 0.009, 0.011, 0.2])]})
    r = _run(watch(src, window=150))
    assert any(i.kind == IssueKind.ERROR_SPIKE for i in r.issues)


def test_watch_flatline_is_info_only() -> None:
    src = json.dumps({"series": [_series("replicas", [3, 3, 3, 3, 3])]})
    r = _run(watch(src, window=150))
    assert any(i.kind == IssueKind.FLATLINE for i in r.issues)
    assert r.verdict == Verdict.PASS  # INFO never escalates the verdict


def test_watch_poll_live_backend_accumulates(monkeypatch) -> None:
    # Drive the polling path with a fake live backend and zero-sleep.
    import importlib

    from vitel.signals.series import TimeSeries

    watch_mod = importlib.import_module("vitel.core.watch")

    seq = iter([180, 240, 320, 420])

    class FakeBackend:
        name = "scrape"

        async def fetch(self, source, *, window_s=None):
            return [TimeSeries(name="latency_ms", points=[(0.0, float(next(seq)))], unit="ms")]

    monkeypatch.setattr(watch_mod, "resolve_backend", lambda *a, **k: FakeBackend())

    async def _no_sleep(*_a, **_k):
        return None

    monkeypatch.setattr(watch_mod.asyncio, "sleep", _no_sleep)
    r = _run(watch_mod.watch("http://x/metrics", window=4, interval=1))
    assert any(i.kind == IssueKind.LATENCY_REGRESSION for i in r.issues)


def test_watch_poll_count_is_bounded(monkeypatch) -> None:
    # DoS guard: a tiny interval over a huge window must not exceed settings.max_polls.
    import importlib

    from vitel.config import Settings
    from vitel.signals.series import TimeSeries

    watch_mod = importlib.import_module("vitel.core.watch")
    calls = {"n": 0}

    class FakeBackend:
        name = "scrape"

        async def fetch(self, source, *, window_s=None):
            calls["n"] += 1
            return [TimeSeries(name="x", points=[(0.0, 1.0)])]

    monkeypatch.setattr(watch_mod, "resolve_backend", lambda *a, **k: FakeBackend())

    async def _no_sleep(*_a, **_k):
        return None

    monkeypatch.setattr(watch_mod.asyncio, "sleep", _no_sleep)
    _run(watch_mod.watch("http://x/metrics", window=10_000, interval=0.001,
                         settings=Settings(max_polls=5)))
    assert calls["n"] == 5
