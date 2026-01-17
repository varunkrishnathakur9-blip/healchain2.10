# HealChain Aggregator - Verification Module
# encode–verify consistency

"""
HealChain Aggregation Verification (Module M4)
==============================================

Purpose:
---------
Implements the Encode–Verify step after BSGS recovery.

Ensures:
- Aggregated EC result is mathematically consistent
- No malformed ciphertexts or backend tampering occurred
- BSGS output corresponds EXACTLY to decrypted EC points

Security Role:
--------------
This is a mandatory integrity check before:
- Model update
- Candidate block formation
"""

from typing import List

from tinyec.ec import Point

from crypto.ec_utils import (
    G,
    point_mul,
    point_add,
)

from utils.logging import get_logger

logger = get_logger("aggregation.verifier")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def verify_recovered_aggregate(
    recovered_points: List[Point],
    submissions: List[dict],
    weights: List[int],
    keys,
) -> bool:
    """
    Verify correctness of recovered aggregate using re-encoding.

    Logic:
    ------
    1. Take recovered EC points: g^{⟨Δ′[j], y⟩}
    2. Re-encode them using pk_A and weights
    3. Compare against FE-decrypted aggregate

    This ensures:
    - BSGS result is correct
    - No tampering in ciphertext aggregation
    - No malformed miner submissions

    Parameters:
    -----------
    recovered_points : List[Point]
        Output of NDD-FE decrypt (before BSGS)

    submissions : List[dict]
        Validated miner submissions

    weights : List[int]
        Aggregation weights y_i

    keys :
        KeyManager instance (must expose pkA, skA)

    Returns:
    --------
    True if verification passes, False otherwise
    """

    logger.info("[M4] Verifying recovered aggregate consistency")

    # ------------------------------------------------------------
    # Step 1: Re-aggregate encrypted updates directly
    # ------------------------------------------------------------
    num_coords = len(recovered_points)
    recomputed = [None] * num_coords

    for sub, w in zip(submissions, weights):
        ciphertext = sub["ciphertext"]

        if len(ciphertext) != num_coords:
            logger.error("Ciphertext length mismatch during verification")
            return False

        for j, Ui_hex in enumerate(ciphertext):
            Ui = keys.parse_ciphertext_point(Ui_hex)
            term = point_mul(Ui, w)
            recomputed[j] = (
                term if recomputed[j] is None
                else point_add(recomputed[j], term)
            )

    # ------------------------------------------------------------
    # Step 2: Remove FE mask again
    # ------------------------------------------------------------
    fe_mask = point_mul(keys.pkTP, keys.skFE)

    for j in range(num_coords):
        recomputed[j] = recomputed[j] - fe_mask

    # ------------------------------------------------------------
    # Step 3: Apply designated decryptor inverse
    # ------------------------------------------------------------
    inv_skA = pow(keys.skA, -1, G.curve.field.n)

    for j in range(num_coords):
        recomputed[j] = point_mul(recomputed[j], inv_skA)

    # ------------------------------------------------------------
    # Step 4: Compare EC points
    # ------------------------------------------------------------
    for j, (p1, p2) in enumerate(zip(recovered_points, recomputed)):
        if p1 != p2:
            logger.error(
                f"[M4] Verification failed at index {j}"
            )
            return False

    logger.info("[M4] Aggregate verification successful")
    return True
