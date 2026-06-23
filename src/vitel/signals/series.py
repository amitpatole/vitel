"""The normalized time series — a name, a unit, and ordered (timestamp, value) points."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TimeSeries:
    """A single metric series. Timestamps are epoch seconds (floats), sorted ascending."""

    name: str
    points: list[tuple[float, float]] = field(default_factory=list)
    unit: str = ""

    def __post_init__(self) -> None:
        # Keep points ordered by time so last()/rate() are meaningful regardless of input order.
        self.points.sort(key=lambda p: p[0])

    @property
    def values(self) -> list[float]:
        return [v for _, v in self.points]

    @property
    def timestamps(self) -> list[float]:
        return [t for t, _ in self.points]

    def is_empty(self) -> bool:
        return not self.points

    def last(self) -> float | None:
        return self.points[-1][1] if self.points else None
