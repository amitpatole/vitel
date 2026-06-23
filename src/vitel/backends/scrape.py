"""Scrape a Prometheus/OpenMetrics ``/metrics`` endpoint (lazy ``httpx``, SSRF-guarded).

The ``source`` is the URL of a ``/metrics`` endpoint exposing the text exposition format; each
sample becomes a single-point :class:`TimeSeries`. This is the "grade a live ``/metrics`` endpoint"
path. Use the ``prometheus`` backend instead for PromQL range queries against a Prometheus server.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import MissingDependencyError, SourceError
from ..netguard import validate_url
from ..signals.series import TimeSeries


def _parse_labels(blob: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in blob.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        labels[k.strip()] = v.strip().strip('"')
    return labels


def _series_name(metric: str, labels: dict[str, str]) -> str:
    if not labels:
        return metric
    return f"{metric}{{{','.join(f'{k}={v}' for k, v in sorted(labels.items()))}}}"


def parse_exposition(text: str) -> list[TimeSeries]:
    """Parse Prometheus/OpenMetrics text exposition into single-point series (pure, testable)."""
    series: list[TimeSeries] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # name{labels} value [timestamp]
        if "{" in line:
            metric, _, rest = line.partition("{")
            labelblob, _, after = rest.partition("}")
            labels = _parse_labels(labelblob)
            fields = after.split()
        else:
            parts = line.split()
            metric, labels = parts[0], {}
            fields = parts[1:]
        if not fields:
            continue
        try:
            value = float(fields[0])
        except ValueError:
            continue  # skip NaN/inf-shaped or malformed samples
        ts = 0.0
        if len(fields) > 1:
            try:
                ts = float(fields[1]) / 1000.0  # exposition timestamps are epoch millis
            except ValueError:
                ts = 0.0
        series.append(TimeSeries(name=_series_name(metric.strip(), labels), points=[(ts, value)]))
    return series


class ScrapeBackend:
    name = "scrape"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        from importlib.util import find_spec

        return find_spec("httpx") is not None

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        if not source or not source.strip():
            raise SourceError("scrape backend needs a /metrics URL as the source")
        try:
            import httpx
        except ImportError as e:
            raise MissingDependencyError("scrape backend needs httpx; pip install vitel[prometheus]") from e

        url = validate_url(source.strip(), allow_private=self.settings.allow_private_targets)
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_s) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                # bound the response we read into memory
                body = resp.text
        except httpx.HTTPError as e:
            raise SourceError(f"scrape request failed: {e}") from e
        if len(body.encode("utf-8", "ignore")) > self.settings.max_source_bytes:
            raise SourceError("scrape response exceeds max_source_bytes")
        series = parse_exposition(body)
        total = sum(len(s.points) for s in series)
        if total > self.settings.max_points:
            raise SourceError(f"scrape returned {total} samples, exceeds max_points")
        return series
