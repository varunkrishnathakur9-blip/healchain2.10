import numpy as np
import json
import os
from pathlib import Path

# Define paths
LOCAL_DATA_DIR = Path(__file__).parent.parent / "local_data"
DATASET_TYPE = "chestxray"
DATA_DIR = LOCAL_DATA_DIR / DATASET_TYPE
IMAGES_DIR = DATA_DIR / "images"

def generate_sample_data(num_samples=20):
    """
    Generate sample data for testing real training.
    """
    print(f"Generating {num_samples} sample images in {IMAGES_DIR}...")
    
    # Create directories
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    labels = {}
    
    for i in range(num_samples):
        # Create dummy image data (flattened 10-feature vector as used in model.py)
        # In a real scenario, this would be a 2D image array
        img_data = np.random.randn(10).astype(np.float32)
        
        filename = f"sample_{i:04d}.npy"
        filepath = IMAGES_DIR / filename
        
        # Save .npy file
        np.save(filepath, img_data)
        
        # Assign random label (0 or 1)
        labels[f"sample_{i:04d}"] = np.random.randint(0, 2)
        
    # Save labels.json
    labels_path = DATA_DIR / "labels.json"
    with open(labels_path, "w") as f:
        json.dump(labels, f, indent=2)
        
    print(f"✅ Generated {num_samples} samples.")
    print(f"Labels saved to {labels_path}")
    print("\nYou can now run training and it will pick up this data!")

if __name__ == "__main__":
    generate_sample_data()
