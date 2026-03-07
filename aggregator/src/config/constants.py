# HealChain Aggregator - Constants Configuration
# task states, thresholds

"""
HealChain Aggregator – Protocol Constants
========================================

Defines task states, timeouts, and consensus thresholds used by:
- main.py orchestration
- aggregation collector
- consensus (M5/M6)

IMPORTANT:
----------
- These are PROTOCOL constants, not cryptographic parameters.
- Changing them alters system behavior and must be documented.
"""
import os

# -------------------------------------------------------------------
# Task Lifecycle States
# -------------------------------------------------------------------

TASK_STATE_INITIALIZED = "INITIALIZED"
TASK_STATE_METADATA_LOADED = "METADATA_LOADED"
TASK_STATE_COLLECTING = "COLLECTING_SUBMISSIONS"
TASK_STATE_AGGREGATING = "AGGREGATING"
TASK_STATE_EVALUATED = "MODEL_EVALUATED"
TASK_STATE_CANDIDATE_BUILT = "CANDIDATE_BUILT"
TASK_STATE_VERIFYING = "VERIFYING"
TASK_STATE_PUBLISHED = "PUBLISHED"
TASK_STATE_ABORTED = "ABORTED"


# -------------------------------------------------------------------
# Participation Thresholds
# -------------------------------------------------------------------

# Minimum number of miners required to start aggregation
MIN_PARTICIPANTS = 2

# Maximum number of miners allowed (sanity bound)
MAX_PARTICIPANTS = 1_000


# -------------------------------------------------------------------
# Timeouts (seconds)
# -------------------------------------------------------------------

# Time window to wait for miner submissions (M4)
# Large local test payloads can be hundreds of MB per submission.
# Keep this configurable via env for quick tuning without code edits.
AGGREGATION_TIMEOUT = int(os.getenv("AGGREGATION_TIMEOUT", "600"))

# Time window to wait for miner verification feedback (M5)
FEEDBACK_TIMEOUT = int(os.getenv("FEEDBACK_TIMEOUT", "180"))

# Polling interval when waiting on backend
BACKEND_POLL_INTERVAL = float(os.getenv("BACKEND_POLL_INTERVAL", "1.0"))


# -------------------------------------------------------------------
# Consensus Parameters (M5)
# -------------------------------------------------------------------

# Default Byzantine fault tolerance (33%)
DEFAULT_TOLERABLE_FAULT_RATE = 0.33

# Verdict labels (used in feedback)
VERDICT_VALID = "VALID"
VERDICT_INVALID = "INVALID"


# -------------------------------------------------------------------
# Accuracy & Evaluation
# -------------------------------------------------------------------

# Minimum delta required to consider accuracy improvement meaningful
MIN_ACCURACY_DELTA = 0.0

# Accuracy bounds (sanity checks)
MIN_ACCURACY = 0.0
MAX_ACCURACY = 1.0


# -------------------------------------------------------------------
# Miscellaneous
# -------------------------------------------------------------------

# Timestamp tolerance (seconds) for backend-reported events
TIMESTAMP_TOLERANCE = 30

# Default learning rate used by aggregator if not specified
DEFAULT_LEARNING_RATE = 1.0
