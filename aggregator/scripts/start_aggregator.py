# HealChain Aggregator - Startup Script
# Main startup script for the aggregator

"""
HealChain Aggregator – Startup Script
====================================

Entry point for running the HealChain Aggregator.

Responsibilities:
-----------------
- Load environment variables
- Initialize logging
- Validate required configuration
- Launch the task-scoped aggregator

NON-RESPONSIBILITIES:
---------------------
- No cryptography
- No backend logic
- No protocol decisions
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

from utils.logging import setup_logging
from main import main


# -------------------------------------------------------------------
# Environment Validation
# -------------------------------------------------------------------

REQUIRED_ENV_VARS = [
    "TASK_ID",
    "BACKEND_URL",
    "AGGREGATOR_SK",
    "AGGREGATOR_PK",
    "TP_PUBLIC_KEY",
    "FE_FUNCTION_KEY",
]


def _validate_env():
    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


# -------------------------------------------------------------------
# Main Entry
# -------------------------------------------------------------------

def start():
    """
    Validate environment and start aggregator.
    """
    setup_logging()

    _validate_env()

    print("==========================================")
    print(" HealChain Aggregator Starting")
    print("==========================================")
    print(f"TASK_ID       : {os.getenv('TASK_ID')}")
    print(f"BACKEND_URL   : {os.getenv('BACKEND_URL')}")
    print("==========================================")

    main()


if __name__ == "__main__":
    start()
