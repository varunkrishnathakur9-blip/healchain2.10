# HealChain Aggregator - NDD-FE Decryption
# decrypt logic (NO encrypt)

"""
HealChain NDD-FE – Aggregator Side
=================================

Implements:
- NDD-FE Decryption (Module M4)
- Matches miner-side encrypt_update() EXACTLY

Mathematical goal:
    E* = g^{⟨Δ′, y⟩}

Assumptions (FIXED, do not change):
- Curve: secp256r1
- Ciphertext format: ["x_hex,y_hex", ...]
- Aggregator is the designated decryptor
"""

import os
import time
from typing import Dict, List, Tuple
import concurrent.futures
import multiprocessing as mp
from tinyec import registry
from tinyec.ec import Point

from crypto.ec_utils import (
    curve,
    G,
    N,
    point_add,
    point_mul,
    point_sub,
)
from utils.logging import get_logger

logger = get_logger("crypto.ndd_fe")

# -------------------------------------------------------------------
# Hex Point Parser (matches FL client format)
# -------------------------------------------------------------------

def _is_identity(pt) -> bool:
    """
    tinyec may represent point-at-infinity as None or an Inf instance.
    """
    return pt is None or pt.__class__.__name__ == "Inf"

def parse_hex_point(serialized: str) -> Point:
    """
    Parse FL client hex format: "x_hex,y_hex"
    where x_hex and y_hex are 64-character hex strings.
    """
    try:
        x_hex, y_hex = serialized.split(",")
        x = int(x_hex, 16)  # Parse as hex
        y = int(y_hex, 16)  # Parse as hex
    except Exception as e:
        raise ValueError(f"Invalid hex EC point encoding: {serialized}") from e

    pt = Point(curve, x, y)

    # Validate point is on curve using tinyec's built-in validation
    # The Point constructor already validates this, so we just check if it's None
    if pt is None:
        raise ValueError("Point not on secp256r1 curve")

    return pt


# -------------------------------------------------------------------
# Core NDD-FE Decryption
# -------------------------------------------------------------------

def ndd_fe_decrypt(
    *,
    ciphertexts: List[List[str]],
    weights: List[int],
    pk_tp: Point,
    sk_fe: int,
    sk_agg: int,
) -> List[Point]:
    """
    Perform NDD-FE decryption and aggregation.

    Inputs:
    -------
    ciphertexts : List of miners, each miner provides:
        [
          "x_hex,y_hex",  # EC point for Δ′[0]
          "x_hex,y_hex",  # EC point for Δ′[1]
          ...
        ]

    weights : y_i aggregation weights (usually uniform 1/h)

    pk_tp : g^{s_TP}
    sk_fe : functional encryption key
    sk_agg: aggregator private key s_A

    Returns:
    --------
    List[Point] representing:
        g^{⟨Δ′[j], y⟩}   for each gradient index j
    """

    # Input validation
    if not validate_ciphertext_format(ciphertexts):
        raise ValueError("Invalid ciphertext format")
    
    if not validate_keys(pk_tp, sk_fe, sk_agg):
        raise ValueError("Invalid cryptographic keys")
    
    if len(ciphertexts) != len(weights):
        raise ValueError("Ciphertext / weight length mismatch")

    num_coords = len(ciphertexts[0])
    miner_count = len(ciphertexts)
    log_every = max(1, int(os.getenv("NDD_FE_LOG_EVERY", "50000")))
    workers = max(1, int(os.getenv("NDD_FE_WORKERS", "1")))
    chunk_size = max(1, int(os.getenv("NDD_FE_CHUNK_SIZE", "50000")))
    start = time.time()
    logger.info(
        f"[M4][NDD-FE] Start decrypt: miners={miner_count}, coords={num_coords}, "
        f"log_every={log_every}, workers={workers}, chunk_size={chunk_size}"
    )

    if workers > 1 and num_coords > chunk_size:
        return _ndd_fe_decrypt_parallel(
            ciphertexts=ciphertexts,
            weights=weights,
            pk_tp=pk_tp,
            sk_fe=sk_fe,
            sk_agg=sk_agg,
            workers=workers,
            chunk_size=chunk_size,
            start_time=start,
        )

    return _ndd_fe_decrypt_serial(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pk_tp,
        sk_fe=sk_fe,
        sk_agg=sk_agg,
        log_every=log_every,
        start_time=start,
    )


