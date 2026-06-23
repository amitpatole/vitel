"""``vitel`` command-line interface (Typer)."""

from __future__ import annotations

import asyncio

import typer

from .. import __version__
from ..config import Settings
from ..core import analyze as _analyze
from ..core import check as _check
from ..core import perceive as _perceive
from ..core import render as _render
from ..core import watch as _watch
from ..errors import VitelError
from ..slo import SLO
from .doctor import run_checks

app = typer.Typer(
    name="vitel",
    help="Vitals / interoception sense — graded observability (pass/warn/fail) on metrics, SLOs and error budgets.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the vitel version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Check the install: contract, backends, optional extras, REST posture."""
    all_ok = True
    for c in run_checks():
        mark = "ok " if c.ok else "MISS"
        if not c.ok and c.name in ("agentsensory contract",):
            all_ok = False
        typer.echo(f"[{mark}] {c.name}: {c.detail}")
    raise typer.Exit(code=0 if all_ok else 1)


def _slo_from(slo_text: str | None, expect: list[str] | None) -> SLO | None:
    if not slo_text and not expect:
        return None
    s = SLO.from_inputs(text=slo_text, expect=expect)
    return None if s.is_empty() else s


def _print_report(report) -> None:
    typer.echo(f"{report.verdict.value.upper()}: {report.summary}")
    for issue in report.issues:
        typer.echo(f"  - [{issue.severity.value}] {issue.kind.value}: {issue.message}")


def _gate_code(verdict: str, warn_as_fail: bool) -> int:
    """CI gate exit code: 1 on FAIL (and on WARN when --warn-as-fail), else 0."""
    if verdict == "fail":
        return 1
    if verdict == "warn" and warn_as_fail:
        return 1
    return 0


@app.command()
def check(
    source: str = typer.Argument(..., help="Path to a JSON/CSV series file, or inline JSON."),
    expect: list[str] = typer.Option(
        None, "--expect", "-e", help="A requirement, e.g. 'must: error_rate < 1%' (repeatable)."
    ),
    slo: str = typer.Option(None, "--slo", help="Free-text SLO description."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name (default: file)."),
    window: float = typer.Option(None, "--window", "-w", help="Evaluation window (seconds)."),
    warn_as_fail: bool = typer.Option(
        False, "--warn-as-fail", help="Exit non-zero on WARN too (stricter deploy gate)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit the full Report as JSON."),
) -> None:
    """Deterministically grade a telemetry source. Exits non-zero on FAIL (CI gate)."""
    try:
        report = asyncio.run(
            _check(source, slo=_slo_from(slo, expect), settings=Settings(), backend=backend, window_s=window)
        )
    except VitelError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from None

    if json_out:
        typer.echo(report.model_dump_json(indent=2))
    else:
        _print_report(report)
    raise typer.Exit(code=_gate_code(report.verdict.value, warn_as_fail))


@app.command()
def render(
    source: str = typer.Argument(..., help="Path to a JSON/CSV series file, or inline JSON."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name (default: file)."),
    window: float = typer.Option(None, "--window", "-w", help="Window (seconds)."),
) -> None:
    """Decode a source into normalized series + summary statistics (no grading)."""
    try:
        result = asyncio.run(_render(source, settings=Settings(), backend=backend, window_s=window))
    except VitelError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from None
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def watch(
    source: str = typer.Argument(..., help="Source (file/inline, or a URL for live backends)."),
    expect: list[str] = typer.Option(None, "--expect", "-e", help="A requirement (repeatable)."),
    slo: str = typer.Option(None, "--slo", help="Free-text SLO description."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name."),
    window: float = typer.Option(None, "--window", "-w", help="Total window (seconds)."),
    interval: float = typer.Option(None, "--interval", "-i", help="Poll interval for live backends."),
    json_out: bool = typer.Option(False, "--json", help="Emit the full Report as JSON."),
) -> None:
    """Grade a source over time: trend, degradation, liveness. Exits non-zero on FAIL."""
    try:
        report = asyncio.run(
            _watch(source, window=window, interval=interval, slo=_slo_from(slo, expect),
                   settings=Settings(), backend=backend)
        )
    except VitelError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from None
    if json_out:
        typer.echo(report.model_dump_json(indent=2))
    else:
        _print_report(report)
    raise typer.Exit(code=1 if report.verdict.value == "fail" else 0)


@app.command()
def analyze(
    source: str = typer.Argument(..., help="Path to a JSON/CSV series file, or inline JSON."),
    expect: list[str] = typer.Option(None, "--expect", "-e", help="A requirement (repeatable)."),
    slo: str = typer.Option(None, "--slo", help="Free-text SLO description."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name."),
    window: float = typer.Option(None, "--window", "-w", help="Evaluation window (seconds)."),
    no_llm: bool = typer.Option(False, "--no-llm", help="Skip the optional LLM critique."),
    json_out: bool = typer.Option(False, "--json", help="Emit the full Report as JSON."),
) -> None:
    """Deterministic grade + anomaly/trend detection + optional LLM critique. Exits non-zero on FAIL."""
    try:
        report = asyncio.run(
            _analyze(source, slo=_slo_from(slo, expect), settings=Settings(), backend=backend,
                     window_s=window, use_llm=not no_llm)
        )
    except VitelError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from None
    if json_out:
        typer.echo(report.model_dump_json(indent=2))
    else:
        _print_report(report)
    raise typer.Exit(code=1 if report.verdict.value == "fail" else 0)


@app.command()
def perceive(
    source: str = typer.Argument(..., help="Path to a JSON/CSV series file, or inline JSON."),
    expect: list[str] = typer.Option(None, "--expect", "-e", help="A requirement (repeatable)."),
    slo: str = typer.Option(None, "--slo", help="Free-text SLO description."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name."),
    window: float = typer.Option(None, "--window", "-w", help="Evaluation window (seconds)."),
) -> None:
    """Emit the afferent Handoff (for a brain like Verel) as JSON. Exits non-zero unless next_action=done."""
    try:
        handoff = asyncio.run(
            _perceive(source, slo=_slo_from(slo, expect), settings=Settings(), backend=backend, window_s=window)
        )
    except VitelError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from None
    typer.echo(handoff.model_dump_json(indent=2))
    raise typer.Exit(code=0 if handoff.next_action.value == "done" else 1)


@app.command()
def demo() -> None:
    """Grade a synthetic degrading service (budget-burn FAIL) then its fix (PASS). No API key."""
    from ._demo_assets import degrading_source, demo_slo, healthy_source

    slo = demo_slo()
    typer.echo("vitel demo — synthetic service graded against a 99.9% SLO (no API key, no network)\n")

    typer.echo("1) degrading service:")
    before = asyncio.run(_check(degrading_source(), slo=slo, settings=Settings()))
    _print_report(before)

    typer.echo("\n2) after the fix:")
    after = asyncio.run(_check(healthy_source(), slo=slo, settings=Settings()))
    _print_report(after)

    ok = before.verdict.value == "fail" and after.verdict.value == "pass"
    typer.echo("\n" + ("demo OK: budget-burn FAIL → fixed → PASS" if ok else "demo did not behave as expected"))
    raise typer.Exit(code=0 if ok else 1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
