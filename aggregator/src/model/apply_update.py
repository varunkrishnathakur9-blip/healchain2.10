# HealChain Aggregator - Model Update
# W_t + Δ

"""
HealChain Aggregator – Model Update Logic
========================================

Implements:
- Global model update step (Module M4)

Responsibilities:
-----------------
- Apply aggregated gradient update Δ to current global model W_t
- Return updated model W_{t+1}

NON-RESPONSIBILITIES:
---------------------
- No training
- No evaluation
- No cryptography
- No backend or blockchain logic
"""

from typing import Any, List

from utils.logging import get_logger
from config.limits import validate_aggregate_vector

logger = get_logger("model.apply_update")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def apply_model_update(
    *,
    base_model: Any,
    aggregate_update: List[float],
    learning_rate: float = 1.0,
) -> Any:
    """
    Apply aggregated gradient update to the global model.

    Update rule:
        W_{t+1} = W_t + η · Δ

    Parameters:
    -----------
    base_model : Any
        Current global model.
        Expected to expose:
            - get_weights() -> List[float]
            - set_weights(List[float])

    aggregate_update : List[float]
        Dequantized aggregated gradient vector

    learning_rate : float
        Update scaling factor (η)

    Returns:
    --------
    new_model : Any
        Updated global model
    """

    if base_model is None:
        raise ValueError("Base model is None")

    if not hasattr(base_model, "get_weights"):
        raise TypeError("Model missing get_weights()")

    if not hasattr(base_model, "set_weights"):
        raise TypeError("Model missing set_weights()")

    weights = base_model.get_weights()

    if len(weights) != len(aggregate_update):
        raise ValueError(
            "Model weights and aggregate update length mismatch"
        )

    # Validate aggregate update dimensions and bounds
    # Note: aggregate_update is already dequantized (float), but we validate
    # the underlying quantized values were within bounds during BSGS recovery
    if len(aggregate_update) > 10_000_000:  # MAX_MODEL_DIMENSION
        raise ValueError("Aggregate update exceeds maximum model dimension")

    logger.info(
        f"[M4] Applying model update | params={len(weights)}"
    )

    # ------------------------------------------------------------
    # Apply update
    # ------------------------------------------------------------
    new_weights = []
    for w, delta in zip(weights, aggregate_update):
        new_w = w + learning_rate * delta
        new_weights.append(new_w)

    # ------------------------------------------------------------
    # Update model in-place
    # ------------------------------------------------------------
    base_model.set_weights(new_weights)

    logger.info("[M4] Model update applied successfully")

    return base_model
