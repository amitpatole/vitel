"""Logging with a secret scrubber so credentials never reach the logs.

Register any secret value with :func:`register_secret` (config does this for resolved tokens/keys);
the filter masks every registered value in formatted log records.
"""

from __future__ import annotations

import logging

_SECRETS: set[str] = set()
_MASK = "***"


def register_secret(value: str | None) -> None:
    """Mark a value as secret so it is masked everywhere it appears in logs."""
    if value and len(value) >= 4:
        _SECRETS.add(value)


class _ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if _SECRETS and any(s in msg for s in _SECRETS):
            for s in _SECRETS:
                msg = msg.replace(s, _MASK)
            record.msg = msg
            record.args = ()
        return True


def get_logger(name: str = "vitel") -> logging.Logger:
    """Return a vitel logger with the secret-scrubbing filter attached once."""
    logger = logging.getLogger(name)
    if not any(isinstance(f, _ScrubFilter) for f in logger.filters):
        logger.addFilter(_ScrubFilter())
    return logger
