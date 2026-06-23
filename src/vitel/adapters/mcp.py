"""MCP server — gives an MCP host (Claude, Cursor, …) the vitals feedback loop.

An MCP host runs locally on the agent's own machine, so a tool ``source`` may be a local path, a
``/metrics`` URL, or inline JSON, graded with default settings. Tools return JSON Reports / Handoffs.
Heavy/optional: install with ``vitel[mcp]``.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import MissingDependencyError
from ..slo import SLO

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - only without the [mcp] extra
    FastMCP = None  # type: ignore


def _slo(slo: str | None, expect: list[str] | None) -> SLO | None:
    if not (slo or expect):
        return None
    s = SLO.from_inputs(text=slo, expect=expect)
    return None if s.is_empty() else s


def build_server():
    if FastMCP is None:
        raise MissingDependencyError("MCP server needs the mcp package; pip install vitel[mcp]")

    mcp = FastMCP("vitel")

    @mcp.tool()
    async def vitals_check(
        source: str, expect: list[str] | None = None, slo: str | None = None,
        backend: str | None = None, window: float | None = None,
    ) -> dict:
        """Deterministically grade telemetry (thresholds / SLO / error-budget). No LLM, no egress.

        ``source`` is a JSON/CSV file path, inline JSON, or a metrics query/URL (with ``backend``).
        """
        from ..core import check

        report = await check(source, slo=_slo(slo, expect), settings=Settings(), backend=backend, window_s=window)
        return report.model_dump(mode="json")

    @mcp.tool()
    async def vitals_watch(
        source: str, expect: list[str] | None = None, slo: str | None = None,
        backend: str | None = None, window: float | None = None, interval: float | None = None,
    ) -> dict:
        """Grade over time: trend, ongoing degradation, liveness (e.g. slow latency regression)."""
        from ..core import watch

        report = await watch(source, slo=_slo(slo, expect), settings=Settings(), backend=backend,
                             window=window, interval=interval)
        return report.model_dump(mode="json")

    @mcp.tool()
    async def vitals_status(
        source: str, expect: list[str] | None = None, slo: str | None = None, backend: str | None = None,
    ) -> dict:
        """A concise vitals status: verdict, summary, and the top issues (for a quick health read)."""
        from ..core import check

        report = await check(source, slo=_slo(slo, expect), settings=Settings(), backend=backend)
        return {
            "verdict": report.verdict.value,
            "summary": report.summary,
            "issues": [
                {"kind": i.kind.value, "severity": i.severity.value, "message": i.message}
                for i in report.issues[:5]
            ],
        }

    @mcp.tool()
    async def vitals_render(source: str, backend: str | None = None, window: float | None = None) -> dict:
        """Normalized series + summary statistics (rates/percentiles), no grading."""
        from ..core import render

        return (await render(source, settings=Settings(), backend=backend, window_s=window)).model_dump(mode="json")

    @mcp.tool()
    async def vitals_analyze(
        source: str, expect: list[str] | None = None, slo: str | None = None,
        backend: str | None = None, window: float | None = None,
    ) -> dict:
        """Deterministic grade + anomaly/trend detection + optional LLM critique (may egress)."""
        from ..core import analyze

        report = await analyze(source, slo=_slo(slo, expect), settings=Settings(), backend=backend, window_s=window)
        return report.model_dump(mode="json")

    @mcp.tool()
    async def perceive_handoff(
        source: str, expect: list[str] | None = None, slo: str | None = None, backend: str | None = None,
    ) -> dict:
        """The vitals→brain handoff: grade and return the distilled signal.

        Returns {perceived, next_action, matches_intent, summary, todo[], open_questions[]} — what
        the brain should do next: 'done', 'revise' (act on todo), or 'review'.
        """
        from ..core import perceive

        return (await perceive(source, slo=_slo(slo, expect), settings=Settings(), backend=backend)).model_dump(mode="json")

    @mcp.tool()
    def doctor() -> dict:
        """Report install health: contract, backends, optional extras, REST posture."""
        from .doctor import run_checks

        return {"checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in run_checks()]}

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
