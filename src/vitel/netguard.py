"""SSRF guard for remote metric sources.

Any URL vitel fetches (Prometheus, OTLP, cloud) is validated here first: scheme must be http/https,
and every IP the host resolves to must be public unless ``allow_private`` is set. This blocks
loopback, link-local (incl. the ``169.254.169.254`` cloud-metadata endpoint), private and other
reserved ranges.

Residual risk: a DNS-rebinding TOCTOU between this check and the socket connect is not eliminated
here; callers that need that guarantee must pin the validated IP at connect time.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from .errors import UnsafeSourceError

_ALLOWED_SCHEMES = {"http", "https"}


def _ip_is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_private
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def validate_url(url: str, *, allow_private: bool = False) -> str:
    """Validate a URL for outbound fetch. Returns it unchanged or raises ``UnsafeSourceError``."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeSourceError(f"unsupported URL scheme {parsed.scheme!r} (need http/https)")
    host = parsed.hostname
    if not host:
        raise UnsafeSourceError("URL has no host")
    if allow_private:
        return url
    try:
        infos = socket.getaddrinfo(host, parsed.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise UnsafeSourceError(f"cannot resolve host {host!r}: {e}") from None
    resolved = {str(info[4][0]) for info in infos}
    if not resolved:
        raise UnsafeSourceError(f"host {host!r} did not resolve")
    for ip in resolved:
        if not _ip_is_public(ip):
            raise UnsafeSourceError(
                f"refusing to fetch {host!r}: resolves to non-public address {ip} "
                f"(set allow_private_targets to override)"
            )
    return url
