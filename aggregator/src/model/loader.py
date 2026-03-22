"""
HealChain Aggregator - Base Model Loader

Loads the current global model from task metadata links.
Supports:
- Aggregator JSON artifact format {"weights": [...], "num_parameters": ...}
- Keras H5/KERAS checkpoint files (flattened to vector) when h5py is available
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from utils.logging import get_logger
from model.vector_model import VectorModel

logger = get_logger("model.loader")

MODEL_CACHE_DIR = Path(
    os.getenv("MODEL_CACHE_DIR", Path(os.getenv("MODEL_ARTIFACT_DIR", "./artifacts")) / "cache")
)
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_ipfs_link(link: str) -> str:
    if not link.startswith("ipfs://"):
        return link
    cid_path = link[len("ipfs://") :]
    gateway = os.getenv("IPFS_GATEWAY_URL", "http://127.0.0.1:8080/ipfs").rstrip("/")
    if gateway.endswith("/ipfs"):
        return f"{gateway}/{cid_path}"
    return f"{gateway}/ipfs/{cid_path}"


def _download_to_cache(task_id: str, model_link: str) -> Path:
    normalized = _normalize_ipfs_link(model_link)
    ext = os.path.splitext(normalized.split("?", 1)[0])[1].lower()
    if ext not in {".json", ".h5", ".keras"}:
        ext = ".bin"
    out_path = MODEL_CACHE_DIR / f"{task_id}_base_model{ext}"

    if normalized.startswith(("http://", "https://")):
        try:
            resp = requests.get(normalized, timeout=60)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            logger.info(f"[ModelLoader] Downloaded base model to {out_path}")
            return out_path
        except Exception as e:
            # Fallback for links like:
            # https://<cid>.ipfs.dweb.link?filename=...
            parsed = urlparse(normalized)
            host = parsed.netloc.lower()
            if host.endswith(".ipfs.dweb.link"):
                cid = host.split(".ipfs.dweb.link", 1)[0]
                gateway = os.getenv("IPFS_GATEWAY_URL", "http://127.0.0.1:8080/ipfs").rstrip("/")
                if gateway.endswith("/ipfs"):
                    fallback = f"{gateway}/{cid}"
                else:
                    fallback = f"{gateway}/ipfs/{cid}"
                logger.warning(
                    f"[ModelLoader] Primary download failed ({e}); retrying via local IPFS gateway: {fallback}"
                )
                resp2 = requests.get(fallback, timeout=60)
                resp2.raise_for_status()
                out_path.write_bytes(resp2.content)
                logger.info(f"[ModelLoader] Downloaded base model via local gateway to {out_path}")
                return out_path
            raise

    # Local filesystem path
    p = Path(normalized)
    if not p.exists():
        raise FileNotFoundError(f"Base model link is not reachable: {model_link}")
    return p


def _load_json_vector_model(path: Path, static_accuracy: Optional[float]) -> VectorModel:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict) or "weights" not in payload:
        raise ValueError("Model JSON must be an object with 'weights' field")
    weights = payload.get("weights")
    if not isinstance(weights, list):
        raise ValueError("Model JSON field 'weights' must be a list")
    return VectorModel(weights, static_accuracy=static_accuracy)


def _load_h5_vector_model(path: Path, static_accuracy: Optional[float]) -> VectorModel:
    try:
        import h5py  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "h5py is required to load .h5/.keras base models in aggregator. "
            "Install with: pip install h5py"
        ) from e

    flat_weights = []
    with h5py.File(path, "r") as f:
        root = f["model_weights"] if "model_weights" in f else f

        # Preferred deterministic Keras ordering.
        layer_names = root.attrs.get("layer_names")
        if layer_names is not None:
            for lname_raw in layer_names:
                lname = lname_raw.decode() if isinstance(lname_raw, (bytes, bytearray)) else str(lname_raw)
                if lname not in root:
                    continue
                layer_group = root[lname]
                weight_names = layer_group.attrs.get("weight_names", [])
                for wname_raw in weight_names:
                    wname = (
                        wname_raw.decode() if isinstance(wname_raw, (bytes, bytearray)) else str(wname_raw)
                    )
                    if wname not in layer_group:
                        continue
                    arr = layer_group[wname][()]
                    try:
                        flat_weights.extend(arr.reshape(-1).astype("float64").tolist())
                    except Exception:
                        # Defensive fallback
                        flat_weights.extend([float(x) for x in arr.reshape(-1)])
        else:
            # Generic deterministic traversal fallback.
            def _visit(name, obj):
                if hasattr(obj, "shape") and callable(getattr(obj, "__getitem__", None)):
                    arr = obj[()]
                    try:
                        flat_weights.extend(arr.reshape(-1).astype("float64").tolist())
                    except Exception:
                        flat_weights.extend([float(x) for x in arr.reshape(-1)])

            root.visititems(_visit)

    if not flat_weights:
        raise ValueError(f"No weights found in model file: {path}")

    logger.info(f"[ModelLoader] Loaded {len(flat_weights)} flattened weights from {path.name}")
    return VectorModel(flat_weights, static_accuracy=static_accuracy)


def load_base_model_from_link(
    *,
    task_id: str,
    model_link: str,
    static_accuracy: Optional[float] = None,
) -> VectorModel:
    """
    Load base model from task initial/current model link.
    """
    if not model_link or not str(model_link).strip():
        raise ValueError("Model link is empty")

    model_path = _download_to_cache(task_id, model_link.strip())
    suffix = model_path.suffix.lower()

    if suffix == ".json":
        return _load_json_vector_model(model_path, static_accuracy=static_accuracy)
    if suffix in {".h5", ".keras"}:
        return _load_h5_vector_model(model_path, static_accuracy=static_accuracy)

    # Try JSON first, then H5 parsing.
    try:
        return _load_json_vector_model(model_path, static_accuracy=static_accuracy)
    except Exception:
        return _load_h5_vector_model(model_path, static_accuracy=static_accuracy)
