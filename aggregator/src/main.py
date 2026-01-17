
"""
HealChain Aggregator – Main Orchestrator
======================================

Implements Modules:
- M4: Secure Aggregation + BSGS Recovery
- M5: Miner Verification Feedback
- M6: Candidate Block Build & Publish

IMPORTANT:
- Does NOT train models
- Does NOT perform encryption
- Does NOT interact with smart contracts directly
- Treats backend as an untrusted relay

This file coordinates task-scoped execution only.
"""

import os
import time
import threading
from typing import Dict, List

from config.constants import (
    MIN_PARTICIPANTS,  # Default fallback
    AGGREGATION_TIMEOUT,
    FEEDBACK_TIMEOUT,
)

from state.task_state import TaskState
from state.key_manager import KeyManager
from state.progress import ProgressTracker

from backend_iface.receiver import BackendReceiver
from backend_iface.sender import BackendSender

from aggregation.collector import collect_and_validate_submissions
from aggregation.aggregator import secure_aggregate
from aggregation.verifier import verify_recovered_aggregate

from model.apply_update import apply_model_update
from model.evaluate import evaluate_model
from model.artifact import publish_model_artifact

from consensus.candidate import build_candidate_block
from consensus.feedback import collect_feedback
from consensus.majority import has_majority

from utils.logging import get_logger

logger = get_logger("aggregator.main")


