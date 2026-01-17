# HealChain Aggregator - BSGS Algorithm
# bounded discrete log recovery

"""
HealChain BSGS (Baby-Step Giant-Step)
====================================

Purpose:
---------
Recover signed, bounded integers x from EC points of the form:

    P = g^x   (secp256r1)

where:
    x ∈ [BSGS_MIN_BOUND, BSGS_MAX_BOUND]
    x is a signed int64
    x represents a FIXED-POINT value (scale = 10^6)

This module is used ONLY by the Aggregator (Module M4).

Security & Correctness:
-----------------------
- Deterministic
- Bounded
- Signed recovery
- Guaranteed termination within configured bounds
"""

from typing import Dict
import math

from tinyec.ec import Point

from crypto.ec_utils import (
    curve,
    G,
    N,
    point_add,
    point_mul,
    point_neg,
    serialize_point,
)

# -------------------------------------------------------------------
# BSGS Configuration (MUST match FL-client)
# -------------------------------------------------------------------

# Import from centralized configuration for single source of truth
from config.limits import (
    BSGS_MIN_BOUND,
    BSGS_MAX_BOUND,
    QUANTIZATION_SCALE,
    BSGS_EFFECTIVE_BOUND,
)


# -------------------------------------------------------------------
# Signed BSGS Implementation
# -------------------------------------------------------------------

def recover_discrete_log(point: Point) -> int:
    """
    Recover signed integer x such that:
        point == x * G
    with x in [BSGS_MIN_BOUND, BSGS_MAX_BOUND]
    """

    if point is None:
        return 0  # identity = 0·G

    MIN = BSGS_MIN_BOUND
    MAX = BSGS_MAX_BOUND
    RANGE = MAX - MIN

    # Transform signed domain to non-negative
    offset = point_mul(G, -MIN)
    target = point_add(point, offset)

    m = int(math.isqrt(RANGE)) + 1

    # ------------------------------------------------------------
    # Baby steps: j·G
    # ------------------------------------------------------------
    baby_steps: Dict[str, int] = {}
    cur = None  # identity

    for j in range(m):
        key = "identity" if cur is None else serialize_point(cur)
        baby_steps[key] = j
        cur = G if cur is None else point_add(cur, G)

    # ------------------------------------------------------------
    # Giant steps: target - i·(m·G)
    # ------------------------------------------------------------
    step = point_mul(G, m)
    step_neg = point_neg(step)

    gamma = target

    for i in range(m + 1):
        key = "identity" if gamma is None else serialize_point(gamma)
        if key in baby_steps:
            k = i * m + baby_steps[key]
            x = k + MIN
            if MIN <= x <= MAX:
                return x

        gamma = point_add(gamma, step_neg)

    raise ValueError(
        f"Discrete log not found in range [{MIN}, {MAX}]"
    )


    # ------------------------------------------------------------
    # Giant steps: compute P * g^(-i*m)
    # ------------------------------------------------------------

    # Compute factor = m * G
    factor = point_mul(G, m)
    factor_neg = point_neg(factor)

    gamma = point

    for i in range(m + 1):
        # Check if gamma matches any baby step
        if gamma is None:
            gamma_key = "identity"
        else:
            gamma_key = serialize_point(gamma)
        
        if gamma_key in baby_steps:
            # Found: x = i*m + baby_steps[gamma_key]
            x = i * m + baby_steps[gamma_key]
            
            # Adjust for negative range
            if x > max_x:
                # Try negative equivalent
                x_neg = x - N
                if min_x <= x_neg <= max_x:
                    return x_neg
            
            if min_x <= x <= max_x:
                return x

        # Next giant step
        gamma = point_add(gamma, factor_neg)

    raise ValueError(
        f"Discrete log not found in range "
        f"[{BSGS_MIN_BOUND}, {BSGS_MAX_BOUND}]"
    )


# -------------------------------------------------------------------
# Vector Recovery Helpers
# -------------------------------------------------------------------

def recover_vector(points: list[Point]) -> list[int]:
    """
    Recover a vector of signed integers from EC points.

    Input:
        points = [g^x1, g^x2, ..., g^xn]

    Output:
        [x1, x2, ..., xn]  (int64, quantized)
    """
    recovered = []
    for idx, pt in enumerate(points):
        try:
            val = recover_discrete_log(pt)
            recovered.append(val)
        except Exception as e:
            raise ValueError(
                f"BSGS failed at index {idx}"
            ) from e
    return recovered


def dequantize_vector(q_values: list[int]) -> list[float]:
    """
    Convert quantized int64 values back to float.

    float = q / SCALE
    """
    return [q / QUANTIZATION_SCALE for q in q_values]
