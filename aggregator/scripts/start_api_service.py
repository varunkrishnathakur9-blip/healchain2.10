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

# Load environment variables from .env file
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT_DIR, ".env")

if os.path.exists(ENV_FILE):
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

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