def ndd_fe_decrypt_sparse(
    *,
    sparse_submissions: List[Dict],
    weights: List[int],
    pk_tp: Point,
    sk_fe: int,
    sk_agg: int,
) -> Tuple[List[int], List[Point], int]:
    """
    Sparse NDD-FE decrypt path.

    Each submission dict must include:
      - total_size: int
      - nonzero_indices: List[int]
      - ciphertext: List[str]         # sparse encrypted values Ui[idx]
      - base_mask: str                # encrypted zero g^{r_i}
    """

    if not sparse_submissions:
        raise ValueError("No sparse submissions provided")
    if len(sparse_submissions) != len(weights):
        raise ValueError("Sparse submissions / weight length mismatch")
    if not validate_keys(pk_tp, sk_fe, sk_agg):
        raise ValueError("Invalid cryptographic keys")

    total_size = sparse_submissions[0].get("total_size")
    if not isinstance(total_size, int) or total_size <= 0:
        raise ValueError("Sparse submission total_size must be a positive integer")

    log_every = max(1, int(os.getenv("NDD_FE_LOG_EVERY", "50000")))
    start_time = time.time()

    total_sparse_values = sum(len(sub.get("ciphertext", [])) for sub in sparse_submissions)
    logger.info(
        f"[M4][NDD-FE] Start sparse decrypt: miners={len(sparse_submissions)}, "
        f"total_size={total_size}, sparse_values={total_sparse_values}, log_every={log_every}"
    )

    # Accumulate weighted base mask sum and sparse weighted gradient terms.
    weighted_base_sum = None
    weighted_terms_by_index: Dict[int, Point] = {}
    processed = 0

    for miner_idx, (sub, w) in enumerate(zip(sparse_submissions, weights), start=1):
        if w == 0:
            logger.info(f"[M4][NDD-FE] Skipping zero-weight miner {miner_idx}/{len(sparse_submissions)}")
            continue

        sub_total_size = sub.get("total_size")
        if sub_total_size != total_size:
            raise ValueError(
                f"Sparse submission total_size mismatch: expected {total_size}, got {sub_total_size}"
            )

        nonzero_indices = sub.get("nonzero_indices")
        sparse_values = sub.get("ciphertext")
        base_mask_hex = sub.get("base_mask")
        if not isinstance(nonzero_indices, list) or not isinstance(sparse_values, list):
            raise ValueError("Sparse submission must include nonzero_indices and ciphertext lists")
        if len(nonzero_indices) != len(sparse_values):
            raise ValueError("Sparse submission nonzero_indices/ciphertext length mismatch")
        if not isinstance(base_mask_hex, str):
            raise ValueError("Sparse submission base_mask is missing")

        base_mask_pt = parse_hex_point(base_mask_hex)
        weighted_base = point_mul(base_mask_pt, w)
        weighted_base_sum = weighted_base if weighted_base_sum is None else point_add(weighted_base_sum, weighted_base)

        for idx, ui_hex in zip(nonzero_indices, sparse_values):
            if not isinstance(idx, int) or idx < 0 or idx >= total_size:
                raise ValueError(f"Sparse index out of bounds: {idx}")
            ui_pt = parse_hex_point(ui_hex)
            grad_term = point_sub(ui_pt, base_mask_pt)  # removes miner-specific base mask
            weighted_term = None if _is_identity(grad_term) else point_mul(grad_term, w)
            existing = weighted_terms_by_index.get(idx)
            weighted_terms_by_index[idx] = weighted_term if existing is None else point_add(existing, weighted_term)

            processed += 1
            if processed % log_every == 0:
                logger.info(
                    f"[M4][NDD-FE] Sparse combine progress: processed={processed}/{total_sparse_values}, "
                    f"unique_indices={len(weighted_terms_by_index)}, elapsed={time.time() - start_time:.1f}s"
                )

        logger.info(
            f"[M4][NDD-FE] Sparse miner processed: {miner_idx}/{len(sparse_submissions)}, "
            f"miner_nonzero={len(nonzero_indices)}, elapsed={time.time() - start_time:.1f}s"
        )

    if weighted_base_sum is None:
        raise ValueError("Weighted base mask sum is empty; check aggregation weights")

    # Validate zero baseline decrypts to identity.
    fe_mask = point_mul(pk_tp, sk_fe)
    zero_encoded = point_sub(weighted_base_sum, fe_mask)
    inv_sk_agg = pow(sk_agg, -1, N)
    zero_decrypted = None if _is_identity(zero_encoded) else point_mul(zero_encoded, inv_sk_agg)
    if zero_decrypted is not None:
        raise ValueError(
            "Sparse decrypt baseline check failed: decrypted zero baseline is non-identity. "
            "Check baseMask/counter/task binding consistency."
        )

    # Decrypt sparse coordinates only.
    sparse_indices = sorted(weighted_terms_by_index.keys())
    recovered_points: List[Point] = []
    for done, idx in enumerate(sparse_indices, start=1):
        term = weighted_terms_by_index[idx]
        recovered_points.append(None if _is_identity(term) else point_mul(term, inv_sk_agg))
        if done % log_every == 0:
            elapsed = max(time.time() - start_time, 1e-6)
            rate = done / elapsed
            remaining = len(sparse_indices) - done
            eta = remaining / rate if rate > 0 else 0.0
            logger.info(
                f"[M4][NDD-FE] Sparse decrypt progress: {done}/{len(sparse_indices)}, "
                f"elapsed={elapsed:.1f}s, rate={rate:.1f} coords/s, eta={eta:.1f}s"
            )

    logger.info(
        f"[M4][NDD-FE] Sparse decrypt complete: "
        f"sparse_coords={len(sparse_indices)}, total_size={total_size}, "
        f"elapsed={time.time() - start_time:.2f}s"
    )
    return sparse_indices, recovered_points, total_size


