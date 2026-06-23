"""``vitel doctor`` — probe the install without importing heavy deps."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec

from ..config import Settings


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _has_module(dotted: str) -> bool:
    """True if a module is importable, without importing it. Safe when a parent is missing."""
    try:
        return find_spec(dotted) is not None
    except (ModuleNotFoundError, ValueError):
        return False


# (label, probe spec, install hint) for each optional surface.
_OPTIONAL = [
    ("prometheus", "prometheus_api_client", "pip install vitel[prometheus]"),
    ("otel", "opentelemetry.sdk", "pip install vitel[otel]"),
    ("cloud", "boto3", "pip install vitel[cloud]"),
    ("psutil", "psutil", "pip install vitel[psutil]"),
    ("serve (REST)", "fastapi", "pip install vitel[serve]"),
    ("mcp", "mcp", "pip install vitel[mcp]"),
]


def run_checks(settings: Settings | None = None) -> list[Check]:
    settings = settings or Settings()
    checks: list[Check] = []

    # Core contract import.
    try:
        import agentsensory  # noqa: F401

        checks.append(Check("agentsensory contract", True, f"v{agentsensory.__version__}"))
    except Exception as e:  # pragma: no cover - import always succeeds in a valid install
        checks.append(Check("agentsensory contract", False, str(e)))

    # Built-in file backend is always available.
    checks.append(Check("file backend", True, "JSON/CSV series (built-in)"))

    # Optional surfaces (presence only — never import the heavy module).
    for label, mod, hint in _OPTIONAL:
        present = _has_module(mod)
        checks.append(Check(label, present, "installed" if present else f"not installed — {hint}"))

    # REST auth posture.
    checks.append(
        Check(
            "REST auth token",
            True,
            "set (auth enabled)" if settings.api_token else "unset (loopback-only; required off-loopback)",
        )
    )
    return checks
