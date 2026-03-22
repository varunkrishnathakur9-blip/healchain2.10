# HealChain Aggregator - Core Aggregation
# secure aggregation core (M4)


"""
HealChain Secure Aggregation Core (Module M4)
=============================================

Responsibilities:
-----------------
- Perform NDD-FE aggregation + decryption
- Recover quantized integer gradients using signed BSGS
- Dequantize gradients back to float space
- Return aggregate update vector (ready for model apply)

STRICT NON-RESPONSIBILITIES:
----------------------------
- No model updates
- No backend interaction
- No consensus logic
- No encryption
"""

import time
from typing import Any, List, Dict

from utils.logging import get_logger
from config.limits import MAX_MINERS, MAX_MODEL_DIMENSION

from crypto.ndd_fe import ndd_fe_decrypt, ndd_fe_decrypt_sparse
from crypto.bsgs import recover_vector, dequantize_vector
from crypto.ec_utils import G, point_mul
from tinyec.ec import Point

logger = get_logger("aggregation.aggregator")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def secure_aggregate(
    *,
    submissions: List[Dict],
    skFE: int,
    skA: int,
    pkTP: Point,
    weights: List[int],
) -> List[float]:
    """
    Perform full secure aggregation pipeline:

        encrypted Ui
          → NDD-FE decrypt
          → EC points g^{⟨Δ′,y⟩}
          → signed BSGS
          → dequantized float update

    Parameters:
    -----------
    submissions : list of validated miner submissions
        Each submission must contain:
            {
              "ciphertext": [ "x_hex,y_hex", ... ],
              "miner_pk": "...",
              ...
            }

    skFE : functional encryption key
    skA  : aggregator private key
    pkTP : task publisher public key (EC Point)
    weights : aggregation weights y_i

    Returns:
    --------
    aggregate_update : List[float]
        Dequantized aggregated gradient vector
    """

    if not submissions:
        raise ValueError("No submissions provided for aggregation")

    if len(submissions) > MAX_MINERS:
        raise ValueError(f"Too many submissions: {len(submissions)} > {MAX_MINERS}")

    logger.info(f"[M4] Starting secure aggregation for {len(submissions)} miners")

    formats = {sub.get("format", "dense") for sub in submissions}
    if len(formats) != 1:
        raise ValueError(f"Mixed submission formats are not allowed: {formats}")
    submission_format = formats.pop()

    if submission_format == "sparse":
        aggregate_update = _secure_aggregate_sparse(
            submissions=submissions,
            skA=skA,
            weights=weights,
        )
    elif submission_format == "dense":
        aggregate_update = _secure_aggregate_dense(
            submissions=submissions,
            skFE=skFE,
            skA=skA,
            pkTP=pkTP,
            weights=weights,
        )
    else:
        raise ValueError(f"Unsupported submission format: {submission_format}")

    # Validate final aggregate dimensions
    if len(aggregate_update) > MAX_MODEL_DIMENSION:
        raise ValueError(
            f"Aggregate vector too large: {len(aggregate_update)} > {MAX_MODEL_DIMENSION} "
            "(configure MAX_MODEL_DIMENSION in aggregator/.env if this task is expected)"
        )

    return aggregate_update


def _secure_aggregate_dense(
    *,
    submissions: List[Dict],
    skFE: int,
    skA: int,
    pkTP: Point,
    weights: List[int],
) -> List[float]:
    weight_sum = max(1, sum(abs(int(w)) for w in weights))
    # ------------------------------------------------------------
    # Step 1: Extract ciphertext vectors
    # ------------------------------------------------------------
    ciphertexts = []
    for idx, sub in enumerate(submissions):
        if "ciphertext" not in sub:
            raise ValueError(f"Submission {idx} missing ciphertext")
        ciphertexts.append(sub["ciphertext"])

    # ------------------------------------------------------------
    # Step 2: NDD-FE decryption
    #         Output: EC points g^{⟨Δ′[j], y⟩}
    # ------------------------------------------------------------
    logger.info("[M4] Performing NDD-FE decryption (dense)")
    t_ndd = time.time()

    aggregated_points: List[Point] = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    logger.info(
        f"[M4] NDD-FE decryption successful "
        f"(coords={len(aggregated_points)}, elapsed={time.time() - t_ndd:.2f}s)"
    )

    # ------------------------------------------------------------
    # Step 3: BSGS recovery (signed, bounded)
    # ------------------------------------------------------------
    logger.info("[M4] Recovering integer gradients via BSGS (dense)")
    t_bsgs = time.time()

    quantized_update: List[int] = recover_vector(aggregated_points, weight_sum=weight_sum)

    logger.info(
        f"[M4] BSGS recovery complete "
        f"(coords={len(quantized_update)}, elapsed={time.time() - t_bsgs:.2f}s)"
    )

    # ------------------------------------------------------------
    # Step 4: Encode-verify check (Algorithm 4)
    # ------------------------------------------------------------
    _verify_recovered_points(quantized_update, aggregated_points)

    # ------------------------------------------------------------
    # Step 5: Dequantization (fixed-point → float)
    # ------------------------------------------------------------
    t_deq = time.time()
    aggregate_update: List[float] = dequantize_vector(quantized_update)
    logger.info(
        f"[M4] Dequantization complete "
        f"(coords={len(aggregate_update)}, elapsed={time.time() - t_deq:.2f}s)"
    )
    return aggregate_update


