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
import re
from typing import Any, Tuple
import requests

from utils.logging import get_logger

logger = get_logger("model.artifact")


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

ARTIFACT_DIR = os.getenv("MODEL_ARTIFACT_DIR", "./artifacts")


def _normalize_ipfs_api_base(raw: str) -> str:
    """
    Normalize IPFS Desktop / Kubo API address formats into HTTP base URL.

    Supported inputs:
    - http://127.0.0.1:5001
    - 127.0.0.1:5001
    - /ip4/127.0.0.1/tcp/5003
    """
    token = (raw or "").strip()
    if not token:
        return "http://localhost:5001"

    if token.startswith("http://") or token.startswith("https://"):
        return token.rstrip("/")

    m = re.match(r"^/ip4/([^/]+)/tcp/(\d+)$", token)
    if m:
        host, port = m.groups()
        return f"http://{host}:{port}"

    if ":" in token and "/" not in token:
        return f"http://{token}".rstrip("/")

    return token.rstrip("/")


def _upload_json_to_ipfs(*, filename: str, payload: bytes) -> str:
    api_base = _normalize_ipfs_api_base(
        os.getenv("MODEL_ARTIFACT_IPFS_API_URL", "http://localhost:5001")
    )
    add_url = f"{api_base}/api/v0/add?pin=true"
    files = {"file": (filename, payload, "application/json")}
    resp = requests.post(add_url, files=files, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    cid = data.get("Hash")
    if not cid:
        raise RuntimeError(f"Unexpected IPFS add response: {data}")
    gateway = os.getenv("MODEL_ARTIFACT_IPFS_GATEWAY_URL", "http://127.0.0.1:8080/ipfs").rstrip("/")
    if gateway.endswith("/ipfs"):
        return f"{gateway}/{cid}"
    return f"{gateway}/ipfs/{cid}"


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

    use_ipfs = os.getenv("MODEL_ARTIFACT_USE_IPFS", "0").strip().lower() in {"1", "true", "yes", "on"}
    model_link = filepath
    if use_ipfs:
        model_link = _upload_json_to_ipfs(filename=filename, payload=artifact_bytes)

    logger.info(
        f"[M4] Model artifact published | "
        f"path={filepath}, link={model_link}, hash={model_hash[:12]}..."
    )

    return model_link, model_hash


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
