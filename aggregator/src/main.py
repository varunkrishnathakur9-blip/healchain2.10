
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
from typing import Dict, List, Optional

from config.constants import (
    MIN_PARTICIPANTS,  # Default fallback
    AGGREGATION_TIMEOUT,
    BACKEND_POLL_INTERVAL,
    FEEDBACK_TIMEOUT,
)

from state.task_state import TaskState
from state.key_manager import KeyManager
from state.progress import ProgressTracker

from backend_iface.receiver import BackendReceiver
from backend_iface.sender import BackendSender

from aggregation.collector import collect_and_validate_submissions
from aggregation.aggregator import secure_aggregate

from model.apply_update import apply_model_update
from model.evaluate import evaluate_model
from model.artifact import publish_model_artifact
from model.vector_model import VectorModel
from model.loader import load_base_model_from_link

from consensus.candidate import build_candidate_block
from consensus.feedback import collect_feedback
from consensus.majority import has_majority

from utils.logging import get_logger
from utils.env_sync import sync_task_keys_to_env

logger = get_logger("aggregator.main")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str) -> Optional[float]:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        val = float(str(raw).strip())
    except Exception as e:
        raise ValueError(f"{name} must be a float in [0.0, 1.0], got: {raw!r}") from e
    if not (0.0 <= val <= 1.0):
        raise ValueError(f"{name} must be in [0.0, 1.0], got: {val}")
    return val


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
        # Algorithm 4: Accuracy Check (Lines 35-40)
        # =========================
        if acc < self.state.required_accuracy:
            logger.warning(
                f"[Aggregator] Accuracy {acc:.4f} < {self.state.required_accuracy:.4f}. "
                f"Starting next round (current round: {self.state.round})."
            )
            if self.backend_tx.reset_round():
                logger.info("[Aggregator] Round reset successful. Aggregator exiting.")
                self.running = False
                return
            else:
                logger.error("[Aggregator] Failed to trigger round reset in backend.")
                raise RuntimeError("Round reset failed")

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
        
        # Get aggregator address from environment
        aggregator_address = os.getenv("AGGREGATOR_ADDRESS")
        
        # Fetch metadata once to share between components
        metadata = self.backend_rx.fetch_key_derivation_metadata()
        if not metadata:
            raise RuntimeError("Could not fetch task metadata from backend")
        task_public_keys = self.backend_rx.fetch_task_public_keys() or {}

        try:
            changed_keys = sync_task_keys_to_env(self.task_id, task_public_keys)
            if changed_keys:
                logger.info(
                    f"[Aggregator] Synced task keys into .env: {', '.join(changed_keys)}"
                )
        except Exception as e:
            logger.warning(f"[Aggregator] Failed to sync task keys into .env: {e}")

        # Load keys (skFE will be derived from backend using metadata)
        self.keys.load(
            aggregator_address=aggregator_address,
            metadata=metadata,
            task_public_keys=task_public_keys,
        )
        # Load state metadata
        self.state.load_metadata(metadata=metadata)

        # Fetch full task details (includes initialModelLink and status fields).
        task_details = self.backend_rx.fetch_task_details() or {}
        self.state.initial_model_link = task_details.get("initialModelLink")

        allow_zero_base = _env_flag("AGGREGATOR_ALLOW_ZERO_BASE_MODEL", default=False)
        static_acc = _env_float("AGGREGATOR_STATIC_ACCURACY")

        if self.state.current_model is None and self.state.initial_model_link:
            try:
                self.state.current_model = load_base_model_from_link(
                    task_id=self.task_id,
                    model_link=self.state.initial_model_link,
                    static_accuracy=static_acc,
                )
                logger.info(
                    "[Aggregator] Loaded base model from task initialModelLink "
                    f"({self.state.initial_model_link})"
                )
            except Exception as e:
                logger.warning(
                    "[Aggregator] Could not load base model from initialModelLink: "
                    f"{e}"
                )

        # Strict-by-default: fail before expensive crypto if no base model is available.
        if self.state.current_model is None and not allow_zero_base:
            initial_link = self.state.initial_model_link
            raise RuntimeError(
                "Base model is missing before aggregation (current_model is None). "
                f"Task initialModelLink={initial_link!r}. "
                "Aggregator failed to load a runtime model from this link (or link is unavailable). "
                "Either provide a loadable model artifact link, a preloaded model object in metadata, "
                "or explicitly enable non-strict "
                "fallback with AGGREGATOR_ALLOW_ZERO_BASE_MODEL=1 and AGGREGATOR_STATIC_ACCURACY."
            )

        if allow_zero_base and static_acc is None:
            raise RuntimeError(
                "AGGREGATOR_ALLOW_ZERO_BASE_MODEL=1 requires AGGREGATOR_STATIC_ACCURACY "
                "(float in [0.0, 1.0]) to be set."
            )

        if isinstance(self.state.current_model, VectorModel) and static_acc is None:
            raise RuntimeError(
                "Vector-model runtime requires AGGREGATOR_STATIC_ACCURACY "
                "(float in [0.0, 1.0]) because no dataset-bound evaluator is configured "
                "in aggregator."
            )

        self.min_participants = self._get_min_participants()
        self.max_participants = self._get_max_participants()

        logger.info(
            f"[Aggregator] Keys and task metadata loaded | "
            f"round={self.state.round}, target_acc={self.state.required_accuracy}, "
            f"min_participants={self.min_participants}"
        )

    # ------------------------------------------------------------------
    # M4 – Submission Collection
    # ------------------------------------------------------------------

    def _wait_for_submissions(self) -> List[Dict]:
        logger.info("[Aggregator] Waiting for miner submissions")

        start = time.time()
        # Keep latest submission per gradient id to avoid duplicates across polls.
        submissions_by_id = {}

        while time.time() - start < AGGREGATION_TIMEOUT:
            batch = self.backend_rx.fetch_submissions()
            if batch:
                new_count = 0
                for sub in batch:
                    sub_id = sub.get("id")
                    if not sub_id:
                        continue
                    if sub_id not in submissions_by_id:
                        new_count += 1
                    submissions_by_id[sub_id] = sub
                logger.info(
                    f"[Aggregator] Received {len(batch)} submissions "
                    f"({new_count} new, {len(submissions_by_id)} unique total)"
                )

            if len(submissions_by_id) >= self.min_participants:
                break

            time.sleep(BACKEND_POLL_INTERVAL)

        submissions = list(submissions_by_id.values())

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

        # Align weights with the accepted submissions only.
        # state.weights/state.participants are task-level metadata and may include
        # miners whose submissions were rejected or missing.
        participant_to_weight = {
            pk: w for pk, w in zip(self.state.participants, self.state.weights)
        }
        active_weights = []
        for sub in submissions:
            miner_pk = sub.get("miner_pk")
            if miner_pk not in participant_to_weight:
                raise RuntimeError(
                    f"Missing aggregation weight for submission miner_pk={miner_pk}"
                )
            active_weights.append(participant_to_weight[miner_pk])

        aggregate = secure_aggregate(
            submissions=submissions,
            skFE=self.keys.skFE,
            skA=self.keys.skA,
            pkTP=self.keys.pkTP,
            weights=active_weights,
        )

        self.progress.mark("aggregation_complete")
        return aggregate

    # ------------------------------------------------------------------
    # M4 – Model Update & Evaluation
    # ------------------------------------------------------------------

    def _update_and_evaluate(self, aggregate):
        logger.info("[Aggregator] Applying update and evaluating model")

        if self.state.current_model is None:
            # Explicit, non-strict fallback for environments without a real base-model runtime.
            static_acc = _env_float("AGGREGATOR_STATIC_ACCURACY")
            self.state.current_model = VectorModel(
                [0.0] * len(aggregate),
                static_accuracy=static_acc,
            )
            logger.warning(
                "[Aggregator] Using zero-initialized base model "
                "(AGGREGATOR_ALLOW_ZERO_BASE_MODEL=1). "
                "This mode is for controlled testing only."
            )

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
            round_no=self.state.round,
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
