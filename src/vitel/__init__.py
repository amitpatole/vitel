"""vitel — the vitals / interoception sense for AI agents.

Graded observability: turn telemetry (metrics, SLOs, error budgets) into a pass/warn/fail
``Report`` whose issues are grounded in a ``Metric`` (name, window, observed vs threshold,
burn-rate). Built on the shared ``agentsensory`` contract; ``check`` is the deterministic main path.

The light base imports nothing heavy. CLI / MCP / REST and the metrics backends live behind
extras and are lazy-imported on first use.
"""

from __future__ import annotations

__version__ = "0.0.0"

__all__ = ["__version__"]
