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

from typing import Any, List, Dict

from utils.logging import get_logger
from config.limits import MAX_MINERS, MAX_MODEL_DIMENSION

from crypto.ndd_fe import ndd_fe_decrypt
from crypto.bsgs import recover_vector, dequantize_vector
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
    logger.info("[M4] Performing NDD-FE decryption")

    aggregated_points: List[Point] = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    logger.info("[M4] NDD-FE decryption successful")

    # ------------------------------------------------------------
    # Step 3: BSGS recovery (signed, bounded)
    # ------------------------------------------------------------
    logger.info("[M4] Recovering integer gradients via BSGS")

    quantized_update: List[int] = recover_vector(aggregated_points)

    logger.info("[M4] BSGS recovery complete")

    # ------------------------------------------------------------
    # Step 4: Dequantization (fixed-point → float)
    # ------------------------------------------------------------
    aggregate_update: List[float] = dequantize_vector(quantized_update)

    # Validate final aggregate dimensions
    if len(aggregate_update) > MAX_MODEL_DIMENSION:
        raise ValueError(f"Aggregate vector too large: {len(aggregate_update)} > {MAX_MODEL_DIMENSION}")

    logger.info("[M4] Dequantization complete")

    return aggregate_update
