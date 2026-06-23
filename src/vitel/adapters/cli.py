"""``vitel`` command-line interface (Typer)."""

from __future__ import annotations

import asyncio

import typer

from .. import __version__
from ..config import Settings
from ..core import check as _check
from ..core import render as _render
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


@app.command()
def check(
    source: str = typer.Argument(..., help="Path to a JSON/CSV series file, or inline JSON."),
    expect: list[str] = typer.Option(
        None, "--expect", "-e", help="A requirement, e.g. 'must: error_rate < 1%' (repeatable)."
    ),
    slo: str = typer.Option(None, "--slo", help="Free-text SLO description."),
    backend: str = typer.Option(None, "--backend", "-b", help="Backend name (default: file)."),
    window: float = typer.Option(None, "--window", "-w", help="Evaluation window (seconds)."),
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
        typer.echo(f"{report.verdict.value.upper()}: {report.summary}")
        for issue in report.issues:
            typer.echo(f"  - [{issue.severity.value}] {issue.kind.value}: {issue.message}")
    raise typer.Exit(code=1 if report.verdict.value == "fail" else 0)


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
