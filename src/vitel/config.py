"""Runtime settings, resolved from ``VITEL_*`` env vars (and an optional ``.env``).

No secret has a default: tokens/keys resolve from env → per-provider key file → ``None`` (fail
closed). Resolved secrets are registered with the log scrubber so they can't leak.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_cache_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging import register_secret

# Conventional per-provider key-file locations (matches the sibling organs' layout under ~/.config).
_KEY_FILES = {
    "ollama": Path.home() / ".config" / "ollama" / "key",
    "anthropic": Path.home() / ".config" / "Anthropic" / "key",
    "openai": Path.home() / ".config" / "OpenAI" / "key",
}


def _default_cache_dir() -> Path:
    return Path(user_cache_dir("vitel"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VITEL_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    # Backend selection
    backend: str = "file"

    # Prometheus (vitel[prometheus])
    prometheus_url: str | None = None

    # OTLP (vitel[otel])
    otlp_endpoint: str | None = None

    # LLM critique (vitel[—], used by analyze)
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")

    # Resource caps (bound anything an attacker / bad input controls)
    max_source_bytes: int = 50_000_000
    max_points: int = 1_000_000
    max_polls: int = 600  # hard cap on watch() poll iterations (bounds a live-watch request)
    request_timeout_s: float = 30.0

    # SSRF policy for remote metric sources
    allow_private_targets: bool = False

    # REST service (vitel[serve]) — fail closed off loopback
    api_token: str | None = Field(default=None, validation_alias="VITEL_API_TOKEN")
    max_concurrent_jobs: int = 4
    max_request_bytes: int = 10_000_000
    rest_enabled_backends: list[str] = Field(default_factory=list)

    # Workspace
    cache_dir: Path = Field(default_factory=_default_cache_dir)

    def key_for(self, provider: str) -> str | None:
        """Resolve a provider credential: explicit field → key file → None (registered for scrubbing)."""
        field = {"anthropic": self.anthropic_api_key, "openai": self.openai_api_key}.get(provider)
        if field:
            register_secret(field)
            return field
        path = _KEY_FILES.get(provider)
        if path and path.is_file():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                register_secret(value)
                return value
        return None
