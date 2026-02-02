# HealChain Aggregator - Task State Management
# task-scoped state management

"""
HealChain Aggregator – Task State
================================

Responsibilities:
-----------------
- Maintain task-scoped, in-memory state
- Track current model, round, weights, and metadata
- Provide controlled mutation of task state

NON-RESPONSIBILITIES:
---------------------
- No cryptography
- No backend communication
- No consensus logic
- No persistence beyond process lifetime
"""

from typing import Any, Dict, List, Optional

from utils.logging import get_logger
from config.constants import (
    TASK_STATE_INITIALIZED,
    TASK_STATE_METADATA_LOADED,
    TASK_STATE_COLLECTING,
    TASK_STATE_AGGREGATING,
    TASK_STATE_EVALUATED,
    TASK_STATE_CANDIDATE_BUILT,
    TASK_STATE_VERIFYING,
    TASK_STATE_PUBLISHED,
    TASK_STATE_ABORTED,
)

logger = get_logger("state.task_state")


class TaskState:
    """
    In-memory state container for a single HealChain task.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id

        # ------------------------------
        # Core task metadata (immutable)
        # ------------------------------
        self.publisher_pk: Optional[str] = None
        self.required_accuracy: Optional[float] = None
        self.max_rounds: Optional[int] = None

        # ------------------------------
        # Aggregation parameters
        # ------------------------------
        self.weights: List[int] = []      # y_i (aggregation weights)
        self.participants: List[str] = [] # miner public keys

        # ------------------------------
        # Model lifecycle
        # ------------------------------
        self.round: int = 0
        self.current_model: Optional[Any] = None

        # ------------------------------
        # Task status
        # ------------------------------
        self.status: str = "INITIALIZED"

    # ------------------------------------------------------------------
    # Metadata Loading
    # ------------------------------------------------------------------

    def load_metadata(self, metadata: Optional[Dict] = None):
        """
        Load task metadata.

        In practice, metadata is fetched indirectly via backend
        before aggregator startup and passed in.

        Expected fields:
        ----------------
        - publisher_pk
        - required_accuracy
        - max_rounds
        - participants
        - weights
        - initial_model
        """

        if metadata is None:
            logger.warning(
                "[TaskState] No metadata provided; assuming preloaded model"
            )
            return

        self.publisher_pk = metadata.get("publisher_pk") or metadata.get("publisher")
        self.required_accuracy = metadata.get("required_accuracy") or metadata.get("targetAccuracy", 0.8)
        self.max_rounds = metadata.get("max_rounds", 1)
        self.round = metadata.get("currentRound", 1)

        self.participants = metadata.get("participants", []) or metadata.get("minerPublicKeys", [])
        self.weights = metadata.get("weights", [])

        self.current_model = metadata.get("initial_model")

        self._validate_metadata()

        self.status = TASK_STATE_METADATA_LOADED
        logger.info(f"[TaskState] Metadata loaded for task {self.task_id}")

    # ------------------------------------------------------------------
    # Model Updates
    # ------------------------------------------------------------------

    def update_model(self, new_model: Any):
        """
        Update the current global model and advance round counter.
        """
        self.current_model = new_model
        self.round += 1
        self.status = "MODEL_UPDATED"

        logger.info(
            f"[TaskState] Model updated | round={self.round}"
        )

    # ------------------------------------------------------------------
    # State Queries
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """
        Check whether task has reached max rounds.
        """
        if self.max_rounds is None:
            return False
        return self.round >= self.max_rounds

    # ------------------------------------------------------------------
    # Internal Validation
    # ------------------------------------------------------------------

    def _validate_metadata(self):
        """
        Defensive validation of loaded metadata.
        """

        if self.required_accuracy is None:
            raise ValueError("required_accuracy missing in task metadata")

        if not isinstance(self.weights, list) or not self.weights:
            raise ValueError("aggregation weights missing or invalid")

        if not isinstance(self.participants, list) or not self.participants:
            raise ValueError("participants list missing or invalid")

        if len(self.weights) != len(self.participants):
            raise ValueError(
                "weights and participants length mismatch"
            )

        logger.info("[TaskState] Metadata validation successful")
