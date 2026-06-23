"""The built-in JSON / CSV series backend — the light base, no extra dependencies.

Accepts a path to a ``.json``/``.csv`` file or an inline JSON string. Untrusted input is bounded
(byte cap before read, point cap while parsing) and shape-validated before it reaches the grader.

JSON shapes::

    {"series": [{"name": "error_rate", "unit": "ratio", "points": [[t, v], ...]}], "window_s": 300}
    {"series": [{"name": "cpu", "value": 0.42}]}          # scalar → one point
    {"metrics": {"error_rate": 0.02, "p99_latency_ms": 350}}   # scalar map
    {"error_rate": 0.02, "p99_latency_ms": 350}                # bare scalar map

CSV: header row of column names; an optional ``timestamp``/``ts``/``time`` column sets the time
(epoch seconds or ISO-8601), every other numeric column becomes a series.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from ..config import Settings
from ..errors import SourceError, UnsafeSourceError
from ..signals.series import TimeSeries

_TS_COLS = {"timestamp", "ts", "time", "t"}


def _to_ts(raw: object, fallback: float) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        s = raw.strip()
        try:
            return float(s)
        except ValueError:
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return fallback
    return fallback


class FileBackend:
    name = "file"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        return True

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        return ""

    def _read(self, source: str) -> str:
        stripped = source.lstrip()
        if stripped[:1] in ("{", "["):  # inline JSON
            if len(source.encode("utf-8", "ignore")) > self.settings.max_source_bytes:
                raise UnsafeSourceError("inline source exceeds max_source_bytes")
            return source
        path = Path(source)
        if not path.is_file():
            raise SourceError(f"no such file: {source}")
        size = path.stat().st_size
        if size > self.settings.max_source_bytes:
            raise UnsafeSourceError(
                f"source {size} bytes exceeds max_source_bytes={self.settings.max_source_bytes}"
            )
        return path.read_text(encoding="utf-8")

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        text = self._read(source)
        is_json = source.lstrip()[:1] in ("{", "[") or source.rstrip().endswith(".json")
        series = self._parse_json(text) if is_json else self._parse_csv(text)
        total = sum(len(s.points) for s in series)
        if total > self.settings.max_points:
            raise UnsafeSourceError(
                f"source has {total} points, exceeds max_points={self.settings.max_points}"
            )
        return series

    def _parse_json(self, text: str) -> list[TimeSeries]:
        try:
            data = json.loads(text)
        except (ValueError, RecursionError) as e:
            raise SourceError(f"invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise SourceError("JSON source must be an object")

        if "series" in data:
            return [self._series_from_obj(o) for o in self._as_list(data["series"])]
        if "metrics" in data:
            return self._scalar_map(data["metrics"])
        # bare scalar map
        return self._scalar_map(data)

    @staticmethod
    def _as_list(v: object) -> list:
        if not isinstance(v, list):
            raise SourceError("'series' must be a list")
        return v

    def _series_from_obj(self, o: object) -> TimeSeries:
        if not isinstance(o, dict) or "name" not in o:
            raise SourceError("each series needs a 'name'")
        name = str(o["name"])
        unit = str(o.get("unit", ""))
        points: list[tuple[float, float]] = []
        if "points" in o:
            for i, p in enumerate(o["points"]):
                if not isinstance(p, (list, tuple)) or len(p) != 2:
                    raise SourceError(f"series '{name}': each point must be [ts, value]")
                ts, val = p
                if not isinstance(val, (int, float)):
                    raise SourceError(f"series '{name}': value must be a number")
                points.append((_to_ts(ts, float(i)), float(val)))
        elif "value" in o:
            v = o["value"]
            if not isinstance(v, (int, float)):
                raise SourceError(f"series '{name}': value must be a number")
            points.append((0.0, float(v)))
        return TimeSeries(name=name, points=points, unit=unit)

    def _scalar_map(self, m: object) -> list[TimeSeries]:
        if not isinstance(m, dict):
            raise SourceError("scalar metrics must be a mapping of name → number")
        out: list[TimeSeries] = []
        for k, v in m.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(TimeSeries(name=str(k), points=[(0.0, float(v))]))
        if not out:
            raise SourceError("no numeric metrics found in source")
        return out

    def _parse_csv(self, text: str) -> list[TimeSeries]:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise SourceError("CSV has no header row")
        ts_col = next((c for c in reader.fieldnames if c and c.lower() in _TS_COLS), None)
        metric_cols = [c for c in reader.fieldnames if c and c != ts_col]
        series: dict[str, TimeSeries] = {c: TimeSeries(name=c) for c in metric_cols}
        for i, row in enumerate(reader):
            ts = _to_ts(row.get(ts_col, ""), float(i)) if ts_col else float(i)
            for c in metric_cols:
                cell = (row.get(c) or "").strip()
                if cell == "":
                    continue
                try:
                    series[c].points.append((ts, float(cell)))
                except ValueError:
                    raise SourceError(f"column '{c}': non-numeric value {cell!r}") from None
        for s in series.values():
            s.__post_init__()  # re-sort after appending
        return list(series.values())
