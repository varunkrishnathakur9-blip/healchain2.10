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
from typing import List
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
    start = time.time()
    logger.info(
        f"[M4][NDD-FE] Start decrypt: miners={miner_count}, coords={num_coords}, log_every={log_every}"
    )
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
                    f"coord={j + 1}/{num_coords}, elapsed={time.time() - start:.1f}s"
                )
        logger.info(
            f"[M4][NDD-FE] Miner combined: {miner_idx}/{miner_count}, elapsed={time.time() - start:.1f}s"
        )

    # ------------------------------------------------------------
    # Step 2: Remove pk_TP^{∑ r_i y_i} using skFE
    # ------------------------------------------------------------
    fe_mask = point_mul(pk_tp, sk_fe)

    for j in range(num_coords):
        aggregated[j] = point_sub(aggregated[j], fe_mask)
        if (j + 1) % log_every == 0:
            logger.info(
                f"[M4][NDD-FE] FE-mask removal: coord={j + 1}/{num_coords}, elapsed={time.time() - start:.1f}s"
            )

    # ------------------------------------------------------------
    # Step 3: Designated decryptor step
    #         (pk_A^{⟨Δ′,y⟩})^{1/sk_A} = g^{⟨Δ′,y⟩}
    # ------------------------------------------------------------
    inv_sk_agg = pow(sk_agg, -1, N)

    recovered = []
    for j in range(num_coords):
        recovered.append(point_mul(aggregated[j], inv_sk_agg))
        if (j + 1) % log_every == 0:
            logger.info(
                f"[M4][NDD-FE] Decrypt step: coord={j + 1}/{num_coords}, elapsed={time.time() - start:.1f}s"
            )

    logger.info(
        f"[M4][NDD-FE] Complete: coords={num_coords}, total_elapsed={time.time() - start:.2f}s"
    )

    return recovered


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
