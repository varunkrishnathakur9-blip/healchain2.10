# HealChain Aggregator - Model Artifact
# model storage + hashing

"""
HealChain Aggregator – Model Artifact Handling
=============================================

Implements:
- Model artifact serialization
- Deterministic hashing
- Artifact publishing (off-chain reference)

Used in:
- Module M4: Candidate block formation

NON-RESPONSIBILITIES:
---------------------
- No backend communication
- No blockchain interaction
- No cryptographic aggregation
"""

import os
import json
import hashlib
from typing import Any, Tuple

from utils.logging import get_logger

logger = get_logger("model.artifact")


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

ARTIFACT_DIR = os.getenv("MODEL_ARTIFACT_DIR", "./artifacts")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def publish_model_artifact(
    model: Any,
    *,
    task_id: str,
    round_no: int,
) -> Tuple[str, str]:
    """
    Serialize model, store artifact, and return (link, hash).

    Parameters:
    -----------
    model : Any
        Trained global model.
        Must expose:
            - get_weights() -> list[float]

    task_id : str
        HealChain task identifier

    round_no : int
        Current FL round number

    Returns:
    --------
    model_link : str
        Off-chain reference (path or URI)

    model_hash : str
        SHA-256 hash of serialized model
    """

    if not hasattr(model, "get_weights"):
        raise TypeError("Model missing get_weights()")

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    artifact = _serialize_model(model)

    artifact_bytes = json.dumps(
        artifact,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    model_hash = hashlib.sha256(artifact_bytes).hexdigest()

    filename = f"{task_id}_round{round_no}.json"
    filepath = os.path.join(ARTIFACT_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(artifact_bytes)

    logger.info(
        f"[M4] Model artifact published | "
        f"path={filepath}, hash={model_hash[:12]}..."
    )

    # For now, model_link is a filesystem path.
    # This can later be replaced with IPFS / S3 / DB ref.
    return filepath, model_hash


# -------------------------------------------------------------------
# Internal Helpers
# -------------------------------------------------------------------

def _serialize_model(model: Any) -> dict:
    """
    Convert model into a deterministic, JSON-serializable dict.

    This ensures:
    - Hash stability
    - Auditability
    """

    weights = model.get_weights()

    if not isinstance(weights, list):
        raise TypeError("Model weights must be a list")

    return {
        "weights": weights,
        "num_parameters": len(weights),
    }
