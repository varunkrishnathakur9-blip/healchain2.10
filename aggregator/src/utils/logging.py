# HealChain Aggregator - Logging Utilities
# structured logging

"""
HealChain Aggregator – Logging Utilities
=======================================

Responsibilities:
-----------------
- Centralized logging configuration
- Consistent formatting across all modules
- Environment-driven log level control

Design Goals:
-------------
- Deterministic logs (no randomness)
- Human-readable + machine-parseable
- Minimal overhead
"""

import logging
import os
import sys
from typing import Optional


# -------------------------------------------------------------------
# Configuration Defaults
# -------------------------------------------------------------------

DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def setup_logging(
    *,
    level: Optional[str] = None,
    stream=sys.stdout,
):
    """
    Initialize global logging configuration.

    Parameters:
    -----------
    level : str, optional
        Logging level override (DEBUG, INFO, WARNING, ERROR)
        If None, reads from LOG_LEVEL env var.

    stream :
        Output stream (default: stdout)
    """

    log_level_str = (
        level
        or os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    ).upper()

    try:
        log_level = getattr(logging, log_level_str)
    except AttributeError:
        raise ValueError(f"Invalid log level: {log_level_str}")

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(stream)
        ],
        force=True,  # override any previous config
    )

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info(
        f"[Logging] Initialized | level={log_level_str}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a module-scoped logger.

    Usage:
    ------
    logger = get_logger(__name__)
    """
    return logging.getLogger(name)
