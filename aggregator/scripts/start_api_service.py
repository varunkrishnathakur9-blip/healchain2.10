#!/usr/bin/env python3
"""
HealChain Aggregator – HTTP API Service Startup Script
======================================================

Starts the HTTP API service that the backend can call to trigger aggregation.

Usage:
    python scripts/start_api_service.py

Environment Variables:
    AGGREGATOR_PORT: Port to listen on (default: 5002)
    AGGREGATOR_HOST: Host to bind to (default: 0.0.0.0)
    LOG_LEVEL: Logging level (default: INFO)
"""

import os
import sys
import getpass

# Load environment variables from .env file
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT_DIR, ".env")

if os.path.exists(ENV_FILE):
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)


def _is_valid_private_scalar(raw: str) -> bool:
    try:
        val = int(raw.strip(), 0)
        return val > 0
    except Exception:
        return False


def prompt_aggregator_private_key():
    """
    Prompt for AGGREGATOR_SK at service startup (hidden input).
    - Press Enter to keep current value (if present).
    - Accepts decimal or 0x-prefixed hex.
    """
    prompt_enabled = os.getenv("PROMPT_FOR_AGGREGATOR_SK", "1") != "0"
    if not prompt_enabled:
        return

    current = (os.getenv("AGGREGATOR_SK") or "").strip()
    if not sys.stdin.isatty():
        # Non-interactive shell: do not block.
        if not current:
            raise EnvironmentError(
                "AGGREGATOR_SK is missing and interactive prompt is unavailable. "
                "Set AGGREGATOR_SK in environment or disable prompt with PROMPT_FOR_AGGREGATOR_SK=0."
            )
        return

    while True:
        if current:
            user_input = getpass.getpass(
                "Enter AGGREGATOR_SK (decimal or 0x hex) "
                "[press Enter to keep current]: "
            ).strip()
            if not user_input:
                return
            candidate = user_input
        else:
            candidate = getpass.getpass(
                "Enter AGGREGATOR_SK (decimal or 0x hex): "
            ).strip()
            if not candidate:
                print("AGGREGATOR_SK is required.")
                continue

        if not _is_valid_private_scalar(candidate):
            print("Invalid AGGREGATOR_SK. Use a positive decimal or 0x-prefixed hex scalar.")
            continue

        os.environ["AGGREGATOR_SK"] = candidate
        return


prompt_aggregator_private_key()

# Ensure src/ is on PYTHONPATH
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from api_service import app
from utils.logging import setup_logging, get_logger

# Initialize logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("api_service.startup")

if __name__ == "__main__":
    port = int(os.getenv("AGGREGATOR_PORT", "5002"))
    host = os.getenv("AGGREGATOR_HOST", "0.0.0.0")
    
    logger.info("=" * 60)
    logger.info("HealChain Aggregator HTTP API Service")
    logger.info("=" * 60)
    logger.info(f"Starting on {host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/api/health")
    logger.info(f"Aggregate endpoint: http://{host}:{port}/api/aggregate")
    logger.info("=" * 60)
    
    app.run(host=host, port=port, debug=False)
