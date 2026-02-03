import requests
import torch
import os
from pathlib import Path

# Define models directory relative to this file
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

def download_initial_model(task_id: str, model_url: str):
    """
    Download initial model from task publisher.
    
    Args:
        task_id: Task identifier
        model_url: URL or IPFS hash of the model
    
    Returns:
        model: PyTorch model loaded from checkpoint
    """
    import os
    # Determine extension from URL
    ext = os.path.splitext(model_url)[-1].lower()
    if ext not in [".h5", ".keras", ".pt"]:
        ext = ".h5"  # Default to .h5 if unknown

    model_path = MODELS_DIR / f"{task_id}_initial{ext}"
    h5_path = MODELS_DIR / f"{task_id}_initial.h5"

    # Priority 1: Check for manual .h5 file (User override)
    if h5_path.exists():
        print(f"[Model] Found local H5 override: {h5_path}")
        from training.model import load_model_checkpoint
        return load_model_checkpoint(h5_path)

    # Priority 2: Check for cached file
    if model_path.exists():
        print(f"[Model] Loading cached model: {model_path}")
        if ext in [".h5", ".keras"]:
            from training.model import load_model_checkpoint
            return load_model_checkpoint(model_path)
        elif ext == ".pt":
            import torch
            return torch.load(model_path)
        else:
            raise ValueError(f"Unsupported model file extension: {ext}")

    print(f"[Model] Downloading from: {model_url}")

    try:
        response = requests.get(model_url, timeout=30)
        response.raise_for_status()
        # Save to cache
        with open(model_path, 'wb') as f:
            f.write(response.content)
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
    
    # Try model URL first
    if "modelURL" in task:
        return download_initial_model(task_id, task["modelURL"])
    
    # Try initialModelLink (backend standard)
    if "initialModelLink" in task and task["initialModelLink"]:
        return download_initial_model(task_id, task["initialModelLink"])
    
    # Try IPFS hash
    if "modelIPFSHash" in task:
        ipfs_hash = task["modelIPFSHash"]
        # Construct IPFS gateway URL
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        return download_initial_model(task_id, ipfs_url)
    
    raise ValueError(f"Task {task_id} has no model URL or IPFS hash")