def _ndd_fe_decrypt_serial(
    *,
    ciphertexts: List[List[str]],
    weights: List[int],
    pk_tp: Point,
    sk_fe: int,
    sk_agg: int,
    log_every: int,
    start_time: float,
) -> List[Point]:
    num_coords = len(ciphertexts[0])
    miner_count = len(ciphertexts)
    aggregated = [None] * num_coords

    # ------------------------------------------------------------
    # Step 1: ∏ U_i[j]^{y_i}
    # ------------------------------------------------------------
    for miner_idx, (miner_ct, w) in enumerate(zip(ciphertexts, weights), start=1):
        if len(miner_ct) != num_coords:
            raise ValueError("Inconsistent ciphertext vector length")

        for j, Ui_hex in enumerate(miner_ct):
            Ui = parse_hex_point(Ui_hex)

            term = point_mul(Ui, w)
            aggregated[j] = (
                term if aggregated[j] is None
                else point_add(aggregated[j], term)
            )
            if (j + 1) % log_every == 0:
                logger.info(
                    f"[M4][NDD-FE] Combine progress: miner={miner_idx}/{miner_count}, "
                    f"coord={j + 1}/{num_coords}, elapsed={time.time() - start_time:.1f}s"
                )
        logger.info(
            f"[M4][NDD-FE] Miner combined: {miner_idx}/{miner_count}, elapsed={time.time() - start_time:.1f}s"
        )

    # ------------------------------------------------------------
    # Step 2: Remove pk_TP^{∑ r_i y_i} using skFE
    # ------------------------------------------------------------
    fe_mask = point_mul(pk_tp, sk_fe)

    for j in range(num_coords):
        aggregated[j] = point_sub(aggregated[j], fe_mask)
        if (j + 1) % log_every == 0:
            logger.info(
                f"[M4][NDD-FE] FE-mask removal: coord={j + 1}/{num_coords}, elapsed={time.time() - start_time:.1f}s"
            )

    # ------------------------------------------------------------
    # Step 3: Designated decryptor step
    #         (pk_A^{⟨Δ′,y⟩})^{1/sk_A} = g^{⟨Δ′,y⟩}
    # ------------------------------------------------------------
    inv_sk_agg = pow(sk_agg, -1, N)
    logger.info(
        f"[M4][NDD-FE] Starting designated decryptor step: "
        f"coords={num_coords}, inv_sk_agg_ready=True"
    )

    recovered = []
    for j in range(num_coords):
        recovered.append(None if _is_identity(aggregated[j]) else point_mul(aggregated[j], inv_sk_agg))
        if (j + 1) % log_every == 0:
            done = j + 1
            elapsed = max(time.time() - start_time, 1e-6)
            rate = done / elapsed
            remaining = num_coords - done
            eta = remaining / rate if rate > 0 else 0.0
            logger.info(
                f"[M4][NDD-FE] Decrypt step: coord={done}/{num_coords}, "
                f"elapsed={elapsed:.1f}s, rate={rate:.1f} coords/s, eta={eta:.1f}s"
            )

    logger.info(
        f"[M4][NDD-FE] Complete: coords={num_coords}, total_elapsed={time.time() - start_time:.2f}s"
    )

    return recovered


