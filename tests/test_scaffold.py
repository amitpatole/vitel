"""Scaffold pins: light import, version drift-guard, contract conformance, fail-closed defaults."""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import version

from agentsensory import Handoff, Sense, Verdict

import vitel
from vitel import Settings, Vitals


def test_version_matches_metadata() -> None:
    # Drift-guard: the packaged metadata and the __version__ string must agree.
    assert version("vitel") == vitel.__version__


def test_light_import_pulls_no_heavy_deps() -> None:
    # Importing vitel must not drag in fastapi / prometheus / mcp / boto3 / opentelemetry.
    code = (
        "import vitel, sys;"
        "heavy=[m for m in ('fastapi','prometheus_api_client','mcp','boto3','opentelemetry') "
        "if m in sys.modules];"
        "assert not heavy, heavy"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_vitals_satisfies_sense_protocol() -> None:
    assert isinstance(Vitals(), Sense)


def test_no_default_api_token() -> None:
    # Fail closed: there is never a default REST auth token.
    assert Settings().api_token is None


def test_report_and_handoff_round_trip() -> None:
    from vitel.models import Report

    r = Report(verdict=Verdict.PASS, summary="ok")
    # Pydantic round-trip (our stand-in for assert_valid_report).
    assert Report.model_validate_json(r.model_dump_json()).verdict == Verdict.PASS
    h = r.to_handoff()
    assert isinstance(h, Handoff)
    assert Handoff.model_validate_json(h.model_dump_json()).perceived == Verdict.PASS
