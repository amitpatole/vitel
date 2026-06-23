"""Error-budget mathematics: budget, burn-rate, and remaining-budget.

Given an availability target ``T`` (e.g. ``0.999``), the error budget is ``EB = 1 - T``. For an
observed error ratio ``ER`` over a window:

- **burn rate** ``BR = ER / EB`` — how many times faster than sustainable the budget is being spent.
  ``BR = 1`` exactly exhausts the budget over the SLO period; the classic fast-burn page is ``BR ≥ 14.4``.
- **budget remaining** ``1 - ER/EB`` — fraction of the budget left (negative once blown).

Multi-window burn (Google SRE): alert only when a long *and* a short window both burn hot, which
catches sustained burn while rejecting single-spike noise.
"""

from __future__ import annotations

from .series import TimeSeries
from .stats import aggregate

DEFAULT_ERROR_METRIC = "error_rate"
# Classic multi-window fast-burn threshold (2% of a 30d budget in 1h).
FAST_BURN = 14.4


def error_budget(target: float) -> float:
    """The error budget ``1 - target``. Raises for a nonsensical target."""
    if not 0.0 < target < 1.0:
        raise ValueError(f"availability target must be in (0, 1), got {target}")
    return 1.0 - target


def burn_rate(target: float, error_ratio: float) -> float:
    return error_ratio / error_budget(target)


def budget_remaining(target: float, error_ratio: float) -> float:
    """Fraction of error budget remaining (1.0 = untouched, <0 = blown)."""
    return 1.0 - error_ratio / error_budget(target)


def multi_window_hot(target: float, slow_error: float, fast_error: float, *, page_at: float = FAST_BURN) -> bool:
    """True when both the slow and fast windows burn at/above ``page_at`` — a real fast-burn signal."""
    return burn_rate(target, slow_error) >= page_at and burn_rate(target, fast_error) >= page_at


def derived_budget_series(
    by_name: dict[str, TimeSeries],
    *,
    target: float,
    error_metric: str = DEFAULT_ERROR_METRIC,
    reducer: str = "mean",
) -> list[TimeSeries]:
    """Compute ``burn_rate`` / ``error_budget_remaining`` series from an error-rate series.

    Returns an empty list when the error metric is absent so callers can fail closed.
    """
    ts = by_name.get(error_metric)
    if ts is None or ts.is_empty():
        return []
    slow = aggregate(ts, reducer)
    if slow is None:
        return []
    last = ts.last()
    fast = last if last is not None else slow
    t = ts.timestamps[-1]
    return [
        TimeSeries(name="burn_rate", points=[(t, burn_rate(target, slow))], unit="x"),
        TimeSeries(name="burn_rate_fast", points=[(t, burn_rate(target, fast))], unit="x"),
        TimeSeries(
            name="error_budget_remaining",
            points=[(t, budget_remaining(target, slow))],
            unit="ratio",
        ),
    ]
