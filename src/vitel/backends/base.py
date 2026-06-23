"""The metrics-backend protocol every source implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..signals.series import TimeSeries


@runtime_checkable
class MetricsBackend(Protocol):
    """A source of normalized time series (a file, Prometheus, OTLP, a cloud provider, psutil…)."""

    name: str

    def available(self) -> bool:
        """True when this backend's dependencies/credentials are present."""
        ...

    async def fetch(self, source: str, *, window_s: float | None = None) -> list[TimeSeries]:
        """Read ``source`` and return its series. Raises ``SourceError`` on bad input."""
        ...

    async def critique(self, series: list[TimeSeries], prompt: str) -> str:
        """Optional LLM critique of the signal. Returns "" unless the backend supports it."""
        ...
