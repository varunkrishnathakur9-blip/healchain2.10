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
import os
import time
import concurrent.futures
import multiprocessing as mp

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
from utils.logging import get_logger

logger = get_logger("crypto.bsgs")


# -------------------------------------------------------------------
# Signed BSGS Implementation
# -------------------------------------------------------------------

def _is_identity(pt) -> bool:
    return pt is None or pt.__class__.__name__ == "Inf"

def recover_discrete_log(point: Point) -> int:
    """
    Recover signed integer x such that:
        point == x * G
    with x in [BSGS_MIN_BOUND, BSGS_MAX_BOUND]
    """

    if _is_identity(point):
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
        key = "identity" if _is_identity(cur) else serialize_point(cur)
        baby_steps[key] = j
        cur = G if cur is None else point_add(cur, G)

    # ------------------------------------------------------------
    # Giant steps: target - i·(m·G)
    # ------------------------------------------------------------
    step = point_mul(G, m)
    step_neg = point_neg(step)

    gamma = target

    for i in range(m + 1):
        key = "identity" if _is_identity(gamma) else serialize_point(gamma)
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
    total = len(points)
    log_every = max(1, int(os.getenv("BSGS_LOG_EVERY", "200")))
    workers = max(1, int(os.getenv("BSGS_WORKERS", "1")))
    chunk_size = max(1, int(os.getenv("BSGS_CHUNK_SIZE", "5000")))
    start = time.time()

    logger.info(
        f"[M4][BSGS] Start recovery: coords={total}, log_every={log_every}, "
        f"workers={workers}, chunk_size={chunk_size}, "
        f"range=[{BSGS_MIN_BOUND}, {BSGS_MAX_BOUND}]"
    )

    # Parallel mode (opt-in via BSGS_WORKERS>1).
    if workers > 1 and total > chunk_size:
        return _recover_vector_parallel(
            points=points,
            workers=workers,
            chunk_size=chunk_size,
            start_time=start,
        )

    recovered = _recover_vector_serial(points, log_every=log_every, start_time=start)
    logger.info(f"[M4][BSGS] Complete: coords={total}, elapsed={time.time() - start:.2f}s")
    return recovered


def dequantize_vector(q_values: list[int]) -> list[float]:
    """
    Convert quantized int64 values back to float.

    float = q / SCALE
    """
    return [q / QUANTIZATION_SCALE for q in q_values]


def _recover_vector_serial(points: list[Point], *, log_every: int, start_time: float) -> list[int]:
    total = len(points)
    recovered = []
    for idx, pt in enumerate(points):
        try:
            val = recover_discrete_log(pt)
            recovered.append(val)
            done = idx + 1
            if done % log_every == 0 or done == total:
                elapsed = max(time.time() - start_time, 1e-6)
                rate = done / elapsed
                remaining = total - done
                eta = remaining / rate if rate > 0 else 0.0
                logger.info(
                    f"[M4][BSGS] Progress: {done}/{total} "
                    f"({100.0 * done / total:.2f}%), "
                    f"rate={rate:.2f} coords/s, eta={eta:.1f}s"
                )
        except Exception as e:
            raise ValueError(f"BSGS failed at index {idx}") from e
    return recovered


def _recover_vector_parallel(
    *,
    points: list[Point],
    workers: int,
    chunk_size: int,
    start_time: float,
) -> list[int]:
    total = len(points)
    chunks = []
    for start in range(0, total, chunk_size):
        end = min(start + chunk_size, total)
        chunks.append((start, points[start:end]))

    logger.info(f"[M4][BSGS] Parallel mode: {len(chunks)} chunks across {workers} workers")

    results: Dict[int, list[int]] = {}
    completed = 0
    ctx = mp.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
        futures = [executor.submit(_recover_chunk, start, chunk) for start, chunk in chunks]
        for fut in concurrent.futures.as_completed(futures):
            start_idx, vals = fut.result()
            results[start_idx] = vals
            completed += len(vals)
            elapsed = max(time.time() - start_time, 1e-6)
            rate = completed / elapsed
            remaining = total - completed
            eta = remaining / rate if rate > 0 else 0.0
            logger.info(
                f"[M4][BSGS] Parallel progress: {completed}/{total} "
                f"({100.0 * completed / total:.2f}%), rate={rate:.2f} coords/s, eta={eta:.1f}s"
            )

    recovered: list[int] = []
    for start_idx, _ in chunks:
        recovered.extend(results[start_idx])
    return recovered


def _recover_chunk(start_idx: int, chunk: list[Point]):
    vals = []
    for rel_idx, pt in enumerate(chunk):
        try:
            vals.append(recover_discrete_log(pt))
        except Exception as e:
            raise ValueError(f"BSGS failed at index {start_idx + rel_idx}") from e
    return start_idx, vals
