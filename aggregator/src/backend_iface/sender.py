# HealChain Aggregator - Backend Sender
# opaque send

"""
HealChain Aggregator – Backend Sender
====================================

Responsibilities:
-----------------
- Send opaque payloads to backend relay
- Broadcast candidate blocks (M4)
- Publish verified payloads (M6)

SECURITY MODEL:
---------------
- Backend is UNTRUSTED
- This module performs NO cryptographic signing or verification
- All payloads are assumed to be validated upstream
"""

import requests
from typing import Dict

from utils.logging import get_logger

logger = get_logger("backend_iface.sender")


class BackendSender:
    """
    Thin client for sending data to the backend relay.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.base_url = self._load_backend_url()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def broadcast_candidate(self, candidate_block: Dict) -> bool:
        """
        Broadcast candidate block to backend for miner verification (M4 → M5).

        Parameters:
        -----------
        candidate_block : Dict
            Candidate block payload built by consensus/candidate.py

        Returns:
        --------
        success : bool
        """

        endpoint = f"{self.base_url}/aggregator/{self.task_id}/candidate"

        try:
            resp = requests.post(
                endpoint,
                json=candidate_block,
                timeout=5,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"[BackendSender] Candidate broadcast failed "
                    f"(status={resp.status_code})"
                )
                return False

            logger.info("[BackendSender] Candidate broadcast successful")
            return True

        except Exception as e:
            logger.error(f"[BackendSender] Error broadcasting candidate: {e}")
            return False

    def publish_payload(self, payload: Dict) -> bool:
        """
        Publish verified payload after miner consensus (M6).

        This payload is later used by:
        - smart contracts (commit–reveal / rewards)
        - auditors / observers

        Parameters:
        -----------
        payload : Dict
            Final verified task payload

        Returns:
        --------
        success : bool
        """

        endpoint = f"{self.base_url}/aggregator/{self.task_id}/publish"

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                timeout=5,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"[BackendSender] Payload publish failed "
                    f"(status={resp.status_code})"
                )
                return False

            logger.info("[BackendSender] Payload published successfully")
            return True

        except Exception as e:
            logger.error(f"[BackendSender] Error publishing payload: {e}")
            return False

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _load_backend_url(self) -> str:
        """
        Load backend base URL from environment.
        """

        import os

        url = os.getenv("BACKEND_URL")
        if not url:
            raise EnvironmentError("BACKEND_URL not set")

        logger.info(f"[BackendSender] Using backend URL: {url}")
        return url.rstrip("/")