def _secure_aggregate_sparse(
    *,
    submissions: List[Dict],
    skA: int,
    weights: List[int],
) -> List[float]:
    weight_sum = max(1, sum(abs(int(w)) for w in weights))
    sparse_submissions = []
    for idx, sub in enumerate(submissions):
        missing = [
            k
            for k in ("protocol_version", "ctr", "total_size", "nonzero_indices", "base_mask", "ciphertext")
            if k not in sub
        ]
        if missing:
            raise ValueError(f"Sparse submission {idx} missing fields: {missing}")
        sparse_submissions.append(
            {
                "protocol_version": sub["protocol_version"],
                "ctr": sub["ctr"],
                "total_size": sub["total_size"],
                "nonzero_indices": sub["nonzero_indices"],
                "base_mask": sub["base_mask"],
                "ciphertext": sub["ciphertext"],
            }
        )

    ctr_values = {sub["ctr"] for sub in sparse_submissions}
    if len(ctr_values) != 1:
        raise ValueError(f"Sparse submission ctr mismatch across miners: {sorted(ctr_values)}")
    ctr = next(iter(ctr_values))

    # ------------------------------------------------------------
    # Step 2: NDD-FE decryption (sparse)
    # ------------------------------------------------------------
    logger.info("[M4] Performing NDD-FE decryption (sparse)")
    t_ndd = time.time()
    sparse_indices, sparse_points, total_size = ndd_fe_decrypt_sparse(
        sparse_submissions=sparse_submissions,
        weights=weights,
        sk_agg=skA,
        ctr=ctr,
    )
    logger.info(
        f"[M4] NDD-FE sparse decryption successful "
        f"(sparse_coords={len(sparse_points)}, total_size={total_size}, "
        f"elapsed={time.time() - t_ndd:.2f}s)"
    )

    # ------------------------------------------------------------
    # Step 3: BSGS recovery on sparse coordinates
    # ------------------------------------------------------------
    logger.info("[M4] Recovering integer gradients via BSGS (sparse)")
    t_bsgs = time.time()
    quantized_sparse: List[int] = recover_vector(sparse_points, weight_sum=weight_sum)
    logger.info(
        f"[M4] Sparse BSGS recovery complete "
        f"(sparse_coords={len(quantized_sparse)}, elapsed={time.time() - t_bsgs:.2f}s)"
    )

    # ------------------------------------------------------------
    # Step 4: Encode-verify check (Algorithm 4) on sparse coordinates
    # ------------------------------------------------------------
    _verify_recovered_points(quantized_sparse, sparse_points)

    # ------------------------------------------------------------
    # Step 5: Reconstruct dense quantized vector and dequantize
    # ------------------------------------------------------------
    quantized_dense = [0] * total_size
    for idx, val in zip(sparse_indices, quantized_sparse):
        quantized_dense[idx] = val

    t_deq = time.time()
    aggregate_update: List[float] = dequantize_vector(quantized_dense)
    logger.info(
        f"[M4] Sparse dequantization complete "
        f"(coords={len(aggregate_update)}, elapsed={time.time() - t_deq:.2f}s)"
    )
    return aggregate_update


def _verify_recovered_points(quantized_values: List[int], decrypted_points: List[Point]) -> None:
    """
    Algorithm 4 EncodeAggregateUnderFE consistency check:
      recovered integer -> re-encode point == decrypted point.
    """
    if len(quantized_values) != len(decrypted_points):
        raise ValueError("Encode-verify failed: length mismatch")

    for idx, (val, pt) in enumerate(zip(quantized_values, decrypted_points)):
        expected = None if val == 0 else point_mul(G, val)
        actual = None if (pt is None or pt.__class__.__name__ == "Inf") else pt
        if expected != actual:
            raise ValueError(f"Encode-verify failed at index {idx}")
