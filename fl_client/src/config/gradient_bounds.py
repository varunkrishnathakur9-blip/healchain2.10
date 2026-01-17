# Gradient Bounds and Quantization Configuration
# ===========================================
# Defines parameters for BSGS-compatible gradient quantization

MAX_GRAD_MAGNITUDE = 10_000  # Maximum absolute gradient value
GRADIENT_PRECISION = 6        # Fixed-point decimal precision
QUANTIZATION_SCALE = 10**GRADIENT_PRECISION  # Scale factor for quantization

# BSGS search bounds (signed range)
BSGS_MIN_BOUND = -MAX_GRAD_MAGNITUDE * QUANTIZATION_SCALE
BSGS_MAX_BOUND = MAX_GRAD_MAGNITUDE * QUANTIZATION_SCALE

# Validation constants
MAX_QUANTIZED_VALUE = 2**63 - 1  # int64 max for safety
