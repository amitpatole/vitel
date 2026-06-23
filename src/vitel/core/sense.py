"""``Vitals`` — the object that satisfies the ``agentsensory.Sense`` protocol.

The protocol requires ``name``, ``available()`` and async ``analyze(...)``. vitel's deterministic
``check`` is the main path; ``analyze`` adds LLM critique in a later phase. For V0, ``analyze``
delegates to ``check`` (no LLM).
"""

from __future__ import annotations

from ..config import Settings
from ..models import Report
from ..slo import SLO
from .check import check


class Vitals:
    name = "vitel"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def available(self) -> bool:
        return True

    async def analyze(self, source: str, **kwargs: object) -> Report:
        """Grade ``source``. Accepts ``slo``, ``backend`` and ``window_s`` keyword args."""
        slo = kwargs.get("slo")
        backend = kwargs.get("backend")
        window_s = kwargs.get("window_s")
        return await check(
            source,
            slo=slo if isinstance(slo, SLO) else None,
            settings=self.settings,
            backend=backend if isinstance(backend, str) else None,
            window_s=window_s if isinstance(window_s, (int, float)) else None,
        )
