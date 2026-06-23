"""vitel — the vitals / interoception sense for AI agents.

Graded observability: turn telemetry (metrics, SLOs, error budgets) into a pass/warn/fail
``Report`` whose issues are grounded in a ``Metric`` (name, window, observed vs threshold,
burn-rate). Built on the shared ``agentsensory`` contract; ``check`` is the deterministic main path.

The light base imports nothing heavy. CLI / MCP / REST and the metrics backends live behind
extras and are lazy-imported on first use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "0.1.0"

if TYPE_CHECKING:  # import-time names for type checkers only
    from .config import Settings
    from .core import Vitals, analyze, check, perceive, render, watch
    from .models import Issue, IssueKind, IssueSource, Metric, RenderResult, Report
    from .slo import SLO

_LAZY = {
    "check": ("vitel.core", "check"),
    "analyze": ("vitel.core", "analyze"),
    "watch": ("vitel.core", "watch"),
    "perceive": ("vitel.core", "perceive"),
    "render": ("vitel.core", "render"),
    "Vitals": ("vitel.core", "Vitals"),
    "Settings": ("vitel.config", "Settings"),
    "SLO": ("vitel.slo", "SLO"),
    "Report": ("vitel.models", "Report"),
    "Issue": ("vitel.models", "Issue"),
    "IssueKind": ("vitel.models", "IssueKind"),
    "IssueSource": ("vitel.models", "IssueSource"),
    "Metric": ("vitel.models", "Metric"),
    "RenderResult": ("vitel.models", "RenderResult"),
}


def __getattr__(name: str) -> object:
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module 'vitel' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(target[0]), target[1])


__all__ = [
    "__version__",
    "check",
    "analyze",
    "watch",
    "perceive",
    "render",
    "Vitals",
    "Settings",
    "SLO",
    "Report",
    "Issue",
    "IssueKind",
    "IssueSource",
    "Metric",
    "RenderResult",
]
