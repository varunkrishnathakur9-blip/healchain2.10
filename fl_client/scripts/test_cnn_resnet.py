import sys
import os
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.append(str(SRC_DIR))

import torch
from training.model import SimpleCNN, ResNet9, SimpleModel
from dataset.loader import load_local_dataset

def test_models():
    print("Testing Model Architectures...")
    
    # 1. Test SimpleCNN
    print("\n[Test] SimpleCNN")
    cnn = SimpleCNN()
    x = torch.randn(2, 1, 64, 64) # Batch of 2, 64x64 grayscale
    try:
        out = cnn(x)
        print(f"✅ Forward pass successful. Output shape: {out.shape}")
        if out.shape == (2, 2):
            print("✅ Output shape correct (Batch=2, Classes=2)")
        else:
            print(f"❌ Output shape mismatch: {out.shape}")
    except Exception as e:
        print(f"❌ Forward pass failed: {e}")

    # 2. Test ResNet9
    print("\n[Test] ResNet9")
    resnet = ResNet9()
    try:
        out = resnet(x)
        print(f"✅ Forward pass successful. Output shape: {out.shape}")
        if out.shape == (2, 2):
            print("✅ Output shape correct")
        else:
            print(f"❌ Output shape mismatch: {out.shape}")
    except Exception as e:
        print(f"❌ Forward pass failed: {e}")

    # 3. Test SimpleModel (Linear) Compatibility with 2D input
    print("\n[Test] SimpleModel (Linear) with 2D input")
    linear = SimpleModel()
    try:
        out = linear(x) # Should auto-flatten
        print(f"✅ Forward pass successful (Auto-flatten). Output shape: {out.shape}")
        if out.shape == (2, 2):
            print("✅ Output shape correct")
        else:
            print(f"❌ Output shape mismatch: {out.shape}")
    except Exception as e:
        print(f"❌ Forward pass failed: {e}")

if __name__ == "__main__":
    test_models()
