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
    x in [BSGS_MIN_BOUND, BSGS_MAX_BOUND]
    x is a signed int64
    x represents a FIXED-POINT value (scale = 10^6)
"""

from typing import Dict, Optional, Tuple
import math
import os
import time
import concurrent.futures
import multiprocessing as mp

from tinyec.ec import Point

from crypto.ec_utils import (
    G,
    point_add,
    point_mul,
    point_neg,
)

from config.limits import (
    BSGS_MIN_BOUND,
    BSGS_MAX_BOUND,
    QUANTIZATION_SCALE,
)
from utils.logging import get_logger

logger = get_logger("crypto.bsgs")


def _is_identity(pt) -> bool:
    return pt is None or pt.__class__.__name__ == "Inf"


def _point_key(pt) -> Optional[Tuple[int, int]]:
    if _is_identity(pt):
        return None
    return (int(pt.x), int(pt.y))


class _BsgsContext:
    def __init__(self, min_bound: int, max_bound: int):
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.range_size = max_bound - min_bound
        self.m = int(math.isqrt(self.range_size)) + 1

        # Shift signed search range [MIN, MAX] to [0, RANGE].
        self.offset = point_mul(G, -self.min_bound)

        # Baby-step table: j*G -> j for j in [0, m).
        self.baby_steps: Dict[Optional[Tuple[int, int]], int] = {}
        cur = None  # identity
        for j in range(self.m):
            self.baby_steps[_point_key(cur)] = j
            cur = G if cur is None else point_add(cur, G)

        self.step_neg = point_neg(point_mul(G, self.m))

    def recover(self, point: Point) -> int:
        if _is_identity(point):
            return 0

        target = point_add(point, self.offset)
        gamma = target
        for i in range(self.m + 1):
            j = self.baby_steps.get(_point_key(gamma))
            if j is not None:
                k = i * self.m + j
                x = k + self.min_bound
                if self.min_bound <= x <= self.max_bound:
                    return x
            gamma = point_add(gamma, self.step_neg)

        raise ValueError(
            f"Discrete log not found in range [{self.min_bound}, {self.max_bound}]"
        )


_FULL_ABS_BOUND = max(abs(BSGS_MIN_BOUND), abs(BSGS_MAX_BOUND))
_DEFAULT_TIER_BOUNDS = f"1000000,10000000,100000000,1000000000,{_FULL_ABS_BOUND}"

_BSGS_CTX_BY_BOUND: Dict[int, _BsgsContext] = {}
_WORKER_CTX_BY_BOUND: Optional[Dict[int, _BsgsContext]] = None


def _tier_abs_bounds() -> list[int]:
    raw = os.getenv("BSGS_TIER_BOUNDS", _DEFAULT_TIER_BOUNDS)
    bounds = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            val = int(token)
        except ValueError:
            continue
        if val > 0:
            bounds.append(min(val, _FULL_ABS_BOUND))
    if _FULL_ABS_BOUND not in bounds:
        bounds.append(_FULL_ABS_BOUND)
    return sorted(set(bounds))


def _ctx_min_max(abs_bound: int) -> Tuple[int, int]:
    lo = max(BSGS_MIN_BOUND, -abs_bound)
    hi = min(BSGS_MAX_BOUND, abs_bound)
    return lo, hi


def _get_bsgs_ctx(abs_bound: int) -> _BsgsContext:
    ctx = _BSGS_CTX_BY_BOUND.get(abs_bound)
    if ctx is None:
        lo, hi = _ctx_min_max(abs_bound)
        ctx = _BsgsContext(lo, hi)
        _BSGS_CTX_BY_BOUND[abs_bound] = ctx
    return ctx


def recover_discrete_log(point: Point) -> int:
    """
    Recover signed integer x such that point == x*G.
    """
    last_err = None
    for abs_bound in _tier_abs_bounds():
        try:
            return _get_bsgs_ctx(abs_bound).recover(point)
        except ValueError as e:
            last_err = e
            continue
    if last_err is not None:
        raise last_err
    raise ValueError("BSGS recovery failed")


def recover_vector(points: list[Point]) -> list[int]:
    """
    Recover a vector of signed integers from EC points.
    """
    total = len(points)
    log_every = max(1, int(os.getenv("BSGS_LOG_EVERY", "200")))
    workers = max(1, int(os.getenv("BSGS_WORKERS", "1")))
    chunk_size = max(1, int(os.getenv("BSGS_CHUNK_SIZE", "5000")))
    cache_limit = max(0, int(os.getenv("BSGS_CACHE_LIMIT", "300000")))
    start = time.time()

    logger.info(
        f"[M4][BSGS] Start recovery: coords={total}, log_every={log_every}, "
        f"workers={workers}, chunk_size={chunk_size}, cache_limit={cache_limit}, "
        f"range=[{BSGS_MIN_BOUND}, {BSGS_MAX_BOUND}]"
    )

    if workers > 1 and total > chunk_size:
        recovered = _recover_vector_parallel(
            points=points,
            workers=workers,
            chunk_size=chunk_size,
            cache_limit=cache_limit,
            start_time=start,
        )
    else:
        recovered = _recover_vector_serial(
            points,
            log_every=log_every,
            cache_limit=cache_limit,
            start_time=start,
        )

    logger.info(f"[M4][BSGS] Complete: coords={total}, elapsed={time.time() - start:.2f}s")
    return recovered


def dequantize_vector(q_values: list[int]) -> list[float]:
    """
    Convert quantized int64 values back to float.
    """
    return [q / QUANTIZATION_SCALE for q in q_values]


def _recover_vector_serial(
    points: list[Point],
    *,
    log_every: int,
    cache_limit: int,
    start_time: float,
) -> list[int]:
    total = len(points)
    tier_bounds = _tier_abs_bounds()
    cache: Dict[Optional[Tuple[int, int]], int] = {}
    recovered = []

    for idx, pt in enumerate(points):
        try:
            key = _point_key(pt)
            cached = cache.get(key)
            if cached is not None:
                val = cached
            else:
                val = None
                for abs_bound in tier_bounds:
                    try:
                        val = _get_bsgs_ctx(abs_bound).recover(pt)
                        break
                    except ValueError:
                        continue
                if val is None:
                    raise ValueError("Discrete log not found in configured BSGS tiers")
                if cache_limit > 0 and len(cache) < cache_limit:
                    cache[key] = val
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
    cache_limit: int,
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
    try:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=workers,
            mp_context=ctx,
            initializer=_init_bsgs_worker,
        ) as executor:
            futures = [
                executor.submit(_recover_chunk, start, chunk, cache_limit)
                for start, chunk in chunks
            ]
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
    except Exception as e:
        logger.warning(
            f"[M4][BSGS] Parallel recovery unavailable ({e}); "
            "falling back to serial path"
        )
        return _recover_vector_serial(
            points,
            log_every=max(1, int(os.getenv("BSGS_LOG_EVERY", "200"))),
            cache_limit=cache_limit,
            start_time=start_time,
        )

    recovered: list[int] = []
    for start_idx, _ in chunks:
        recovered.extend(results[start_idx])
    return recovered


def _init_bsgs_worker():
    global _WORKER_CTX_BY_BOUND
    _WORKER_CTX_BY_BOUND = {}


def _recover_chunk(start_idx: int, chunk: list[Point], cache_limit: int):
    global _WORKER_CTX_BY_BOUND
    ctx_map = _WORKER_CTX_BY_BOUND
    if ctx_map is None:
        ctx_map = {}
        _WORKER_CTX_BY_BOUND = ctx_map
    tier_bounds = _tier_abs_bounds()
    cache: Dict[Optional[Tuple[int, int]], int] = {}
    vals = []
    for rel_idx, pt in enumerate(chunk):
        try:
            key = _point_key(pt)
            cached = cache.get(key)
            if cached is not None:
                vals.append(cached)
                continue

            val = None
            for abs_bound in tier_bounds:
                try:
                    tier_ctx = ctx_map.get(abs_bound)
                    if tier_ctx is None:
                        lo, hi = _ctx_min_max(abs_bound)
                        tier_ctx = _BsgsContext(lo, hi)
                        ctx_map[abs_bound] = tier_ctx
                    val = tier_ctx.recover(pt)
                    break
                except ValueError:
                    continue
            if val is None:
                raise ValueError("Discrete log not found in configured BSGS tiers")
            vals.append(val)
            if cache_limit > 0 and len(cache) < cache_limit:
                cache[key] = val
        except Exception as e:
            raise ValueError(f"BSGS failed at index {start_idx + rel_idx}") from e
    return start_idx, vals
