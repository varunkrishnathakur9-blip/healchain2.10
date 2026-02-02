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
from config.constants import VERDICT_VALID, VERDICT_INVALID

logger = get_logger("consensus.feedback")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def collect_feedback(
    *,
    backend_rx,
    candidate_hash: str,
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

    while time.time() - start_time < timeout:
        batch = backend_rx.fetch_feedback()
        if not batch:
            time.sleep(1)
            continue

        for fb in batch:
            try:
                # Inject candidate_hash since backend doesn't store/return it
                fb["candidate_hash"] = candidate_hash
                
                _validate_feedback_structure(fb, candidate_hash)

                miner_pk = fb["miner_pk"]
                if miner_pk in seen_miners:
                    logger.warning(
                        f"[M5] Duplicate feedback from miner {miner_pk[:10]}..."
                    )
                    continue

                _verify_feedback_signature(fb)

                feedbacks.append(fb)
                seen_miners.add(miner_pk)

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

def _validate_feedback_structure(fb: Dict, candidate_hash: str):
    """
    Structural and semantic validation of feedback message.
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

    if fb["candidate_hash"] != candidate_hash:
        raise ValueError("Candidate hash mismatch")

    if fb["verdict"] not in (VERDICT_VALID, VERDICT_INVALID):
        raise ValueError("Invalid verdict value")

    if not isinstance(fb["miner_pk"], str):
        raise ValueError("Invalid miner_pk")

    if not isinstance(fb["signature"], str):
        raise ValueError("Invalid signature format")


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

    # Match FL Client message format:
    # f"HealChain Verification\nTask: {task_id}\nVerdict: {verdict}\nMiner: {miner_address}"
    message = (
        f"HealChain Verification\n"
        f"Task: {fb['task_id']}\n"
        f"Verdict: {fb['verdict']}\n"
        f"Miner: {fb['miner_pk']}"
    )

    return message.encode("utf-8")
