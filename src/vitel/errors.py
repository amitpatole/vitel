"""vitel exception hierarchy."""

from __future__ import annotations


class VitelError(Exception):
    """Base class for all vitel errors."""


class ConfigError(VitelError):
    """Invalid configuration or unknown backend / option."""


class MissingDependencyError(VitelError):
    """An optional extra is required but not installed (e.g. ``vitel[prometheus]``)."""


class SourceError(VitelError):
    """A telemetry source could not be read or parsed."""


class UnsafeSourceError(SourceError):
    """A source was refused for safety reasons (SSRF, oversize, bad shape)."""


class BackendAuthError(VitelError):
    """A backend needs credentials that are not available (fail closed)."""
