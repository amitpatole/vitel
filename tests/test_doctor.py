"""doctor must probe optional extras without importing them or crashing."""

from __future__ import annotations

from vitel.adapters.doctor import run_checks


def test_doctor_runs_without_optional_deps() -> None:
    # find_spec on a submodule whose parent is missing raises ModuleNotFoundError; doctor must not.
    checks = run_checks()
    names = {c.name for c in checks}
    assert "agentsensory contract" in names
    assert "file backend" in names
    # the contract + file backend are always ok
    by_name = {c.name: c for c in checks}
    assert by_name["agentsensory contract"].ok
    assert by_name["file backend"].ok