class HealChainAggregator:
    """
    Task-scoped Aggregator instance.

    One instance == one taskID
    """

    def __init__(self, task_id: str):
        self.task_id = task_id

        self.state = TaskState(task_id)
        self.keys = KeyManager(task_id)
        self.progress = ProgressTracker(task_id)

        self.backend_rx = BackendReceiver(task_id)
        self.backend_tx = BackendSender(task_id)

        self.running = False

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        logger.info(f"[Aggregator] Starting task {self.task_id}")
        self.running = True

        # Load cryptographic material
        self._initialize_keys()

        # =========================
        # M4: Secure Aggregation
        # =========================
        submissions = self._wait_for_submissions()

        aggregate = self._secure_aggregate(submissions)

        updated_model, acc = self._update_and_evaluate(aggregate)

        # =========================
        # M4: Candidate Formation
        # =========================
        candidate = self._form_candidate(updated_model, acc, submissions)

        # =========================
        # M5: Miner Verification
        # =========================
        if not self._run_miner_verification(candidate):
            logger.error("[Aggregator] Candidate rejected by miners")
            self.running = False
            return

        # =========================
        # M6: Publish Payload
        # =========================
        self._publish_candidate(candidate)

        logger.info(f"[Aggregator] Task {self.task_id} completed (awaiting reveal)")
        self.running = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _get_min_participants(self) -> int:
        """
        Get task-specific min participants from backend metadata.
        Falls back to MIN_PARTICIPANTS constant if not available.
        """
        try:
            # Try to get from backend task metadata
            metadata = self.backend_rx.fetch_key_derivation_metadata()
            if metadata and "minMiners" in metadata:
                return int(metadata["minMiners"])
        except Exception as e:
            logger.warning(f"[Aggregator] Could not fetch minMiners from backend: {e}")
        
        # Fallback to constant
        return MIN_PARTICIPANTS

    def _get_max_participants(self) -> int:
        """
        Get task-specific max participants from backend metadata.
        Falls back to MAX_PARTICIPANTS constant if not available.
        """
        try:
            # Try to get from backend task metadata
            metadata = self.backend_rx.fetch_key_derivation_metadata()
            if metadata and "maxMiners" in metadata:
                return int(metadata["maxMiners"])
        except Exception as e:
            logger.warning(f"[Aggregator] Could not fetch maxMiners from backend: {e}")
        
        # Fallback to constant (from limits.py)
        from config.limits import MAX_MINERS
        return MAX_MINERS

    def _initialize_keys(self):
        """
        Load skA, skFE, pkTP, weight vector y.
        
        Algorithm 2.2: skFE is derived from backend metadata (deterministic).
        """
        import os
        
        # Get aggregator address from environment (optional - will be verified from backend)
        aggregator_address = os.getenv("AGGREGATOR_ADDRESS")
        
        # Load keys (skFE will be derived from backend if backend_receiver provided)
        # Algorithm 2.2: Derive skFE deterministically from task metadata
        self.keys.load(
            backend_receiver=self.backend_rx,
            aggregator_address=aggregator_address
        )
        self.state.load_metadata()

        # Get task-specific min/max miners from backend metadata
        # Fallback to constants if not available
        self.min_participants = self._get_min_participants()
        self.max_participants = self._get_max_participants()

        logger.info(
            f"[Aggregator] Keys and task metadata loaded | "
            f"min_participants={self.min_participants}, max_participants={self.max_participants}"
        )

    # ------------------------------------------------------------------
    # M4 – Submission Collection
    # ------------------------------------------------------------------

    def _wait_for_submissions(self) -> List[Dict]:
        logger.info("[Aggregator] Waiting for miner submissions")

        start = time.time()
        submissions = []

        while time.time() - start < AGGREGATION_TIMEOUT:
            batch = self.backend_rx.fetch_submissions()
            if batch:
                submissions.extend(batch)
                logger.info(f"[Aggregator] Received {len(batch)} submissions")

            if len(submissions) >= self.min_participants:
                break

            time.sleep(1)

        valid_subs = collect_and_validate_submissions(
            submissions=submissions,
            task_id=self.task_id,
            min_participants=self.min_participants,
            max_participants=self.max_participants,
        )

        if len(valid_subs) < self.min_participants:
            raise RuntimeError("Insufficient valid submissions")

        self.progress.mark("submissions_collected")
        return valid_subs

    # ------------------------------------------------------------------
    # M4 – Secure Aggregation
    # ------------------------------------------------------------------

    def _secure_aggregate(self, submissions: List[Dict]):
        logger.info("[Aggregator] Performing NDD-FE secure aggregation")

        aggregate = secure_aggregate(
            submissions=submissions,
            skFE=self.keys.skFE,
            skA=self.keys.skA,
            pkTP=self.keys.pkTP,
            weights=self.state.weights,
        )

        if not verify_recovered_aggregate(
            aggregate,
            submissions,
            self.state.weights,
            self.keys,
        ):
            raise RuntimeError("Aggregate verification failed")

        self.progress.mark("aggregation_complete")
        return aggregate

    # ------------------------------------------------------------------
    # M4 – Model Update & Evaluation
    # ------------------------------------------------------------------

    def _update_and_evaluate(self, aggregate):
        logger.info("[Aggregator] Applying update and evaluating model")

        new_model = apply_model_update(
            base_model=self.state.current_model,
            aggregate_update=aggregate,
        )

        acc = evaluate_model(new_model)

        self.state.update_model(new_model)
        self.progress.mark("model_evaluated")

        logger.info(f"[Aggregator] Model accuracy: {acc:.4f}")
        return new_model, acc

    # ------------------------------------------------------------------
    # M4 – Candidate Block
    # ------------------------------------------------------------------

    def _form_candidate(self, model, acc, submissions):
        logger.info("[Aggregator] Building candidate block")

        model_link, model_hash = publish_model_artifact(
            model,
            task_id=self.task_id,
            round_no=self.state.round,
        )

        candidate = build_candidate_block(
            task_id=self.task_id,
            model_hash=model_hash,
            model_link=model_link,
            accuracy=acc,
            submissions=submissions,
            aggregator_pk=self.keys.pkA,
        )

        self.backend_tx.broadcast_candidate(candidate)
        self.progress.mark("candidate_built")

        return candidate

    # ------------------------------------------------------------------
    # M5 – Miner Verification
    # ------------------------------------------------------------------

    def _run_miner_verification(self, candidate) -> bool:
        logger.info("[Aggregator] Collecting miner verification feedback")

        feedback = collect_feedback(
            backend_rx=self.backend_rx,
            candidate_hash=candidate["hash"],
            timeout=FEEDBACK_TIMEOUT,
        )

        result = has_majority(
            feedback,
            total_participants=len(candidate["participants"]),
        )

        self.progress.mark("verification_complete")
        return result

    # ------------------------------------------------------------------
    # M6 – Publish Payload
    # ------------------------------------------------------------------

    def _publish_candidate(self, candidate):
        logger.info("[Aggregator] Publishing verified payload to backend")

        payload = {
            **candidate,
            "verification": "MAJORITY_VALID",
            "timestamp": int(time.time()),
        }

        self.backend_tx.publish_payload(payload)
        self.progress.mark("published")


# ----------------------------------------------------------------------
# CLI Entry
# ----------------------------------------------------------------------

def main():
    task_id = os.getenv("TASK_ID")
    if not task_id:
        raise EnvironmentError("TASK_ID not set")

    aggregator = HealChainAggregator(task_id)
    aggregator.run()


if __name__ == "__main__":
    main()
