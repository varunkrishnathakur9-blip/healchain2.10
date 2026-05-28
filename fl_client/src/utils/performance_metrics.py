"""
Lightweight JSONL performance probes for experimentation runs.

Metrics writes are best-effort by design. A filesystem issue must never break
training or protocol execution.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import time
from typing import Any


def _default_metrics_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "experimentation_and_result_Analysis" / "monitoring_metrics"


def _metrics_dir() -> Path:
    raw = os.getenv("HEALCHAIN_METRICS_DIR")
    return Path(raw).expanduser().resolve() if raw else _default_metrics_dir()


def record_metric_event(
    *,
    component: str,
    task_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        metrics_dir = _metrics_dir()
        metrics_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp_unix": time.time(),
            "timestamp_iso": datetime.now().isoformat(timespec="milliseconds"),
            "component": component,
            "task_id": str(task_id),
            "event_type": event_type,
            "payload": payload or {},
        }
        out_path = metrics_dir / f"{component}_metrics.jsonl"
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    except Exception:
        return
