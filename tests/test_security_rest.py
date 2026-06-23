"""Security regression pins for the REST surface (skipped without fastapi)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from vitel.adapters.rest import build_app, serve  # noqa: E402
from vitel.config import Settings  # noqa: E402

_GOOD = {"series": {"error_rate": 0.05}}


def _client(**kw) -> TestClient:
    return TestClient(build_app(Settings(**kw)))


def test_non_loopback_without_token_refused() -> None:
    # serve() must fail closed when binding a routable interface with no token.
    with pytest.raises(SystemExit):
        serve(host="0.0.0.0", port=0)


def test_loopback_zero_config_works() -> None:
    c = _client()
    r = c.post("/check", json={"series": {"error_rate": 0.05}, "expect": ["must: error_rate < 1%"]})
    assert r.status_code == 200
    assert r.json()["verdict"] == "fail"


def test_auth_required_when_token_set() -> None:
    c = _client(api_token="s3cret")
    assert c.post("/check", json=_GOOD).status_code == 401
    assert c.post("/check", json=_GOOD, headers={"authorization": "Bearer wrong"}).status_code == 401
    ok = c.post("/check", json=_GOOD, headers={"authorization": "Bearer s3cret"})
    assert ok.status_code == 200


def test_non_ascii_auth_header_does_not_500() -> None:
    # A crafted non-ASCII bearer (latin-1 bytes on the wire) must 401, never 500: comparing as str
    # would raise TypeError in hmac.compare_digest, so we compare bytes.
    c = _client(api_token="s3cret")
    r = c.post("/check", json=_GOOD, headers={"authorization": "Bearer sécret".encode("latin-1")})
    assert r.status_code == 401


def test_host_path_source_refused() -> None:
    c = _client()
    r = c.post("/check", json={"source": "/etc/passwd", "expect": ["must: error_rate < 1%"]})
    assert r.status_code == 400
    assert "host-path" in r.json()["detail"]


def test_backend_not_in_allowlist_refused() -> None:
    c = _client()  # rest_enabled_backends empty by default
    r = c.post("/check", json={"source": "http://x/metrics", "backend": "scrape"})
    assert r.status_code == 400
    assert "not enabled" in r.json()["detail"]


def test_allowlisted_url_backend_keeps_ssrf_guard() -> None:
    # scrape is allowed, but the SSRF guard still blocks loopback → sanitized 400.
    c = _client(rest_enabled_backends=["scrape"])
    r = c.post("/check", json={"source": "http://127.0.0.1:9090/metrics", "backend": "scrape"})
    assert r.status_code == 400


def test_request_body_cap() -> None:
    c = _client(max_request_bytes=200)
    big = {"series": {f"m{i}": i for i in range(500)}}
    assert c.post("/check", json=big).status_code == 413


def test_openapi_disabled_when_token_set() -> None:
    c = _client(api_token="s3cret")
    # /openapi.json is disabled (None) so the schema isn't exposed; with auth it 404s.
    assert c.get("/openapi.json", headers={"authorization": "Bearer s3cret"}).status_code == 404


def test_healthz_open() -> None:
    c = _client(api_token="s3cret")
    assert c.get("/healthz").status_code == 200
