import h5py
import sys
import numpy as np
from pathlib import Path

def inspect_h5(path):
    print(f"Inspecting: {path}")
    try:
        with h5py.File(path, 'r') as f:
            def print_attrs(name, obj):
                if isinstance(obj, h5py.Dataset):
                    if "optimizer_weights" in name:
                        return
                    print(f"  {name}: {obj.shape}")
            
            f.visititems(print_attrs)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    MODELS_DIR = Path(__file__).parent.parent / "models"
    h5_path = MODELS_DIR / "task_027_initial.h5"
    if len(sys.argv) > 1:
        h5_path = sys.argv[1]
        
    inspect_h5(h5_path)
