"""Structured logging for Recon.

Designed with local-first privacy: avoids logging raw row values by default,
logging only dataset metadata, column identities, statistics, and rule IDs.
"""

import logging
import sys
from typing import Any


def configure_logging(level: int = logging.INFO, stream: Any = None) -> logging.Logger:
    """Configures structured logger for Recon CLI and library operations."""
    logger = logging.getLogger("recon")
    logger.setLevel(level)

    if stream is not None:
        logger.handlers.clear()
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    elif not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = configure_logging()


def log_safe_event(event_name: str, **kwargs: Any) -> None:
    """Logs an event with safe metadata, explicitly disallowing raw row payloads."""
    # Strip any potential row payloads if accidentally passed
    filtered = {
        k: v for k, v in kwargs.items()
        if not k.startswith("raw_") and k not in ("row", "record", "payload")
    }
    details = " ".join(f"{k}={v}" for k, v in sorted(filtered.items()))
    logger.info(f"{event_name} {details}".strip())
