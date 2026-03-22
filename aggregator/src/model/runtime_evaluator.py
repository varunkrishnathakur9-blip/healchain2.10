"""
Runtime evaluator hook wiring for strict accuracy evaluation.

This module provides two evaluator sources:
1) A pluggable Python hook (AGGREGATOR_EVALUATOR_HOOK=module:function)
2) A built-in sparse binary evaluator backed by a validation dataset file
   (AGGREGATOR_VALIDATION_DATA_PATH / AGGREGATOR_VALIDATION_DATA_LINK).
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

import requests

from utils.logging import get_logger

logger = get_logger("model.runtime_evaluator")

VALIDATION_CACHE_DIR = Path(
    os.getenv(
        "VALIDATION_CACHE_DIR",
        Path(os.getenv("MODEL_ARTIFACT_DIR", "./artifacts")) / "validation_cache",
    )
)
VALIDATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_ipfs_link(link: str) -> str:
    if not link.startswith("ipfs://"):
        return link
    cid_path = link[len("ipfs://") :]
    gateway = os.getenv("IPFS_GATEWAY_URL", "http://127.0.0.1:8080/ipfs").rstrip("/")
    if gateway.endswith("/ipfs"):
        return f"{gateway}/{cid_path}"
    return f"{gateway}/ipfs/{cid_path}"


def _resolve_validation_source(task_details: Optional[Dict[str, Any]]) -> Optional[str]:
    env_path = (os.getenv("AGGREGATOR_VALIDATION_DATA_PATH") or "").strip()
    if env_path:
        return env_path

    env_link = (os.getenv("AGGREGATOR_VALIDATION_DATA_LINK") or "").strip()
    if env_link:
        return env_link

    if not task_details:
        return None

    for key in (
        "validationDataLink",
        "validationDatasetLink",
        "validationSetLink",
        "validationLink",
    ):
        val = task_details.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _download_validation_data(task_id: str, source: str) -> Path:
    normalized = _normalize_ipfs_link(source.strip())
    lower = normalized.lower()
    ext = ".jsonl" if ".jsonl" in lower else ".json"
    out_path = VALIDATION_CACHE_DIR / f"{task_id}_validation{ext}"

    if normalized.startswith(("http://", "https://")):
        resp = requests.get(normalized, timeout=60)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        logger.info(f"[Evaluator] Validation dataset downloaded to {out_path}")
        return out_path

    local_path = Path(normalized)
    if not local_path.exists():
        raise FileNotFoundError(f"Validation dataset source not reachable: {source}")
    return local_path


def _normalize_sparse_sample(sample: Dict[str, Any]) -> Tuple[int, list[int], list[float]]:
    label = sample.get("label")
    if label is None:
        raise ValueError("Validation sample missing 'label'")
    label_int = int(label)
    if label_int not in (0, 1):
        raise ValueError(f"Validation label must be 0/1, got: {label_int}")

    indices_raw = sample.get("indices")
    if not isinstance(indices_raw, list) or not indices_raw:
        raise ValueError("Validation sample 'indices' must be a non-empty list")
    indices = [int(i) for i in indices_raw]
    if any(i < 0 for i in indices):
        raise ValueError("Validation sample indices must be >= 0")

    values_raw = sample.get("values")
    if values_raw is None:
        values = [1.0] * len(indices)
    else:
        if not isinstance(values_raw, list):
            raise ValueError("Validation sample 'values' must be a list")
        values = [float(v) for v in values_raw]
    if len(values) != len(indices):
        raise ValueError("Validation sample 'indices' and 'values' length mismatch")

    return label_int, indices, values


def _iter_sparse_samples(path: Path) -> Iterator[Tuple[int, list[int], list[float]]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except Exception as e:
                    raise ValueError(f"Invalid JSONL at line {lineno}") from e
                if not isinstance(payload, dict):
                    raise ValueError(f"Validation JSONL line {lineno} must be an object")
                yield _normalize_sparse_sample(payload)
        return

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        samples = payload.get("samples")
    else:
        samples = payload
    if not isinstance(samples, list):
        raise ValueError("Validation JSON must be a list or object with 'samples'")

    for idx, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"Validation sample at index {idx} must be an object")
        yield _normalize_sparse_sample(sample)


class SparseBinaryVectorEvaluator:
    """
    Evaluates a flattened vector model against sparse binary-labeled samples.

    Prediction rule:
      pred = 1 if dot(w, x) >= threshold else 0
    """

    def __init__(self, dataset_path: Path, threshold: float = 0.0):
        self.dataset_path = dataset_path
        self.threshold = float(threshold)
        self._preflight()

    def _preflight(self):
        count = 0
        for _ in _iter_sparse_samples(self.dataset_path):
            count += 1
            if count >= 1:
                break
        if count == 0:
            raise ValueError("Validation dataset has no samples")

    def __call__(self, model: Any) -> float:
        if not hasattr(model, "get_weights"):
            raise TypeError("Model missing get_weights() for runtime evaluator")
        weights = model.get_weights()
        if not isinstance(weights, list):
            raise TypeError("Model get_weights() must return a list for sparse evaluator")

        total = 0
        correct = 0
        wlen = len(weights)

        for label, indices, values in _iter_sparse_samples(self.dataset_path):
            score = 0.0
            for i, v in zip(indices, values):
                if i >= wlen:
                    raise ValueError(
                        f"Validation index {i} out of range for model length {wlen}"
                    )
                score += float(weights[i]) * float(v)
            pred = 1 if score >= self.threshold else 0
            correct += int(pred == label)
            total += 1

        if total == 0:
            raise ValueError("Validation dataset has no samples")
        return correct / total


def _build_python_hook(
    spec: str,
    *,
    task_id: str,
    task_details: Optional[Dict[str, Any]],
) -> Callable[[Any], float]:
    if ":" not in spec:
        raise ValueError(
            "AGGREGATOR_EVALUATOR_HOOK must be 'module.submodule:function_name'"
        )
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name.strip())
    fn = getattr(module, func_name.strip(), None)
    if fn is None or not callable(fn):
        raise ValueError(f"Evaluator hook is not callable: {spec}")

    def _wrapped(model: Any) -> float:
        try:
            return float(fn(model=model, task_id=task_id, task_details=task_details))
        except TypeError:
            # Backward-compatible simpler signatures.
            try:
                return float(fn(model, task_id, task_details))
            except TypeError:
                return float(fn(model))

    return _wrapped


def build_runtime_evaluator(
    *,
    task_id: str,
    task_details: Optional[Dict[str, Any]],
) -> Tuple[Optional[Callable[[Any], float]], Optional[str]]:
    """
    Build runtime evaluator callable + source label.
    """
    hook_spec = (os.getenv("AGGREGATOR_EVALUATOR_HOOK") or "").strip()
    if hook_spec:
        evaluator = _build_python_hook(
            hook_spec,
            task_id=task_id,
            task_details=task_details,
        )
        return evaluator, f"python_hook:{hook_spec}"

    source = _resolve_validation_source(task_details)
    if not source:
        return None, None

    path = _download_validation_data(task_id=task_id, source=source)
    threshold = float(os.getenv("AGGREGATOR_VALIDATION_THRESHOLD", "0.0"))
    evaluator = SparseBinaryVectorEvaluator(path, threshold=threshold)
    return evaluator, f"sparse_binary:{path}"

