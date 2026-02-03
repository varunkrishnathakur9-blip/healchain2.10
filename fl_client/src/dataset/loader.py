import tensorflow as tf
from pathlib import Path
import json
import numpy as np

LOCAL_DATA_DIR = Path(__file__).parent.parent.parent / "local_data"

def load_local_dataset(dataset_type: str = "chestxray"):
    """
    Load local dataset matching the task type.
    Tries real data first, falls back to structure dummy data.
    Returns a tf.data.Dataset object.
    """
    try:
        return load_real_local_dataset(str(LOCAL_DATA_DIR), dataset_type)
    except Exception as e:
        print(f"[Dataset] Real data not found ({e}), falling back to synthetic data")

    # Temporary: Structured dummy data that matches task
    if dataset_type == "chestxray":
        # 100 samples of chest X-ray features (simplified)
        X = np.random.randn(100, 10).astype(np.float32)  # 10-dimensional feature vector
        y = np.random.randint(0, 2, 100).astype(np.int64)  # Binary classification
        batch_size = 16
    else:
        # Default for other tasks
        X = np.random.randn(100, 10).astype(np.float32)
        y = np.random.randint(0, 2, 100).astype(np.int64)
        batch_size = 16
    
    dataset = tf.data.Dataset.from_tensor_slices((X, y))
    return dataset.shuffle(buffer_size=len(X)).batch(batch_size)

def load_real_local_dataset(dataset_path: str, dataset_type: str):
    """
    Load REAL local dataset from disk.
    
    Expected structure:
    local_data/
    ├── chestxray/
    │   ├── images/
    │   │   ├── sample_0001.npy
    │   │   └── ...
    │   └── labels.json
    
    Returns:
        A tf.data.Dataset object.
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
        img = np.load(img_file).astype(np.float32)
        # Transpose if channel-first (1, 64, 64) to channel-last (64, 64, 1)
        if img.shape == (1, 64, 64):
            img = np.transpose(img, (1, 2, 0))
        # If model expects 3 channels, convert grayscale to RGB
        if img.shape == (64, 64, 1):
            img = np.repeat(img, 3, axis=-1)  # (64, 64, 3)
        X.append(img)

        label = labels_dict.get(img_file.stem)
        y.append(label)
    

    X = np.array(X)
    y = np.array(y, dtype=np.int64)

    # Ensure images are (num_samples, 64, 64, 3) for RGB models
    if X.ndim == 4 and X.shape[-1] == 1:
        X = np.repeat(X, 3, axis=-1)

    print(f"[Dataset] Loaded {len(X)} samples from {dataset_type}")

    dataset = tf.data.Dataset.from_tensor_slices((X, y))
    return dataset.shuffle(buffer_size=len(X)).batch(16)
