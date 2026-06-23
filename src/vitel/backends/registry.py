"""Backend resolution: built-in fast paths first, then third-party entry points."""

from __future__ import annotations

from importlib.metadata import entry_points

from ..config import Settings
from ..errors import ConfigError
from .base import MetricsBackend
from .file import FileBackend

_ENTRY_GROUP = "vitel.backends"


def resolve_backend(name: str | None = None, settings: Settings | None = None) -> MetricsBackend:
    """Return the requested backend. Defaults to ``settings.backend`` (``file``)."""
    settings = settings or Settings()
    name = name or settings.backend or "file"

    if name == "file":
        return FileBackend(settings)
    if name in ("prometheus", "prom"):
        from .prometheus import PrometheusBackend

        return PrometheusBackend(settings)

    for ep in entry_points(group=_ENTRY_GROUP):
        if ep.name == name:
            factory = ep.load()
            return factory(settings) if callable(factory) else factory

    raise ConfigError(f"unknown backend {name!r}")
