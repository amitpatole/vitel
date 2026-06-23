"""Cloud metrics backends (``vitel[cloud]``): Datadog and CloudWatch, lazy-imported.

Registered as ``datadog`` and ``cloudwatch``. The ``source`` is a provider query string. Response
parsing is factored into pure functions so it can be tested without network or credentials.
"""

from __future__ import annotations

import os
from datetime import UTC

from ..config import Settings
from ..errors import BackendAuthError, ConfigError, MissingDependencyError, SourceError
from ..logging import register_secret
from ..signals.series import TimeSeries


def parse_datadog(data: dict) -> list[TimeSeries]:
    """Parse a Datadog metrics-query response (``series[].pointlist`` of ``[ts_ms, value]``)."""
    out: list[TimeSeries] = []
    for s in data.get("series", []):
        name = s.get("metric") or s.get("display_name") or "datadog"
        scope = s.get("scope")
        full = f"{name}{{{scope}}}" if scope and scope != "*" else name
        points: list[tuple[float, float]] = []
        for pt in s.get("pointlist", []):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2 or pt[1] is None:
                continue
            try:
                points.append((float(pt[0]) / 1000.0, float(pt[1])))
            except (TypeError, ValueError):
                continue
        out.append(TimeSeries(name=full, points=points))
    return out


def parse_cloudwatch(data: dict) -> list[TimeSeries]:
    """Parse a CloudWatch ``get_metric_data`` response (``MetricDataResults``)."""
    out: list[TimeSeries] = []
    for r in data.get("MetricDataResults", []):
        name = r.get("Label") or r.get("Id") or "cloudwatch"
        stamps = r.get("Timestamps", [])
        values = r.get("Values", [])
        points: list[tuple[float, float]] = []
        for ts, val in zip(stamps, values, strict=False):
            try:
                # boto3 returns datetimes; accept epoch floats too
                t = ts.timestamp() if hasattr(ts, "timestamp") else float(ts)
                points.append((t, float(val)))
            except (TypeError, ValueError):
                continue
        out.append(TimeSeries(name=name, points=points))
    return out


class CloudBackend:
    def __init__(self, settings: Settings | None = None, *, provider: str = "datadog") -> None:
        self.settings = settings or Settings()
        if provider not in ("datadog", "cloudwatch"):
            raise ConfigError(f"unknown cloud provider {provider!r}")
        self.provider = provider
        self.name = provider

    def available(self) -> bool:
        from importlib.util import find_spec

        if self.provider == "datadog":
            return find_spec("datadog_api_client") is not None and bool(os.getenv("DD_API_KEY"))
        return find_spec("boto3") is not None

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        if not source or not source.strip():
            raise SourceError(f"{self.provider} backend needs a query as the source")
        return (
            await self._fetch_datadog(source, window_s)
            if self.provider == "datadog"
            else await self._fetch_cloudwatch(source, window_s)
        )

    async def _fetch_datadog(self, query: str, window_s: float | None) -> list[TimeSeries]:
        import time

        try:
            from datadog_api_client import ApiClient, Configuration
            from datadog_api_client.v1.api.metrics_api import MetricsApi
        except ImportError as e:
            raise MissingDependencyError("datadog backend needs datadog-api-client; pip install vitel[cloud]") from e
        api_key = os.getenv("DD_API_KEY")
        app_key = os.getenv("DD_APP_KEY")
        if not api_key or not app_key:
            raise BackendAuthError("datadog needs DD_API_KEY and DD_APP_KEY")
        register_secret(api_key)
        register_secret(app_key)
        end = int(time.time())
        start = end - int(window_s or 300)
        conf = Configuration()
        conf.api_key["apiKeyAuth"] = api_key
        conf.api_key["appKeyAuth"] = app_key
        with ApiClient(conf) as client:
            resp = MetricsApi(client).query_metrics(_from=start, to=end, query=query)
        data = resp.to_dict() if hasattr(resp, "to_dict") else dict(resp)
        return parse_datadog(data)

    async def _fetch_cloudwatch(self, query: str, window_s: float | None) -> list[TimeSeries]:
        # query form: "Namespace/MetricName" (statistic Average); dimensions via settings/env later.
        import time
        from datetime import datetime

        try:
            import boto3
        except ImportError as e:
            raise MissingDependencyError("cloudwatch backend needs boto3; pip install vitel[cloud]") from e
        if "/" not in query:
            raise SourceError("cloudwatch query must be 'Namespace/MetricName'")
        namespace, _, metric_name = query.partition("/")
        end = datetime.now(UTC)
        start = datetime.fromtimestamp(time.time() - (window_s or 300), tz=UTC)
        client = boto3.client("cloudwatch")
        resp = client.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "m1",
                    "MetricStat": {
                        "Metric": {"Namespace": namespace, "MetricName": metric_name},
                        "Period": 60,
                        "Stat": "Average",
                    },
                }
            ],
            StartTime=start,
            EndTime=end,
        )
        return parse_cloudwatch(resp)
