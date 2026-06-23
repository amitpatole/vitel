"""Deterministic evaluation: turn measured series + an SLO into grounded issues and conformance."""

from __future__ import annotations

from .checks import GradeResult, evaluate
from .trends import analyze_trends, detect_flatline, detect_spikes

__all__ = ["GradeResult", "evaluate", "analyze_trends", "detect_flatline", "detect_spikes"]
