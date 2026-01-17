# HealChain Aggregator - Majority Logic
# threshold logic

"""
HealChain Aggregator – Majority Decision Logic (Module M5)
=========================================================

Responsibilities:
-----------------
- Decide whether miner feedback reaches majority approval
- Support configurable fault tolerance
- Enforce deterministic consensus outcome

NON-RESPONSIBILITIES:
---------------------
- No feedback collection (handled by feedback.py)
- No cryptographic verification
- No backend or smart contract interaction
"""

from typing import Dict, List

from utils.logging import get_logger
from config.constants import VERDICT_VALID, VERDICT_INVALID

logger = get_logger("consensus.majority")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def has_majority(
    feedbacks: List[Dict],
    *,
    total_participants: int,
    tolerable_fault_rate: float = 0.33,
) -> bool:
    """
    Determine whether majority consensus is achieved.

    Parameters:
    -----------
    feedbacks : List[Dict]
        Verified miner feedback entries, each with:
            {
              "miner_pk": str,
              "verdict": "VALID" | "INVALID",
              ...
            }

    total_participants : int
        Number of miners expected to vote (from candidate block)

    tolerable_fault_rate : float
        Fraction of faulty / Byzantine miners tolerated.
        Default: 0.33 (Byzantine-safe threshold)

    Consensus Rule:
    ---------------
    valid_count >= ceil(total_participants * (1 - tolerable_fault_rate))

    Returns:
    --------
    True if candidate is accepted, False otherwise
    """

    if total_participants <= 0:
        raise ValueError("total_participants must be positive")

    # ------------------------------------------------------------
    # Count verdicts
    # ------------------------------------------------------------
    valid_votes = 0
    invalid_votes = 0

    for fb in feedbacks:
        verdict = fb.get("verdict")
        if verdict == VERDICT_VALID:
            valid_votes += 1
        elif verdict == VERDICT_INVALID:
            invalid_votes += 1

    required_majority = _required_majority(
        total_participants,
        tolerable_fault_rate,
    )

    logger.info(
        "[M5] Consensus tally | "
        f"VALID={valid_votes}, INVALID={invalid_votes}, "
        f"REQUIRED={required_majority}"
    )

    # ------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------
    if valid_votes >= required_majority:
        logger.info(f"[M5] Majority {VERDICT_VALID} reached")
        return True

    logger.warning(f"[M5] Majority {VERDICT_VALID} NOT reached")
    return False


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _required_majority(
    total_participants: int,
    tolerable_fault_rate: float,
) -> int:
    """
    Compute required number of VALID votes.

    Formula:
        ceil(N * (1 - f))
    """
    if not (0.0 <= tolerable_fault_rate < 1.0):
        raise ValueError("tolerable_fault_rate must be in [0, 1)")

    return int(
        (total_participants * (1.0 - tolerable_fault_rate)) + 0.999999
    )
