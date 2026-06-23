"""REST service (FastAPI) — for non-MCP / networked / CI agents.

Security (mirrors the reviewed sibling template):
- Provider creds are read server-side only, NEVER accepted in a request; per-request backend
  selection is limited to ``rest_enabled_backends`` so a remote caller can't redirect egress.
- A remote caller can NEVER make the server read a host file by path: for path-capable backends
  (file/otel) the source must be inline JSON; bare paths are refused. URL backends keep the SSRF
  guard on (loopback/private blocked unless the server opted in).
- Bearer-token auth in CONSTANT time (``hmac.compare_digest``); zero-config on loopback, REQUIRED
  off-loopback (``serve`` refuses to bind a routable host without a token).
- Request bodies are capped on the Content-Length header AND the raw stream (chunked can't bypass);
  heavy jobs run behind a concurrency semaphore.
- Errors are sanitized: only ``UnsafeSourceError`` text is returned; everything else is logged
  server-side with a generic message to the caller.
"""

from __future__ import annotations

import asyncio
import hmac

from ..config import Settings
from ..errors import MissingDependencyError, UnsafeSourceError, VitelError
from ..logging import get_logger
from ..slo import SLO

try:
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - only without the [serve] extra
    FastAPI = None  # type: ignore

log = get_logger("rest")
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1"}
# Backends whose source is a URL (SSRF-guarded in the backend) rather than a host path.
_URL_BACKENDS = {"scrape", "prometheus", "prom", "datadog", "cloudwatch"}
_PATH_BACKENDS = {"file", "otel", "otlp", None, ""}


def _is_loopback(host: str) -> bool:
    return host in _LOOPBACK


def _slo_from(slo: str | None, expect: list[str] | None) -> SLO | None:
    if not (slo or expect):
        return None
    s = SLO.from_inputs(text=slo, expect=expect)
    return None if s.is_empty() else s


def build_app(settings: Settings | None = None):
    if FastAPI is None:
        raise MissingDependencyError("REST service needs FastAPI; pip install vitel[serve]")

    from .. import __version__

    settings = settings or Settings()

    def _unauthorized(request: Request) -> bool:
        if request.url.path == "/healthz":
            return False
        token = settings.api_token
        if not token:
            return False
        provided = request.headers.get("authorization", "")
        # Compare as bytes (a non-ASCII header would make compare_digest on str raise → 500/401 leak).
        return not hmac.compare_digest(
            provided.encode("utf-8", "ignore"), f"Bearer {token}".encode()
        )

    def _auth(request: Request):
        if _unauthorized(request):
            raise HTTPException(status_code=401, detail="Unauthorized")

    app = FastAPI(
        title="vitel",
        version=__version__,
        dependencies=[Depends(_auth)],
        openapi_url=(None if settings.api_token else "/openapi.json"),
    )
    _job_sem = asyncio.Semaphore(settings.max_concurrent_jobs)

    @app.middleware("http")
    async def _gate(request: Request, call_next):
        # Authenticate BEFORE buffering the body (no DoS amplification on unauth callers).
        if _unauthorized(request):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        cap = settings.max_request_bytes
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > cap:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
        total = 0
        chunks: list[bytes] = []
        async for chunk in request.stream():
            total += len(chunk)
            if total > cap:
                return JSONResponse({"detail": "Request body too large."}, status_code=413)
            chunks.append(chunk)
        body = b"".join(chunks)
        request._body = body

        async def _replay():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = _replay
        return await call_next(request)

    async def _job_slot():
        async with _job_sem:
            yield

    def _http_error(e: Exception) -> HTTPException:
        if isinstance(e, UnsafeSourceError):
            return HTTPException(status_code=400, detail=str(e))
        log.warning("request failed: %s: %s", type(e).__name__, e)
        return HTTPException(status_code=400, detail="Could not read or grade the source.")

    def _resolve_source(body: dict) -> tuple[str, str | None]:
        """Return (source, backend) after enforcing the no-host-path and allowlist rules."""
        backend = body.get("backend")
        if backend and backend not in settings.rest_enabled_backends:
            raise HTTPException(
                status_code=400,
                detail=f"Backend {backend!r} is not enabled on this server. "
                f"Allowed: {settings.rest_enabled_backends or '(none — server default only)'}",
            )
        # Caller may send the metric data inline as a JSON object…
        series = body.get("series")
        if series is not None:
            import json

            return json.dumps(series), backend
        source = body.get("source")
        if not isinstance(source, str) or not source.strip():
            raise HTTPException(status_code=400, detail="provide 'series' (object) or 'source' (string)")
        if backend in _URL_BACKENDS:
            return source, backend  # SSRF guard runs inside the backend
        if backend in _PATH_BACKENDS and source.lstrip()[:1] not in ("{", "["):
            raise HTTPException(
                status_code=400,
                detail="host-path sources are not allowed over REST; send inline JSON in 'series'/'source'.",
            )
        return source, backend

    async def _grade(body: dict, fn_name: str):
        from .. import core

        source, backend = _resolve_source(body)
        slo = _slo_from(body.get("slo"), body.get("expect"))
        window = body.get("window")
        fn = getattr(core, fn_name)
        if fn_name == "watch":
            return await fn(source, slo=slo, settings=settings, backend=backend,
                            window=window, interval=body.get("interval"))
        if fn_name == "analyze":
            return await fn(source, slo=slo, settings=settings, backend=backend,
                            window_s=window, use_llm=bool(body.get("use_llm", False)))
        return await fn(source, slo=slo, settings=settings, backend=backend, window_s=window)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": __version__}

    @app.get("/doctor")
    def doctor_ep():
        from .doctor import run_checks

        return {"checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in run_checks(settings)]}

    @app.post("/check")
    async def check_ep(body: dict, _slot=Depends(_job_slot)):
        try:
            return (await _grade(body, "check")).model_dump(mode="json")
        except VitelError as e:
            raise _http_error(e) from e

    @app.post("/analyze")
    async def analyze_ep(body: dict, _slot=Depends(_job_slot)):
        try:
            return (await _grade(body, "analyze")).model_dump(mode="json")
        except VitelError as e:
            raise _http_error(e) from e

    @app.post("/render")
    async def render_ep(body: dict, _slot=Depends(_job_slot)):
        try:
            return (await _grade(body, "render")).model_dump(mode="json")
        except VitelError as e:
            raise _http_error(e) from e

    @app.post("/watch")
    async def watch_ep(body: dict, _slot=Depends(_job_slot)):
        try:
            return (await _grade(body, "watch")).model_dump(mode="json")
        except VitelError as e:
            raise _http_error(e) from e

    @app.post("/perceive")
    async def perceive_ep(body: dict, _slot=Depends(_job_slot)):
        try:
            return (await _grade(body, "perceive")).model_dump(mode="json")
        except VitelError as e:
            raise _http_error(e) from e

    return app


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    # Fail closed: never expose a routable interface without a token.
    if not _is_loopback(host) and not Settings().api_token:
        raise SystemExit(
            f"Refusing to bind non-loopback host {host!r} without auth. Set VITEL_API_TOKEN to "
            "expose the service (clients send 'Authorization: Bearer <token>'), or bind 127.0.0.1."
        )
    import uvicorn

    uvicorn.run(build_app(), host=host, port=port)


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
