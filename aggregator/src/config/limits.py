# HealChain Aggregator - Limits Configuration
# BSGS bounds, DGC limits

"""
HealChain Aggregator – Numeric & Cryptographic Limits
====================================================

Defines all hard bounds and limits used across:
- Quantization / dequantization
- BSGS discrete log recovery
- Secure aggregation sanity checks

IMPORTANT:
----------
- These limits MUST match the FL-client configuration exactly.
- Do NOT modify after protocol freeze.
"""

# -------------------------------------------------------------------
# Gradient Quantization (FIXED-POINT)
# -------------------------------------------------------------------

# Original (float) gradient clipping bound (FL-client)
MAX_GRAD = 10_000

# Fixed-point precision (decimal places)
GRADIENT_PRECISION = 6

# Fixed-point scale factor
# float_value * QUANTIZATION_SCALE -> int64
QUANTIZATION_SCALE = 1_000_000  # 10^6

# -------------------------------------------------------------------
# Quantized Integer Bounds (Signed)
# -------------------------------------------------------------------

# Derived bounds after quantization:
# MAX_GRAD * QUANTIZATION_SCALE
BSGS_MIN_BOUND = -10_000_000_000
BSGS_MAX_BOUND =  10_000_000_000

# Explicit data type guarantee
BSGS_INT_TYPE = "int64"

# -------------------------------------------------------------------
# BSGS Search Parameters
# -------------------------------------------------------------------

# Conservative absolute bound used for BSGS
BSGS_ABS_BOUND = BSGS_MAX_BOUND

# Safety margin (can be used to slightly over-provision search)
BSGS_SAFETY_MARGIN = 0

# Effective search bound
BSGS_EFFECTIVE_BOUND = BSGS_ABS_BOUND + BSGS_SAFETY_MARGIN

# -------------------------------------------------------------------
# Aggregation Limits
# -------------------------------------------------------------------

# Maximum number of miners allowed in one aggregation round
MAX_MINERS = 1_000

# Maximum supported model dimensionality (sanity bound)
MAX_MODEL_DIMENSION = 10_000_000

# -------------------------------------------------------------------
# Validation Helpers
# -------------------------------------------------------------------

def validate_quantized_value(x: int):
    """
    Validate a single quantized gradient value.
    """
    if not isinstance(x, int):
        raise TypeError("Quantized gradient must be int")

    if not (BSGS_MIN_BOUND <= x <= BSGS_MAX_BOUND):
        raise ValueError(
            f"Quantized gradient {x} out of bounds "
            f"[{BSGS_MIN_BOUND}, {BSGS_MAX_BOUND}]"
        )


def validate_aggregate_vector(vec: list[int]):
    """
    Validate an entire aggregated quantized vector.
    """
    if len(vec) > MAX_MODEL_DIMENSION:
        raise ValueError("Aggregate vector exceeds max dimension")

    for x in vec:
        validate_quantized_value(x)
