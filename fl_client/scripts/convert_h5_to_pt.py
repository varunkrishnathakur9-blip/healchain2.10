import torch
import torch.nn as nn
import h5py
import numpy as np
import sys
from pathlib import Path

# Define PyTorch Architecture (Must match Keras model structure physically)
class SimpleModel(nn.Module):
    def __init__(self, input_features=4096, output_classes=2):
        super().__init__()
        self.fc = nn.Linear(input_features, output_classes)
    
    def forward(self, x):
        return self.fc(x)

def convert_h5_to_pt(h5_path, output_path=None):
    h5_path = Path(h5_path)
    if not h5_path.exists():
        print(f"❌ File not found: {h5_path}")
        return

    if output_path is None:
        # Default output name: task_027_initial.pt
        output_path = h5_path.parent / "task_027_initial.pt"
    
    print(f"Converting {h5_path} to PyTorch format...")
    
    try:
        # Load weights from H5
        with h5py.File(h5_path, 'r') as f:
            # Inspection helper (uncomment to see structure)
            # def print_structure(name, obj):
            #     print(name)
            # f.visititems(print_structure)
            
            # Assuming standard Keras save format (files may vary!)
            # We look for the kernel (weights) and bias of the Dense layer
            
            # Note: This path depends heavily on how the H5 was saved.
            # Common path: model_weights -> dense -> dense -> kernel:0
            
            # Heuristic search for weights
            weights = None
            bias = None
            
            print("Inspecting H5 file structure:")
            def find_weights(name, obj):
                nonlocal weights, bias
                if isinstance(obj, h5py.Dataset):
                    # Skip scalar/empty datasets
                    if len(obj.shape) == 0:
                        return
                        
                    print(f"  - Found dataset: {name}, Shape: {obj.shape}")
                    
                    if 'kernel' in name or 'weights' in name:
                        # Check if it looks like our weights (either 4096x2 or 2x4096)
                        if (len(obj.shape) == 2):
                            if (obj.shape[0] == 4096 and obj.shape[1] == 2):
                                print(f"    -> MATCH: Weights found (Keras format)")
                                weights = np.array(obj)
                            elif (obj.shape[0] == 2 and obj.shape[1] == 4096):
                                print(f"    -> MATCH: Weights found (PyTorch format)")
                                weights = np.array(obj).T # Transpose to match Keras shape expectation for later logic
                    
                    if 'bias' in name:
                         if (len(obj.shape) == 1 and obj.shape[0] == 2):
                            print(f"    -> MATCH: Bias found")
                            bias = np.array(obj)
            
            f.visititems(find_weights)
            
            if weights is None or bias is None:
                print("❌ Could not find expected weights (4096x2) or bias (2) in H5 file.")
                print("This script assumes a simple Dense(2, input_dim=4096) layer.")
                return

            # Convert to PyTorch (Transpose weights because Keras is (In, Out), PyTorch is (Out, In))
            pt_weights = torch.tensor(weights.T).float()
            pt_bias = torch.tensor(bias).float()
            
            # Create PyTorch model
            model = SimpleModel()
            
            # Load weights
            with torch.no_grad():
                model.fc.weight.copy_(pt_weights)
                model.fc.bias.copy_(pt_bias)
            
            # Save as valid .pt file
            torch.save(model, output_path)
            print(f"✅ Conversion successful!")
            print(f"Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        # Fallback: Generate fresh random model if conversion fails but user needs to proceed
        print("💡 Suggestion: If strict conversion fails, you can generate a fresh PyTorch model using scripts/generate_initial_model.py")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_h5_to_pt.py <path_to_model.h5>")
    else:
        convert_h5_to_pt(sys.argv[1])
