# HealChain Aggregator - Candidate Block
# candidate block builder (M4)

"""
HealChain Aggregator – Candidate Block Builder
==============================================

Implements:
- Candidate block construction (Module M4)

Responsibilities:
-----------------
- Deterministically build a candidate block payload
- Canonicalize fields for hashing and signing
- Include all miner score commitments
- Bind model artifact, accuracy, and participants

NON-RESPONSIBILITIES:
---------------------
- No cryptographic verification
- No consensus voting
- No backend publishing
- No smart contract interaction
"""

import time
import hashlib
from typing import Any, Dict, List

from utils.logging import get_logger
from utils.serialization import canonical_candidate_block
from crypto.ec_utils import serialize_point

logger = get_logger("consensus.candidate")


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_block_bytes(block: Dict) -> bytes:
    """
    Deterministic byte encoding of candidate block.

    IMPORTANT:
    - Order of fields MUST be stable
    - Lists MUST already be ordered
    """

    def _stringify(value: Any) -> str:
        if hasattr(value, "x") and hasattr(value, "y"):
            return serialize_point(value)
        return str(value)

    fields = [
        _stringify(block["task_id"]),
        _stringify(block["round"]),
        _stringify(block["model_hash"]),
        _stringify(block["model_link"]),
        f"{float(block['accuracy']):.8f}",
        ",".join(_stringify(v) for v in block["participants"]),
        ",".join(_stringify(v) for v in block["score_commits"]),
        _stringify(block["aggregator_pk"]),
        _stringify(block["timestamp"]),
    ]

    return "|".join(fields).encode("utf-8")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def build_candidate_block(
    *,
    task_id: str,
    round_no: int = 0,
    model_hash: str,
    model_link: str,
    accuracy: float,
    submissions: List[Dict],
    aggregator_pk: Any,
) -> Dict:
    """
    Build a deterministic candidate block.

    Parameters:
    -----------
    task_id : str
        HealChain task identifier

    model_hash : str
        Hash of trained global model

    model_link : str
        Off-chain model artifact link

    accuracy : float
        Evaluated model accuracy

    submissions : List[Dict]
        Validated miner submissions.
        Each submission must contain:
            {
              "miner_pk": str,
              "score_commit": str,
              ...
            }

    aggregator_pk : Any
        Aggregator public key (string or EC Point)

    Returns:
    --------
    candidate_block : Dict
        Unsigned candidate block payload
    """

    logger.info("[M4] Building candidate block")

    # ------------------------------------------------------------
    # Extract miner data (deterministic ordering)
    # ------------------------------------------------------------
    participants = []
    score_commits = []

    for sub in submissions:
        if "miner_pk" not in sub or "score_commit" not in sub:
            raise ValueError("Submission missing miner_pk or score_commit")

        participants.append(sub["miner_pk"])
        score_commits.append(sub["score_commit"])

    # Enforce deterministic ordering
    combined = list(zip(participants, score_commits))
    combined.sort(key=lambda x: x[0])  # sort by miner_pk

    participants = [p for p, _ in combined]
    score_commits = [c for _, c in combined]

    # ------------------------------------------------------------
    # Assemble candidate block
    # ------------------------------------------------------------
    aggregator_pk_value = (
        serialize_point(aggregator_pk)
        if hasattr(aggregator_pk, "x") and hasattr(aggregator_pk, "y")
        else str(aggregator_pk)
    )

    block = {
        "task_id": task_id,
        "round": int(round_no),
        "model_hash": model_hash,
        "model_link": model_link,
        "accuracy": accuracy,
        "participants": participants,
        "score_commits": score_commits,
        "aggregator_pk": aggregator_pk_value,
        "timestamp": int(time.time()),
    }

    # ------------------------------------------------------------
    # Canonical hash
    # ------------------------------------------------------------

    block_bytes = canonical_candidate_block(block)
    block_hash = hashlib.sha256(block_bytes).hexdigest()

    block["hash"] = block_hash

    logger.info(
        f"[M4] Candidate block built | hash={block_hash[:12]}..."
    )

    return block
