# HealChain Aggregator - Backend Receiver
# opaque receive

"""
HealChain Aggregator – Backend Receiver
======================================

Responsibilities:
-----------------
- Fetch opaque data blobs from backend
- Provide simple polling interface for:
    - miner submissions (M4)
    - miner feedback (M5)

SECURITY MODEL:
---------------
- Backend is UNTRUSTED
- This module performs NO cryptographic validation
- All received data is treated as potentially malicious
"""

import time
import requests
from typing import List, Dict, Optional

from utils.logging import get_logger

logger = get_logger("backend_iface.receiver")


class BackendReceiver:
    """
    Thin client for receiving data from the backend relay.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.base_url = self._load_backend_url()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_submissions(self) -> List[Dict]:
        """
        Fetch miner submissions for this task.

        Returns:
        --------
        List of submission dicts (possibly empty)
        """

        endpoint = f"{self.base_url}/aggregator/{self.task_id}/submissions"

        try:
            resp = requests.get(endpoint, timeout=5)
            if resp.status_code != 200:
                logger.warning(
                    f"[BackendReceiver] Submissions fetch failed "
                    f"(status={resp.status_code})"
                )
                return []

            data = resp.json()
            if not isinstance(data, list):
                logger.warning(
                    "[BackendReceiver] Invalid submissions payload type"
                )
                return []

            return data

        except Exception as e:
            logger.error(f"[BackendReceiver] Error fetching submissions: {e}")
            return []

    def fetch_feedback(self) -> List[Dict]:
        """
        Fetch miner feedback messages for this task.

        Returns:
        --------
        List of feedback dicts (possibly empty)
        """

        endpoint = f"{self.base_url}/verification/{self.task_id}"

        try:
            resp = requests.get(endpoint, timeout=5)
            if resp.status_code != 200:
                logger.warning(
                    f"[BackendReceiver] Feedback fetch failed "
                    f"(status={resp.status_code})"
                )
                return []

            data = resp.json()
            if not isinstance(data, list):
                logger.warning(
                    "[BackendReceiver] Invalid feedback payload type"
                )
                return []

            # Normalize backend feedback to aggregator format
            normalized_batch = []
            for fb in data:
                normalized = {
                    "task_id": fb.get("taskID"),
                    "miner_pk": fb.get("minerAddress"),
                    "verdict": fb.get("verdict"),
                    "signature": fb.get("signature"),
                    "candidate_hash": None, # Backend doesn't store this, will be injected by collector
                    "reason": "MVP Verification" # Placeholder
                }
                normalized_batch.append(normalized)

            return normalized_batch

        except Exception as e:
            logger.error(f"[BackendReceiver] Error fetching feedback: {e}")
            return []

    def fetch_key_derivation_metadata(self) -> Optional[Dict]:
        """
        Fetch key derivation metadata from backend (Algorithm 2.2).

        Algorithm 2: The aggregator derives skFE deterministically using:
        skFE = H(publisher || minerPKs || taskID || nonceTP)

        This endpoint returns all inputs needed for derivation.

        Returns:
        --------
        metadata : Optional[Dict]
            {
                "taskID": str,
                "publisher": str,
                "minerPublicKeys": List[str],
                "nonceTP": str,
                "aggregatorAddress": str,
                "minerCount": int
            }
            or None if error
        """

        endpoint = f"{self.base_url}/aggregator/key-derivation/{self.task_id}"

        try:
            resp = requests.get(endpoint, timeout=5)

            if resp.status_code == 404:
                logger.warning(
                    "[BackendReceiver] Task not found for key derivation"
                )
                return None

            if resp.status_code != 200:
                logger.warning(
                    f"[BackendReceiver] Key derivation metadata fetch failed "
                    f"(status={resp.status_code}): {resp.text}"
                )
                return None

            data = resp.json()

            # Validate required fields
            required = ["taskID", "publisher", "minerPublicKeys", "nonceTP"]
            if not all(field in data for field in required):
                logger.warning(
                    "[BackendReceiver] Invalid key derivation metadata payload"
                )
                return None

            logger.info(
                f"[BackendReceiver] Key derivation metadata fetched: "
                f"{data.get('minerCount', 0)} miners"
            )
            return data

        except Exception as e:
            logger.error(
                f"[BackendReceiver] Error fetching key derivation metadata: {e}"
            )
            return None

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

        logger.info(f"[BackendReceiver] Using backend URL: {url}")
        return url.rstrip("/")
