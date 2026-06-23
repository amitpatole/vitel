"""OpenMetrics scraping: pure parser + a live /metrics endpoint (the V2 acceptance)."""

from __future__ import annotations

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from agentsensory import Verdict

from vitel import check
from vitel.backends.scrape import parse_exposition
from vitel.config import Settings
from vitel.slo import SLO

_EXPO = """# HELP error_rate current error ratio
# TYPE error_rate gauge
error_rate 0.05
latency_ms{quantile="0.99"} 480 1620000000000
requests_total 1234
# a comment
malformed_line not_a_number
"""


def test_parse_exposition() -> None:
    series = {s.name: s for s in parse_exposition(_EXPO)}
    assert series["error_rate"].values == [0.05]
    assert series['latency_ms{quantile=0.99}'].values == [480.0]
    assert series['latency_ms{quantile=0.99}'].points[0][0] == 1620000000.0  # ms → s
    assert "malformed_line" not in series  # non-numeric sample skipped


@pytest.fixture()
def metrics_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = _EXPO.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/metrics"
    server.shutdown()


def test_check_grades_live_metrics_endpoint(metrics_server: str) -> None:
    pytest.importorskip("httpx")
    # loopback is blocked by the SSRF guard unless explicitly allowed
    settings = Settings(allow_private_targets=True)
    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    r = asyncio.run(check(metrics_server, slo=slo, backend="scrape", settings=settings))
    assert r.verdict == Verdict.FAIL
    assert r.backend == "scrape"


def test_scrape_loopback_blocked_by_default(metrics_server: str) -> None:
    pytest.importorskip("httpx")
    from vitel.errors import UnsafeSourceError

    slo = SLO.from_inputs(expect=["must: error_rate < 1%"])
    with pytest.raises(UnsafeSourceError):
        asyncio.run(check(metrics_server, slo=slo, backend="scrape", settings=Settings()))
