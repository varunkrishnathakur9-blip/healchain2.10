# HealChain Aggregator - Progress Tracking
# workflow tracking

"""
HealChain Aggregator – Progress Tracker
======================================

Responsibilities:
-----------------
- Track execution milestones for a single task
- Provide deterministic visibility into workflow progress
- Support debugging, auditing, and testing

NON-RESPONSIBILITIES:
---------------------
- No persistence (in-memory only)
- No backend or contract interaction
- No cryptographic logic
"""

import time
from typing import Dict, List, Optional

from utils.logging import get_logger

logger = get_logger("state.progress")


class ProgressTracker:
    """
    In-memory progress tracker for a single HealChain task.

    Each task has a linear sequence of milestones, marked as they complete.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._milestones: Dict[str, float] = {}
        self._order: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark(self, milestone: str):
        """
        Mark a milestone as completed.

        Records:
        - milestone name
        - completion timestamp
        """
        if milestone in self._milestones:
            logger.warning(
                f"[Progress] Milestone '{milestone}' already marked"
            )
            return

        ts = time.time()
        self._milestones[milestone] = ts
        self._order.append(milestone)

        logger.info(
            f"[Progress] Task {self.task_id} reached milestone '{milestone}'"
        )

    def has_reached(self, milestone: str) -> bool:
        """
        Check whether a milestone has been reached.
        """
        return milestone in self._milestones

    def timestamp(self, milestone: str) -> Optional[float]:
        """
        Get the timestamp for a completed milestone.
        """
        return self._milestones.get(milestone)

    def summary(self) -> Dict[str, float]:
        """
        Return an ordered summary of milestones and timestamps.
        """
        return {m: self._milestones[m] for m in self._order}

    # ------------------------------------------------------------------
    # Debug / Inspection
    # ------------------------------------------------------------------

    def dump(self) -> str:
        """
        Human-readable progress dump (for logs / debugging).
        """
        lines = [f"Progress for task {self.task_id}:"]
        for m in self._order:
            ts = self._milestones[m]
            lines.append(f"  - {m}: {time.ctime(ts)}")
        return "\n".join(lines)
