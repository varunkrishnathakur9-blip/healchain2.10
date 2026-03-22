"""
HealChain Aggregator - Environment Sync Helpers
================================================

Keeps non-secret task-scoped key material in sync with backend metadata:
- TASK_ID
- AGGREGATOR_ADDRESS
- AGGREGATOR_PK
- TP_PUBLIC_KEY

Private keys (AGGREGATOR_SK) are intentionally never auto-written.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Dict, List


_ENV_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
_ENV_SYNC_LOCK = threading.Lock()


def _default_env_path() -> Path:
    # .../aggregator/src/utils/env_sync.py -> .../aggregator
    root = Path(__file__).resolve().parents[2]
    return root / ".env"


def _load_env_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _upsert_env_key(lines: List[str], key: str, value: str) -> bool:
    target = f"{key}={value}"
    for idx, line in enumerate(lines):
        m = _ENV_ASSIGN_RE.match(line)
        if m and m.group(1) == key:
            if lines[idx] == target:
                return False
            lines[idx] = target
            return True

    # key not found -> append
    if lines and lines[-1].strip():
        lines.append("")
    lines.append(target)
    return True


def sync_task_keys_to_env(task_id: str, task_public_keys: Dict) -> List[str]:
    """
    Persist backend task public keys into process environment and .env file.

    Returns list of updated keys in the file.
    """
    if not task_id:
        return []

    updates: Dict[str, str] = {"TASK_ID": task_id}
    agg_addr = (task_public_keys.get("aggregatorAddress") or "").strip()
    agg_pk = (task_public_keys.get("aggregatorPublicKey") or "").strip()
    tp_pk = (task_public_keys.get("tpPublicKey") or "").strip()

    if agg_addr:
        updates["AGGREGATOR_ADDRESS"] = agg_addr
    if agg_pk:
        updates["AGGREGATOR_PK"] = agg_pk
    if tp_pk:
        updates["TP_PUBLIC_KEY"] = tp_pk

    # Always sync process env first for current run.
    for k, v in updates.items():
        os.environ[k] = v

    if os.getenv("AUTO_SYNC_TASK_KEYS", "1") == "0":
        return []

    env_path_raw = os.getenv("AUTO_SYNC_ENV_FILE", "").strip()
    env_path = Path(env_path_raw) if env_path_raw else _default_env_path()

    changed_keys: List[str] = []
    with _ENV_SYNC_LOCK:
        lines = _load_env_lines(env_path)
        for key, value in updates.items():
            if _upsert_env_key(lines, key, value):
                changed_keys.append(key)

        if changed_keys:
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return changed_keys

