import requests
import torch
import os
import json
from pathlib import Path

# Define models directory relative to this file
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def _parse_round(task: dict) -> int:
    """
    Best-effort round extraction from task metadata.
    Defaults to round 1 when missing.
    """
    try:
        return int(task.get("currentRound") or task.get("round") or 1)
    except Exception:
        return 1


def _allow_local_override_for_round(round_no: int) -> bool:
    """
    Local H5 override is useful for round-1 bootstrapping, but must not shadow
    iterative retrain links for later rounds unless explicitly forced.
    """
    force_local = os.getenv("FL_FORCE_LOCAL_MODEL_OVERRIDE", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }
    if force_local:
        return True
    return round_no <= 1


def _load_sparse_json_artifact(task_id: str, artifact_bytes: bytes):
    """
    Load aggregator-published JSON artifact:
      {"weights":[...], "num_parameters":N}
    by applying flattened weights onto a local base checkpoint architecture.
    """
    payload = json.loads(artifact_bytes.decode("utf-8"))
    weights = payload.get("weights")
    if not isinstance(weights, list):
        raise ValueError("Invalid JSON model artifact: missing 'weights' list")

    h5_path = MODELS_DIR / f"{task_id}_initial.h5"
    if not h5_path.exists():
        raise FileNotFoundError(
            f"Cannot apply JSON artifact for {task_id}: base checkpoint not found at {h5_path}. "
            f"Place task bootstrap model there or enable an H5 modelLink."
        )

    from training.model import load_model_checkpoint
    model = load_model_checkpoint(h5_path)
    if not hasattr(model, "set_weights_custom"):
        raise TypeError("Loaded model wrapper missing set_weights_custom()")

    model.set_weights_custom(weights)
    print(
        f"[Model] Applied JSON artifact weights for {task_id} "
        f"(len={len(weights)}) on base checkpoint {h5_path}"
    )
    return model


def download_initial_model(task_id: str, model_url: str, *, round_no: int = 1):
    """
    Download initial model from task publisher.
    
    Args:
        task_id: Task identifier
        model_url: URL or IPFS hash of the model
        round_no: FL round number (used for override policy)
    
    Returns:
        model: PyTorch model loaded from checkpoint
    """
    import os
    # Determine extension from URL
    url_path = model_url.split("?", 1)[0]
    ext = os.path.splitext(url_path)[-1].lower()
    ext_defaulted = False
    if ext not in [".h5", ".keras", ".pt"]:
        ext = ".h5"  # Default to .h5 if unknown
        ext_defaulted = True

    model_path = MODELS_DIR / f"{task_id}_initial{ext}"
    h5_path = MODELS_DIR / f"{task_id}_initial.h5"

    # Priority 1: Check for manual .h5 file (User override)
    if h5_path.exists() and _allow_local_override_for_round(round_no):
        print(f"[Model] Found local H5 override: {h5_path}")
        from training.model import load_model_checkpoint
        return load_model_checkpoint(h5_path)
    elif h5_path.exists() and round_no > 1:
        print(
            f"[Model] Skipping local H5 override for round {round_no}; "
            f"using task-provided carried model link."
        )

    # Priority 2: Check for cached file
    if model_path.exists() and not (round_no > 1 and ext_defaulted):
        print(f"[Model] Loading cached model: {model_path}")
        if ext in [".h5", ".keras"]:
            from training.model import load_model_checkpoint
            return load_model_checkpoint(model_path)
        elif ext == ".pt":
            import torch
            return torch.load(model_path)
        else:
            raise ValueError(f"Unsupported model file extension: {ext}")
    elif model_path.exists() and round_no > 1 and ext_defaulted:
        print(
            f"[Model] Ignoring cached {model_path} for round {round_no} because model link has no file extension; "
            f"will fetch link content and detect artifact type."
        )

    print(f"[Model] Downloading from: {model_url}")

    try:
        response = requests.get(model_url, timeout=30)
        response.raise_for_status()

        content_type = (response.headers.get("content-type") or "").lower()
        body = response.content

        # Aggregator iterative artifacts are JSON payloads with flattened weights.
        # They may come from extension-less IPFS links, so we detect by content too.
        is_json_artifact = (
            "application/json" in content_type
            or model_url.lower().endswith(".json")
            or body.lstrip().startswith(b"{")
        )

        if is_json_artifact:
            json_path = MODELS_DIR / f"{task_id}_round{round_no}_artifact.json"
            with open(json_path, "wb") as f:
                f.write(body)
            print(f"[Model] Saved JSON artifact to: {json_path}")
            return _load_sparse_json_artifact(task_id, body)

        # Save to cache
        with open(model_path, 'wb') as f:
            f.write(body)
        print(f"[Model] Saved to: {model_path}")

        # Load and return
        if ext in [".h5", ".keras"]:
            from training.model import load_model_checkpoint
            return load_model_checkpoint(model_path)
        elif ext == ".pt":
            import torch
            return torch.load(model_path)
        else:
            raise ValueError(f"Unsupported model file extension: {ext}")
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        raise

def load_model_from_task(task: dict):
    """
    Load initial model from task metadata.
    Supports both IPFS hash and direct URL.
    """
    task_id = task.get("taskID")
    round_no = _parse_round(task)
    
    # Try model URL first
    if "modelURL" in task:
        return download_initial_model(task_id, task["modelURL"], round_no=round_no)
    
    # Try initialModelLink (backend standard)
    if "initialModelLink" in task and task["initialModelLink"]:
        return download_initial_model(task_id, task["initialModelLink"], round_no=round_no)
    
    # Try IPFS hash
    if "modelIPFSHash" in task:
        ipfs_hash = task["modelIPFSHash"]
        # Construct IPFS gateway URL
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        return download_initial_model(task_id, ipfs_url)
    
    raise ValueError(f"Task {task_id} has no model URL or IPFS hash")
