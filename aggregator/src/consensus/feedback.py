# HealChain Aggregator - Feedback Module
# miner votes (M5)

"""
HealChain Aggregator – Miner Feedback Collection (Module M5)
===========================================================

Responsibilities:
-----------------
- Collect miner verification feedback on candidate block
- Verify miner signatures on feedback
- Enforce task and candidate binding
- Filter malformed or invalid feedback

NON-RESPONSIBILITIES:
---------------------
- No consensus decision (handled by majority.py)
- No cryptographic aggregation
- No backend publishing
- No smart contract interaction
"""

import time
from typing import Dict, List

from utils.validation import verify_signature
from utils.logging import get_logger
from utils.serialization import canonical_feedback_message
from config.constants import VERDICT_VALID, VERDICT_INVALID

logger = get_logger("consensus.feedback")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def collect_feedback(
    *,
    backend_rx,
    task_id: str,
    candidate_hash: str,
    expected_participants: List[str],
    timeout: int,
) -> List[Dict]:
    """
    Collect miner feedback messages for a candidate block.

    Parameters:
    -----------
    backend_rx :
        BackendReceiver instance (opaque relay)

    candidate_hash : str
        Hash of candidate block being verified

    timeout : int
        Time window (seconds) to wait for feedback

    Expected feedback format:
    -------------------------
    {
        "task_id": str,
        "candidate_hash": str,
        "miner_pk": str,
        "verdict": "VALID" | "INVALID",
        "reason": str,
        "signature": str
    }

    Returns:
    --------
    feedbacks : List[Dict]
        Verified feedback entries
    """

    logger.info(
        f"[M5] Collecting miner feedback for candidate {candidate_hash[:12]}..."
    )

    start_time = time.time()
    feedbacks: List[Dict] = []

    seen_miners = set()
    expected_participant_set = {_normalize_public_key(pk) for pk in expected_participants if isinstance(pk, str)}

    while time.time() - start_time < timeout:
        batch = backend_rx.fetch_feedback()
        if not batch:
            time.sleep(1)
            continue

        for fb in batch:
            try:
                _validate_feedback_structure(
                    fb,
                    expected_task_id=task_id,
                    expected_candidate_hash=candidate_hash,
                    expected_participants=expected_participant_set,
                )

                miner_pk = fb["miner_pk"]
                normalized_miner_pk = _normalize_public_key(miner_pk)
                if normalized_miner_pk in seen_miners:
                    logger.warning(
                        f"[M5] Duplicate feedback from miner {miner_pk[:10]}..."
                    )
                    continue

                _verify_feedback_signature(fb)

                feedbacks.append(fb)
                seen_miners.add(normalized_miner_pk)

                logger.info(
                    f"[M5] Feedback accepted from miner {miner_pk[:10]}..."
                )

            except Exception as e:
                logger.warning(
                    f"[M5] Rejected feedback: {str(e)}"
                )

        time.sleep(0.5)

    logger.info(
        f"[M5] Feedback collection complete: {len(feedbacks)} valid responses"
    )

    return feedbacks


# -------------------------------------------------------------------
# Internal Validators
# -------------------------------------------------------------------


def _verify_feedback_signature(fb: Dict):
    """
    Verify miner signature on feedback.

    Signature covers:
        HASH(task_id || candidate_hash || verdict || reason || miner_pk)
    """

    message = _canonical_feedback_message(fb)

    if not verify_signature(
        public_key=fb["miner_pk"],
        message=message,
        signature=fb["signature"],
    ):
        raise ValueError("Invalid feedback signature")


def _canonical_feedback_message(fb: Dict) -> bytes:
    """
    Deterministic encoding of feedback message for signature verification.
    """
    return canonical_feedback_message(
        task_id=fb["task_id"],
        candidate_hash=fb["candidate_hash"],
        verdict=fb["verdict"],
        reason=fb["reason"],
        miner_pk=fb["miner_pk"],
    )


def _normalize_public_key(pk: str) -> str:
    parts = pk.split(",")
    if len(parts) != 2:
        return pk.strip().lower()
    norm = []
    for p in parts:
        t = p.strip().lower()
        if t.startswith("0x"):
            t = t[2:]
        norm.append(t)
    return ",".join(norm)


def _validate_feedback_structure(
    fb: Dict,
    *,
    expected_task_id: str,
    expected_candidate_hash: str,
    expected_participants: set,
):
    """
    Structural + protocol binding checks for feedback.
    """
    required_fields = {
        "task_id",
        "candidate_hash",
        "miner_pk",
        "verdict",
        "reason",
        "signature",
    }

    missing = required_fields - fb.keys()
    if missing:
        raise ValueError(f"Missing feedback fields: {','.join(missing)}")

    if str(fb["task_id"]) != str(expected_task_id):
        raise ValueError("Task ID mismatch")

    if str(fb["candidate_hash"]) != str(expected_candidate_hash):
        raise ValueError("Candidate hash mismatch")

    if fb["verdict"] not in (VERDICT_VALID, VERDICT_INVALID):
        raise ValueError("Invalid verdict value")

    if not isinstance(fb["miner_pk"], str):
        raise ValueError("Invalid miner_pk")

    normalized_pk = _normalize_public_key(fb["miner_pk"])
    if expected_participants and normalized_pk not in expected_participants:
        raise ValueError("Feedback miner is not a candidate participant")

    if not isinstance(fb["reason"], str):
        raise ValueError("Invalid reason format")

    if not isinstance(fb["signature"], str):
        raise ValueError("Invalid signature format")
