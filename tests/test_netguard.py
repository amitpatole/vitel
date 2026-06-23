"""SSRF guard regression pins."""

from __future__ import annotations

import pytest

from vitel.errors import UnsafeSourceError
from vitel.netguard import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9090",
        "http://localhost:9090",
        "http://10.0.0.5/api",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://[::1]:9090",
        "http://0.0.0.0",
    ],
)
def test_blocks_non_public(url: str) -> None:
    with pytest.raises(UnsafeSourceError):
        validate_url(url)


@pytest.mark.parametrize("url", ["ftp://example.com", "file:///etc/passwd", "gopher://x"])
def test_blocks_bad_scheme(url: str) -> None:
    with pytest.raises(UnsafeSourceError):
        validate_url(url)


def test_allows_public_ip() -> None:
    assert validate_url("http://8.8.8.8/api/v1/query") == "http://8.8.8.8/api/v1/query"


def test_allow_private_override() -> None:
    # explicit opt-in lets loopback through (local Prometheus)
    assert validate_url("http://127.0.0.1:9090", allow_private=True).startswith("http://127.0.0.1")
