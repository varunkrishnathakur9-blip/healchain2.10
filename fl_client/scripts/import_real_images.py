import os
import numpy as np
import json
from pathlib import Path
from PIL import Image
import sys

# Define paths
LOCAL_DATA_DIR = Path(__file__).parent.parent / "local_data"
DATASET_TYPE = "chestxray"
DATA_DIR = LOCAL_DATA_DIR / DATASET_TYPE
IMAGES_DIR = DATA_DIR / "images"

# Target Size (must match model input)
TARGET_SIZE = (64, 64)  # 64x64 = 4096 features

def process_images(source_dir):
    """
    Process images from source_dir and save as .npy in local_data.
    Recursively searches for images and uses folder names for labeling.
    """
    source = Path(source_dir)
    if not source.exists():
        print(f"❌ Source directory not found: {source}")
        return

    print(f"Processing images from {source}...")
    print(f"Target size: {TARGET_SIZE}")
    print(f"Destination: {IMAGES_DIR}")
    
    # Create directories
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    labels = {}
    count = 0
    
    # Supported extensions
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tif', '*.tiff']
    files = []
    for ext in extensions:
        # Recursive search using rglob
        files.extend(list(source.rglob(ext)) + list(source.rglob(ext.upper())))
    
    if not files:
        print(f"❌ No image files found in {source} (recursively)")
        return

    print(f"Found {len(files)} images. converting...")

    for img_path in files:
        try:
            # Load and preprocess
            with Image.open(img_path) as img:
                # Convert to grayscale
                img = img.convert('L')
                # Resize
                img = img.resize(TARGET_SIZE)
                # Convert to numpy array and normalize to [0, 1]
                img_data = np.array(img).astype(np.float32) / 255.0
                
                # Save as (1, 64, 64) instead of flattening
                # Add channel dimension
                img_data = np.expand_dims(img_data, axis=0)
                
                # Save as .npy
                # Combine parent folder and filename to be unique
                safe_name = f"{img_path.parent.name}_{img_path.stem}"
                filename = f"{safe_name}.npy"
                filepath = IMAGES_DIR / filename
                np.save(filepath, img_data)
                
                # Auto-labeling logic
                label = 0 # Default
                parent_name = img_path.parent.name.upper()
                
                if "PNEUMONIA" in parent_name:
                    label = 1
                elif "NORMAL" in parent_name:
                    label = 0
                else:
                    # Fallback or keep default
                    label = 0
                
                labels[safe_name] = label
                count += 1
                
                if count % 100 == 0:
                    print(f"Processed {count} images...", end='\r')
                
        except Exception as e:
            print(f"⚠️ Failed to process {img_path.name}: {e}")
            
    # Save labels.json
    labels_path = DATA_DIR / "labels.json"
    
    # If labels file exists, merge with new labels
    if labels_path.exists():
        try:
            with open(labels_path, 'r') as f:
                existing_labels = json.load(f)
            labels.update(existing_labels)
        except json.JSONDecodeError:
            pass # overwriting corrupt file
        
    with open(labels_path, "w") as f:
        json.dump(labels, f, indent=2)
        
    print(f"\n✅ Processed {count} images.")
    print(f"Labels saved to {labels_path}")
    print(f"Auto-labeling applied: NORMAL=0, PNEUMONIA=1")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_real_images.py <path_to_your_images>")
    else:
        process_images(sys.argv[1])
