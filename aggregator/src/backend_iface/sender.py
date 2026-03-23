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

import os
import time
from typing import Dict

import requests

from utils.logging import get_logger

logger = get_logger("backend_iface.sender")


class BackendSender:
    """
    Thin client for sending data to the backend relay.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.base_url = self._load_backend_url()
        self._http_timeout = (
            float(os.getenv("BACKEND_CONNECT_TIMEOUT", "5")),
            float(os.getenv("BACKEND_READ_TIMEOUT", "120")),
        )
        self._round_reset_retry_count = int(os.getenv("ROUND_RESET_RETRIES", "8"))
        self._round_reset_backoff_seconds = float(
            os.getenv("ROUND_RESET_BACKOFF_SECONDS", "1.0")
        )

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

        endpoint = f"{self.base_url}/aggregator/submit-candidate"

        # Normalize fields for backend (camelCase + scaled accuracy for BigInt)
        normalized_payload = {
            "taskID": candidate_block.get("task_id"),
            "modelHash": candidate_block.get("model_hash"),
            "modelLink": candidate_block.get("model_link"),
            "accuracy": int(candidate_block.get("accuracy", 0) * 1000000), # Scale to 6 decimal places for BigInt
            "miners": candidate_block.get("participants", []),
            "scoreCommits": candidate_block.get("score_commits", []),
            "aggregatorPK": candidate_block.get("aggregator_pk"),
            "hash": candidate_block.get("hash")
        }

        try:
            resp = requests.post(
                endpoint,
                json=normalized_payload,
                timeout=self._http_timeout,
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

        endpoint = f"{self.base_url}/aggregator/publish"

        # Normalize fields for backend
        normalized_payload = {
            "taskID": payload.get("task_id"),
            "modelHash": payload.get("model_hash"),
            "accuracy": int(payload.get("accuracy", 0) * 1000000),
            "miners": payload.get("participants", []),
            "verification": payload.get("verification")
        }

        try:
            resp = requests.post(
                endpoint,
                json=normalized_payload,
                timeout=self._http_timeout,
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

    def reset_round(self, model_link: str | None = None) -> bool:
        """
        Trigger a new FL round in the backend (Algorithm 4 lines 35-40).
        - Increments round counter
        - Clears old gradients
        """
        endpoint = f"{self.base_url}/aggregator/{self.task_id}/reset-round"
        payload = {}
        if isinstance(model_link, str) and model_link.strip():
            payload["modelLink"] = model_link.strip()

        for attempt in range(self._round_reset_retry_count):
            try:
                resp = requests.post(
                    endpoint,
                    json=payload if payload else None,
                    timeout=self._http_timeout,
                )
                if resp.status_code == 200:
                    logger.info(
                        "[BackendSender] Round reset triggered successfully "
                        f"for {self.task_id} (attempt {attempt + 1}/{self._round_reset_retry_count})"
                    )
                    return True

                logger.warning(
                    "[BackendSender] Round reset failed "
                    f"(status={resp.status_code}, attempt={attempt + 1}/{self._round_reset_retry_count})"
                )
            except Exception as e:
                logger.warning(
                    "[BackendSender] Error triggering round reset "
                    f"(attempt={attempt + 1}/{self._round_reset_retry_count}): {e}"
                )

            if attempt < self._round_reset_retry_count - 1:
                time.sleep(self._round_reset_backoff_seconds * (attempt + 1))

        return False

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _load_backend_url(self) -> str:
        """
        Load backend base URL from environment.
        """
        url = os.getenv("BACKEND_URL")
        if not url:
            raise EnvironmentError("BACKEND_URL not set")

        logger.info(f"[BackendSender] Using backend URL: {url}")
        return url.rstrip("/")
