import torch
import sys
import os
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.append(str(SRC_DIR))

try:
    from model.h5_adapter import load_h5_weights
    
    MODELS_DIR = Path(__file__).parent.parent / "models"
    h5_path = MODELS_DIR / "task_027_initial.h5"
    
    print(f"Testing H5 load from: {h5_path}")
    model = load_h5_weights(h5_path)
    print("✅ Model loaded successfully!")
    print(f"Model Class: {type(model).__name__}")
    
    # Try a forward pass with dummy data
    print("Testing forward pass...")
    dummy_input = torch.randn(1, 1, 64, 64)
    out = model(dummy_input)
    print(f"✅ Forward pass successful. Output: {out.shape}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
