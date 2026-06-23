"""OpenTelemetry (OTLP) metrics backend.

Parses an OTLP/JSON metrics export (``ExportMetricsServiceRequest`` shape) — gauge / sum / histogram
data points — into normalized series. The JSON parse needs no extra dependency; the ``vitel[otel]``
extra is for the live OTLP receiver path. ``source`` is a path to, or inline, OTLP JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from ..errors import SourceError, UnsafeSourceError
from ..signals.series import TimeSeries


def _attr_suffix(attrs: list) -> str:
    pairs = []
    for a in attrs or []:
        k = a.get("key")
        v = a.get("value", {})
        val = v.get("stringValue") or v.get("intValue") or v.get("doubleValue") or v.get("boolValue")
        if k is not None and val is not None:
            pairs.append(f"{k}={val}")
    return f"{{{','.join(sorted(pairs))}}}" if pairs else ""


def _point_value(dp: dict) -> float | None:
    if "asDouble" in dp:
        try:
            return float(dp["asDouble"])
        except (TypeError, ValueError):
            return None
    if "asInt" in dp:
        try:
            return float(int(dp["asInt"]))
        except (TypeError, ValueError):
            return None
    if "count" in dp:  # histogram → use count
        try:
            return float(int(dp["count"]))
        except (TypeError, ValueError):
            return None
    return None


def _point_ts(dp: dict) -> float:
    nanos = dp.get("timeUnixNano") or dp.get("startTimeUnixNano")
    try:
        return int(nanos) / 1e9 if nanos is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def parse_otlp_json(data: dict) -> list[TimeSeries]:
    """Parse an OTLP/JSON metrics export into normalized series (pure, testable)."""
    by_name: dict[str, TimeSeries] = {}
    for rm in data.get("resourceMetrics", []):
        for sm in rm.get("scopeMetrics", []):
            for metric in sm.get("metrics", []):
                name = metric.get("name")
                if not name:
                    continue
                body = metric.get("gauge") or metric.get("sum") or metric.get("histogram") or {}
                for dp in body.get("dataPoints", []):
                    val = _point_value(dp)
                    if val is None:
                        continue
                    series_name = f"{name}{_attr_suffix(dp.get('attributes', []))}"
                    ts = by_name.setdefault(series_name, TimeSeries(name=series_name))
                    ts.points.append((_point_ts(dp), val))
    for s in by_name.values():
        s.__post_init__()  # sort points by time
    return list(by_name.values())


class OTLPBackend:
    name = "otel"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        return True  # JSON parsing needs no extra; the SDK receiver path uses vitel[otel]

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        stripped = source.lstrip()
        if stripped[:1] in ("{", "["):
            if len(source.encode("utf-8", "ignore")) > self.settings.max_source_bytes:
                raise UnsafeSourceError("inline source exceeds max_source_bytes")
            text = source
        else:
            path = Path(source)
            if not path.is_file():
                raise SourceError(f"no such file: {source}")
            if path.stat().st_size > self.settings.max_source_bytes:
                raise UnsafeSourceError("source exceeds max_source_bytes")
            text = path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except (ValueError, RecursionError) as e:
            raise SourceError(f"invalid OTLP JSON: {e}") from e
        if not isinstance(data, dict):
            raise SourceError("OTLP source must be a JSON object")
        series = parse_otlp_json(data)
        total = sum(len(s.points) for s in series)
        if total > self.settings.max_points:
            raise UnsafeSourceError(f"OTLP source has {total} points, exceeds max_points")
        return series
