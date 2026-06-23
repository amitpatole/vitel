"""Security regression pins for the file backend's untrusted-input handling.

V0's only attack surface is parsing attacker-controlled JSON/CSV. Every bound here must hold so a
refactor can't silently reopen a DoS / malformed-input hole.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from vitel.backends.file import FileBackend
from vitel.config import Settings
from vitel.errors import SourceError, UnsafeSourceError


def _fetch(backend: FileBackend, source: str):
    return asyncio.run(backend.fetch(source))


def test_oversize_inline_rejected() -> None:
    be = FileBackend(Settings(max_source_bytes=100))
    big = json.dumps({"metrics": {f"m{i}": i for i in range(1000)}})
    with pytest.raises(UnsafeSourceError):
        _fetch(be, big)


def test_too_many_points_rejected() -> None:
    be = FileBackend(Settings(max_points=10))
    payload = json.dumps({"series": [{"name": "x", "points": [[i, i] for i in range(100)]}]})
    with pytest.raises(UnsafeSourceError):
        _fetch(be, payload)


def test_oversize_file_rejected(tmp_path) -> None:
    p = tmp_path / "big.json"
    p.write_text(json.dumps({"metrics": {f"m{i}": i for i in range(5000)}}), encoding="utf-8")
    be = FileBackend(Settings(max_source_bytes=200))
    with pytest.raises(UnsafeSourceError):
        _fetch(be, str(p))


def test_malformed_json_rejected() -> None:
    be = FileBackend(Settings())
    with pytest.raises(SourceError):
        _fetch(be, "{not valid json")


def test_non_object_json_rejected() -> None:
    be = FileBackend(Settings())
    with pytest.raises(SourceError):
        _fetch(be, "[1, 2, 3]")


def test_deeply_nested_json_does_not_crash() -> None:
    # Pathological nesting must degrade to a SourceError, never an uncaught RecursionError.
    be = FileBackend(Settings())
    payload = "[" * 2000 + "]" * 2000
    with pytest.raises(SourceError):
        _fetch(be, payload)


def test_non_numeric_value_rejected() -> None:
    be = FileBackend(Settings())
    with pytest.raises(SourceError):
        _fetch(be, '{"series": [{"name": "x", "points": [[0, "boom"]]}]}')


def test_missing_file_rejected() -> None:
    be = FileBackend(Settings())
    with pytest.raises(SourceError):
        _fetch(be, "/no/such/path/series.json")
