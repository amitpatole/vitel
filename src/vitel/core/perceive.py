"""``perceive`` — the afferent signal for a brain (Verel): grade, then distill to a ``Handoff``.

Verel's gate withholds "done" until required senses return a passing verdict. ``perceive`` runs the
deterministic ``check`` and returns ``Report.to_handoff()``: a failing post-deploy vitals verdict
yields ``next_action = REVISE`` (never ``DONE``), so the brain cannot close the task.
"""

from __future__ import annotations

from agentsensory import Handoff

from ..config import Settings
from ..slo import SLO
from .check import check


async def perceive(
    source: str,
    *,
    slo: SLO | None = None,
    settings: Settings | None = None,
    backend: str | None = None,
    window_s: float | None = None,
) -> Handoff:
    """Grade ``source`` deterministically and return the distilled Handoff for the brain."""
    report = await check(
        source, slo=slo, settings=settings or Settings(), backend=backend, window_s=window_s
    )
    return report.to_handoff()
