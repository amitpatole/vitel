"""Prometheus / PromQL backend (``vitel[prometheus]``) — lazy ``httpx``, SSRF-guarded.

The ``source`` is a PromQL expression; it is run as a ``query_range`` over the window and each
returned series becomes a :class:`TimeSeries` named by its ``__name__`` label (falling back to the
full label set). Set ``VITEL_PROMETHEUS_URL`` to the Prometheus base URL.
"""

from __future__ import annotations

import time

from ..config import Settings
from ..errors import ConfigError, MissingDependencyError, SourceError
from ..netguard import validate_url
from ..signals.series import TimeSeries


def _series_name(labels: dict) -> str:
    name = labels.get("__name__")
    if name:
        extra = {k: v for k, v in labels.items() if k != "__name__"}
        return f"{name}{{{','.join(f'{k}={v}' for k, v in sorted(extra.items()))}}}" if extra else name
    return "{" + ",".join(f"{k}={v}" for k, v in sorted(labels.items())) + "}"


def parse_range_response(data: dict) -> list[TimeSeries]:
    """Parse a Prometheus ``query_range`` JSON body into normalized series (pure, testable)."""
    if data.get("status") != "success":
        raise SourceError(f"prometheus error: {data.get('error', 'unknown')}")
    result = data.get("data", {}).get("result", [])
    series: list[TimeSeries] = []
    for item in result:
        labels = item.get("metric", {})
        points: list[tuple[float, float]] = []
        for ts, val in item.get("values", []):
            try:
                points.append((float(ts), float(val)))
            except (TypeError, ValueError):
                continue
        series.append(TimeSeries(name=_series_name(labels), points=points))
    return series


class PrometheusBackend:
    name = "prometheus"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        if not self.settings.prometheus_url:
            return False
        from importlib.util import find_spec

        return find_spec("httpx") is not None

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        if not self.settings.prometheus_url:
            raise ConfigError("set VITEL_PROMETHEUS_URL to use the prometheus backend")
        if not source or not source.strip():
            raise SourceError("prometheus backend needs a PromQL query as the source")
        try:
            import httpx
        except ImportError as e:
            raise MissingDependencyError("prometheus backend needs httpx; pip install vitel[prometheus]") from e

        base = self.settings.prometheus_url.rstrip("/")
        url = f"{base}/api/v1/query_range"
        validate_url(url, allow_private=self.settings.allow_private_targets)

        window = window_s or 300.0
        end = time.time()
        start = end - window
        step = max(window / 250.0, 1.0)  # keep the point count bounded
        params: dict[str, str | float] = {"query": source, "start": start, "end": end, "step": step}

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_s) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise SourceError(f"prometheus request failed: {e}") from e

        series = parse_range_response(data)
        total = sum(len(s.points) for s in series)
        if total > self.settings.max_points:
            raise SourceError(f"prometheus returned {total} points, exceeds max_points")
        return series