def _ndd_fe_decrypt_parallel(
    *,
    ciphertexts: List[List[str]],
    weights: List[int],
    pk_tp: Point,
    sk_fe: int,
    sk_agg: int,
    workers: int,
    chunk_size: int,
    start_time: float,
) -> List[Point]:
    num_coords = len(ciphertexts[0])
    miner_count = len(ciphertexts)
    pk_tp_tuple = (pk_tp.x, pk_tp.y)
    chunks = []
    for start in range(0, num_coords, chunk_size):
        end = min(start + chunk_size, num_coords)
        chunk_ciphertexts = [miner_ct[start:end] for miner_ct in ciphertexts]
        chunks.append((start, chunk_ciphertexts))

    logger.info(
        f"[M4][NDD-FE] Parallel mode: chunks={len(chunks)}, workers={workers}, "
        f"miners={miner_count}, coords={num_coords}"
    )

    ctx = mp.get_context("spawn")
    results = {}
    completed = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as ex:
        futs = [
            ex.submit(
                _decrypt_chunk_task,
                start_idx,
                chunk_cts,
                weights,
                pk_tp_tuple,
                sk_fe,
                sk_agg,
            )
            for start_idx, chunk_cts in chunks
        ]

        for fut in concurrent.futures.as_completed(futs):
            start_idx, recovered_chunk = fut.result()
            results[start_idx] = recovered_chunk
            completed += len(recovered_chunk)
            elapsed = max(time.time() - start_time, 1e-6)
            rate = completed / elapsed
            remaining = num_coords - completed
            eta = remaining / rate if rate > 0 else 0.0
            logger.info(
                f"[M4][NDD-FE] Parallel progress: {completed}/{num_coords} "
                f"({100.0 * completed / num_coords:.2f}%), "
                f"rate={rate:.1f} coords/s, eta={eta:.1f}s"
            )

    recovered: List[Point] = []
    for start_idx, _ in chunks:
        recovered.extend(results[start_idx])

    logger.info(
        f"[M4][NDD-FE] Parallel complete: coords={num_coords}, "
        f"elapsed={time.time() - start_time:.2f}s"
    )
    return recovered


def _decrypt_chunk_task(
    start_idx: int,
    chunk_ciphertexts: List[List[str]],
    weights: List[int],
    pk_tp_tuple: tuple[int, int],
    sk_fe: int,
    sk_agg: int,
):
    # Rebuild TP point in worker.
    pk_tp_local = Point(curve, pk_tp_tuple[0], pk_tp_tuple[1])
    num_coords = len(chunk_ciphertexts[0])
    aggregated = [None] * num_coords

    for miner_ct, w in zip(chunk_ciphertexts, weights):
        for j, ui_hex in enumerate(miner_ct):
            ui = parse_hex_point(ui_hex)
            term = point_mul(ui, w)
            aggregated[j] = term if aggregated[j] is None else point_add(aggregated[j], term)

    fe_mask = point_mul(pk_tp_local, sk_fe)
    for j in range(num_coords):
        aggregated[j] = point_sub(aggregated[j], fe_mask)

    inv_sk_agg = pow(sk_agg, -1, N)
    recovered = []
    for j in range(num_coords):
        recovered.append(None if _is_identity(aggregated[j]) else point_mul(aggregated[j], inv_sk_agg))

    return start_idx, recovered


# -------------------------------------------------------------------
# Validation and Testing
# -------------------------------------------------------------------

def validate_ciphertext_format(ciphertexts: List[List[str]]) -> bool:
    """
    Validate that ciphertexts match FL client format.
    """
    if not ciphertexts:
        return False
    
    for miner_ct in ciphertexts:
        if not isinstance(miner_ct, list):
            return False
        
        for point_hex in miner_ct:
            if not isinstance(point_hex, str):
                return False
            
            try:
                parse_hex_point(point_hex)
            except ValueError:
                return False
    
    return True


def validate_keys(pk_tp: Point, sk_fe: int, sk_agg: int) -> bool:
    """
    Validate cryptographic keys.
    """
    if pk_tp is None:
        return False
    
    if sk_fe <= 0 or sk_fe >= N:
        return False
    
    if sk_agg <= 0 or sk_agg >= N:
        return False
    
    return True
