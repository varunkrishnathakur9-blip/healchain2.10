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
    return load_real_local_dataset(str(LOCAL_DATA_DIR), dataset_type)

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

    first = True
    def generator():
        for img_file in image_files:
            img = np.load(img_file).astype(np.float32)
            # Transpose if channel-first (1, 64, 64) to channel-last (64, 64, 1)
            if img.shape == (1, 64, 64):
                img = np.transpose(img, (1, 2, 0))
            # If model expects 3 channels, convert grayscale to RGB
            if img.shape == (64, 64, 1):
                img = np.repeat(img, 3, axis=-1)  # (64, 64, 3)
            # Resize to (224, 224, 3)
            img = tf.image.resize(img, (224, 224)).numpy()
            label = labels_dict.get(img_file.stem)
            nonlocal first
            if first:
                print(f"[DEBUG] Yielding image shape: {img.shape}, label: {label}")
                first = False
            yield img, label

    output_signature = (
        tf.TensorSpec(shape=(224, 224, 3), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int64)
    )

    dataset = tf.data.Dataset.from_generator(generator, output_signature=output_signature)
    dataset = dataset.shuffle(buffer_size=min(1000, len(image_files))).batch(16).prefetch(tf.data.AUTOTUNE)
    print(f"[Dataset] Using generator for {len(image_files)} samples from {dataset_type}")
    return dataset
