"""Metrics backends: pluggable sources that fetch normalized time series."""

from __future__ import annotations

from .base import MetricsBackend
from .registry import resolve_backend

__all__ = ["MetricsBackend", "resolve_backend"]
