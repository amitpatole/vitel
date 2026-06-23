"""Signal processing: normalized time series and the trustworthy derived statistics."""

from __future__ import annotations

from .series import TimeSeries
from .stats import percentile, summarize

__all__ = ["TimeSeries", "percentile", "summarize"]
