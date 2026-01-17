# HealChain Aggregator - Collection Module
# submission validation

"""
HealChain Aggregator – Submission Collector & Validator
=======================================================

Implements:
- Miner submission validation (Module M4 – pre-aggregation)

Responsibilities:
-----------------
- Validate miner signatures
- Ensure required submission fields exist
- Enforce task binding (task_id)
- Filter malformed or malicious submissions

NON-RESPONSIBILITIES:
---------------------
- No cryptographic aggregation
- No FE decryption
- No BSGS
- No backend communication
"""

from typing import Dict, List

from utils.validation import verify_signature
from utils.logging import get_logger

logger = get_logger("aggregation.collector")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def collect_and_validate_submissions(
    *,
    submissions: List[Dict],
    task_id: str,
    min_participants: int,
    max_participants: int = None,  # Optional: cap submissions at max
) -> List[Dict]:
    """
    Validate miner submissions and return only valid ones.

    Parameters:
    -----------
    submissions : List[Dict]
        Raw submissions received from backend (FL client format)

    task_id : str
        Current HealChain task ID

    min_participants : int
        Minimum number of valid submissions required

    Expected submission format (FL client):
    ------------------------------------
    {
        "taskID": str,                    # FL client uses camelCase
        "miner_pk": str,
        "ciphertext": str or [str],       # Can be string or list
        "scoreCommit": str,               # FL client uses camelCase
        "signature": str,                 # Required for security
        "quantization_scale": int         # Optional FL client field
    }

    Returns:
    --------
    valid_submissions : List[Dict]
        Normalized submissions ready for aggregation
    """

    logger.info(
        f"[M4] Validating {len(submissions)} miner submissions"
    )

    valid: List[Dict] = []

    for idx, sub in enumerate(submissions):
        try:
            # Normalize FL client format to aggregator format
            normalized = _normalize_submission(sub)
            _validate_submission_structure(normalized, task_id)
            _verify_submission_signature(normalized)
            valid.append(normalized)
        except Exception as e:
            logger.warning(
                f"[M4] Rejected submission {idx}: {str(e)}"
            )

    if len(valid) < min_participants:
        raise RuntimeError(
            f"Insufficient valid submissions "
            f"({len(valid)} < {min_participants})"
        )

    # Cap submissions at max_participants if specified
    if max_participants is not None and len(valid) > max_participants:
        logger.warning(
            f"[M4] Capping submissions from {len(valid)} to {max_participants} "
            f"(task maxMiners limit)"
        )
        valid = valid[:max_participants]

    logger.info(
        f"[M4] {len(valid)} submissions accepted"
    )

    return valid


# -------------------------------------------------------------------
# Normalization Helper
# -------------------------------------------------------------------

def _normalize_submission(sub: Dict) -> Dict:
    """
    Normalize FL client submission format to aggregator format.
    
    Handles:
    - Field name mapping (camelCase → snake_case)
    - Ciphertext format (string → list)
    - Optional field preservation
    """
    
    normalized = {}
    
    # Map FL client fields to aggregator fields
    normalized["task_id"] = sub.get("taskID", sub.get("task_id"))
    normalized["miner_pk"] = sub.get("miner_pk")
    normalized["score_commit"] = sub.get("scoreCommit", sub.get("score_commit"))
    normalized["signature"] = sub.get("signature")
    
    # Handle ciphertext format (string or list)
    ciphertext = sub.get("ciphertext", [])
    if isinstance(ciphertext, str):
        normalized["ciphertext"] = [ciphertext]
    elif isinstance(ciphertext, list):
        normalized["ciphertext"] = ciphertext
    else:
        raise ValueError("Invalid ciphertext format")
    
    # Preserve optional FL client fields
    if "quantization_scale" in sub:
        normalized["quantization_scale"] = sub["quantization_scale"]
    
    return normalized


# -------------------------------------------------------------------
# Internal Validators
# -------------------------------------------------------------------

def _validate_submission_structure(sub: Dict, task_id: str):
    """
    Structural and semantic validation (after normalization).
    """

    required_fields = {
        "task_id",
        "miner_pk",
        "ciphertext",
        "score_commit",
        "signature",
    }

    missing = required_fields - sub.keys()
    if missing:
        raise ValueError(
            f"Missing fields: {','.join(missing)}"
        )

    if sub["task_id"] != task_id:
        raise ValueError("Task ID mismatch")

    # After normalization, ciphertext should always be a list
    if not isinstance(sub["ciphertext"], list) or not sub["ciphertext"]:
        raise ValueError("Ciphertext must be non-empty list")

    if not isinstance(sub["score_commit"], str):
        raise ValueError("Invalid score_commit")

    if not isinstance(sub["miner_pk"], str):
        raise ValueError("Invalid miner_pk")

    if not isinstance(sub["signature"], str):
        raise ValueError("Invalid signature")

    # Validate ciphertext format (should be hex points)
    for ct in sub["ciphertext"]:
        if not isinstance(ct, str):
            raise ValueError("Ciphertext entries must be strings")
        # Basic hex format validation
        if "," not in ct:  # Expected "x_hex,y_hex" format
            raise ValueError("Invalid ciphertext point format")


def _verify_submission_signature(sub: Dict):
    """
    Verify miner signature.

    Signature covers:
        HASH(task_id || ciphertext_hash || score_commit || miner_pk)
    """

    message = _canonical_message(sub)

    if not verify_signature(
        public_key=sub["miner_pk"],
        message=message,
        signature=sub["signature"],
    ):
        raise ValueError("Invalid miner signature")


def _canonical_message(sub: Dict) -> bytes:
    """
    Deterministic message encoding for signature verification.
    """

    ciphertext_concat = ",".join(sub["ciphertext"])

    parts = [
        sub["task_id"],
        ciphertext_concat,
        sub["score_commit"],
        sub["miner_pk"],
    ]

    return "|".join(parts).encode("utf-8")
