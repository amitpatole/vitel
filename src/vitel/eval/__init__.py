"""Deterministic evaluation: turn measured series + an SLO into grounded issues and conformance."""

from __future__ import annotations

from .checks import GradeResult, evaluate

__all__ = ["GradeResult", "evaluate"]
