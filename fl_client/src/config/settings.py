import os

# === Blockchain ===
RPC_URL = os.getenv("RPC_URL")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))  # sepolia default

# === Training ===
LOCAL_EPOCHS = int(os.getenv("LOCAL_EPOCHS", "1"))
DGC_THRESHOLD = float(os.getenv("DGC_THRESHOLD", "0.9"))

# === Timing (seconds) ===
MIN_REVEAL_DEADLINE = int(os.getenv("MIN_REVEAL_DEADLINE", "600"))

# === Precision ===
SCORE_PRECISION = 10**6

# === BSGS Compatibility ===
from .gradient_bounds import (
    MAX_GRAD_MAGNITUDE,
    GRADIENT_PRECISION,
    QUANTIZATION_SCALE,
    BSGS_MIN_BOUND,
    BSGS_MAX_BOUND,
    MAX_QUANTIZED_VALUE
)
