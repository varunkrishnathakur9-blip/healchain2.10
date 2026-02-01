import torch
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import json
import numpy as np

LOCAL_DATA_DIR = Path(__file__).parent.parent.parent / "local_data"

def load_local_dataset(dataset_type: str = "chestxray"):
    """
    Load local dataset matching the task type.
    Tries real data first, falls back to structure dummy data.
    """
    # Try loading real data first
    try:
        return load_real_local_dataset(str(LOCAL_DATA_DIR), dataset_type)
    except Exception as e:
        print(f"[Dataset] Real data not found ({e}), falling back to synthetic data")

    # Temporary: Structured dummy data that matches task
    if dataset_type == "chestxray":
        # 100 samples of chest X-ray features (simplified)
        X = torch.randn(100, 10)  # 10-dimensional feature vector
        y = torch.randint(0, 2, (100,))  # Binary classification
        batch_size = 16
    else:
        # Default for other tasks
        X = torch.randn(100, 10)
        y = torch.randint(0, 2, (100,))
        batch_size = 16
    
    return DataLoader(
        TensorDataset(X, y),
        batch_size=batch_size,
        shuffle=True
    )

def load_real_local_dataset(dataset_path: str, dataset_type: str):
    """
    Load REAL local dataset from disk.
    
    Expected structure:
    local_data/
    ├── chestxray/
    │   ├── images/
    │   │   ├── sample_0001.npy
    │   │   ├── sample_0002.npy
    │   │   └── ...
    │   └── labels.json
    │       {
    │         "sample_0001": 0,
    │         "sample_0002": 1,
    │         ...
    │       }
    
    Args:
        dataset_path: Path to local data directory
        dataset_type: Type of dataset (e.g., "chestxray")
    
    Returns:
        DataLoader with real local data
    """
    data_dir = Path(dataset_path) / dataset_type
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset not found: {data_dir}")
    
    # Load images
    images_dir = data_dir / "images"
    image_files = sorted(list(images_dir.glob("*.npy")))
    
    if not image_files:
        raise ValueError(f"No image files found in {images_dir}")
    
    # Load labels
    labels_file = data_dir / "labels.json"
    with open(labels_file) as f:
        labels_dict = json.load(f)
    
    # Load data into memory
    X = []
    y = []
    for img_file in image_files:
        img = torch.from_numpy(np.load(img_file)).float()
        X.append(img)
        
        label = labels_dict.get(img_file.stem)
        y.append(label)
    
    X = torch.stack(X)
    y = torch.tensor(y, dtype=torch.long)
    
    print(f"[Dataset] Loaded {len(X)} samples from {dataset_type}")
    
    return DataLoader(
        TensorDataset(X, y),
        batch_size=16,
        shuffle=True
    )
