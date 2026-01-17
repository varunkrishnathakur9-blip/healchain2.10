# HealChain Aggregator - Model Evaluation
# accuracy evaluation

"""
HealChain Aggregator – Model Evaluation
======================================

Implements:
- Model accuracy evaluation (Module M4)

Responsibilities:
-----------------
- Evaluate the updated global model on a validation set
- Return a scalar accuracy value in [0, 1]

NON-RESPONSIBILITIES:
---------------------
- No training
- No aggregation
- No cryptography
- No backend or blockchain interaction
"""

from typing import Any, Callable, Optional

from utils.logging import get_logger

logger = get_logger("model.evaluate")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def evaluate_model(
    model: Any,
    *,
    evaluator: Optional[Callable[[Any], float]] = None,
) -> float:
    """
    Evaluate a model and return accuracy.

    Parameters:
    -----------
    model : Any
        Trained global model.
        Expected to be compatible with the provided evaluator.

    evaluator : Callable[[model], float], optional
        A callable that takes a model and returns accuracy.
        This allows flexible integration with:
            - PyTorch evaluation
            - NumPy evaluation
            - Custom test harness

    Returns:
    --------
    accuracy : float
        Scalar accuracy in [0.0, 1.0]

    Notes:
    ------
    - Aggregator does NOT own the validation dataset.
    - Evaluator is injected (dependency inversion).
    """

    if model is None:
        raise ValueError("Model is None; cannot evaluate")

    # ------------------------------------------------------------
    # Use injected evaluator if provided
    # ------------------------------------------------------------
    if evaluator is not None:
        acc = evaluator(model)
        _validate_accuracy(acc)
        logger.info(f"[M4] Model evaluated (custom evaluator): acc={acc:.6f}")
        return acc

    # ------------------------------------------------------------
    # Fallback: model provides its own evaluation method
    # ------------------------------------------------------------
    if hasattr(model, "evaluate") and callable(model.evaluate):
        acc = model.evaluate()
        _validate_accuracy(acc)
        logger.info(f"[M4] Model evaluated (model.evaluate): acc={acc:.6f}")
        return acc

    # ------------------------------------------------------------
    # No valid evaluation path
    # ------------------------------------------------------------
    raise RuntimeError(
        "No evaluation method available. "
        "Provide evaluator callable or model.evaluate()."
    )


# -------------------------------------------------------------------
# Internal Validation
# -------------------------------------------------------------------

def _validate_accuracy(acc: float):
    """
    Ensure returned accuracy is valid.
    """
    if not isinstance(acc, (int, float)):
        raise TypeError("Accuracy must be numeric")

    if not (0.0 <= acc <= 1.0):
        raise ValueError("Accuracy must be in range [0.0, 1.0]")
