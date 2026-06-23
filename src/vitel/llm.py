"""Optional LLM critique for ``analyze`` — local Ollama by default, fail-soft.

``analyze`` is the only path that may reach an LLM, and it must never block a deterministic verdict:
if no model is reachable the critique is simply omitted. The key (if any) is read from settings and
registered with the log scrubber.
"""

from __future__ import annotations

from .config import Settings
from .models import RenderResult


def _prompt(render: RenderResult) -> str:
    lines = [
        "You are an SRE reviewing service vitals. In 1-2 sentences, note any anomaly, risk, or",
        "likely root cause you see. Be terse and specific. Signals:",
    ]
    for s in render.series:
        lines.append(
            f"- {s.name}: last={s.last} mean={s.mean} p99={s.p99} min={s.min} max={s.max} (n={s.count})"
        )
    return "\n".join(lines)


def critique(render: RenderResult, *, settings: Settings | None = None) -> tuple[str, str | None]:
    """Return ``(note, model)``. ``note`` is "" when no LLM is reachable (fail-soft)."""
    settings = settings or Settings()
    try:
        import httpx
    except ImportError:
        return "", None

    url = f"{settings.ollama_url.rstrip('/')}/api/generate"
    payload = {"model": settings.ollama_model, "prompt": _prompt(render), "stream": False}
    try:
        with httpx.Client(timeout=min(settings.request_timeout_s, 20.0)) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
    except Exception:
        # fail-soft: a missing/broken Ollama must not affect the deterministic grade
        return "", None
    return text, settings.ollama_model if text else None
