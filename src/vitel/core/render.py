"""``render`` — decode a source into normalized series + trustworthy summary statistics."""

from __future__ import annotations

from ..backends import resolve_backend
from ..config import Settings
from ..models import RenderResult
from ..signals.series import TimeSeries
from ..signals.stats import summarize


async def render(
    source: str,
    *,
    settings: Settings | None = None,
    backend: str | None = None,
    window_s: float | None = None,
) -> RenderResult:
    """Fetch ``source`` via the selected backend and summarize each series."""
    settings = settings or Settings()
    be = resolve_backend(backend, settings)
    series = await be.fetch(source, window_s=window_s)
    return _render_from_series(series, backend=be.name, source_label=_label(source), window_s=window_s)


def _label(source: str) -> str:
    s = source.strip()
    return "<inline>" if s[:1] in ("{", "[") else source


def _render_from_series(
    series: list[TimeSeries], *, backend: str, source_label: str, window_s: float | None
) -> RenderResult:
    return RenderResult(
        backend=backend,
        source_label=source_label,
        window_s=window_s,
        series=[summarize(s) for s in series],
    )
