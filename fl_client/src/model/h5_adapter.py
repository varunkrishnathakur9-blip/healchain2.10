import torch
import torch.nn as nn
import h5py
import numpy as np
from pathlib import Path
from training.model import SimpleCNN, ResNet9, SimpleModel

def load_h5_weights(h5_path, target_model_class=None):
    """
    Load weights from Keras H5 file into a compatible PyTorch model.
    """
    h5_path = Path(h5_path)
    if not h5_path.exists():
        raise FileNotFoundError(f"H5 file not found: {h5_path}")
        
    print(f"[Model] Loading Keras H5 from: {h5_path}")
    
    weights_dict = {}
    
    try:
        with h5py.File(h5_path, 'r') as f:
            def collector(name, obj):
                if isinstance(obj, h5py.Dataset):
                    # We look for kernel/weights and bias
                    if 'kernel' in name or 'weights' in name:
                        weights_dict[name] = np.array(obj)
                    elif 'bias' in name:
                        weights_dict[name] = np.array(obj)
            
            f.visititems(collector)
            
        print(f"[Model] Found {len(weights_dict)} weight tensors in H5")
        
        # Heuristic to choose model architecture if not specified
        # based on weight shapes
        if target_model_class is None:
            has_conv = any(len(w.shape) == 4 for w in weights_dict.values())
            has_deep_resnet = len(weights_dict) > 20 # ResNet9 has many layers
            
            if has_deep_resnet:
                print("[Model] Detected complex structure -> Attempting ResNet9")
                model = ResNet9()
            elif has_conv:
                print("[Model] Detected Conv layers -> Attempting SimpleCNN")
                model = SimpleCNN()
            else:
                print("[Model] Detected only Linear -> Attempting SimpleModel")
                model = SimpleModel()
        else:
            model = target_model_class()
            
        # Map weights
        # This is a naive heuristic mapping: we assume layers are stored in order
        # and we map them to PyTorch list of parameters in order.
        
        # Get PyTorch parameters that need weights (skip BN running stats for now?)
        # Actually BN has weights (gamma/beta) which map to kernel/bias? Keras calls them gamma/beta.
        pt_params = list(model.named_parameters())
        pt_param_idx = 0
        
        # Sort H5 keys to try and match layer order
        # Keras keys properties: model_weights/dense_1/dense_1/kernel:0
        # Sorting by name gives some order but maybe not perfect.
        sorted_keys = sorted(weights_dict.keys())
        
        with torch.no_grad():
            for key in sorted_keys:
                w_np = weights_dict[key]
                if pt_param_idx >= len(pt_params):
                    break
                    
                pt_name, pt_param = pt_params[pt_param_idx]
                
                # Check for shape match compatibility
                # Keras Conv: (H, W, In, Out) -> PyTorch: (Out, In, H, W)
                if len(w_np.shape) == 4 and len(pt_param.shape) == 4:
                    # Check if standard transpose works
                    w_t = np.transpose(w_np, (3, 2, 0, 1))
                    if w_t.shape == pt_param.shape:
                        pt_param.copy_(torch.tensor(w_t))
                        print(f"  Mapped {key} ({w_np.shape}) -> {pt_name} {pt_param.shape}")
                        pt_param_idx += 1
                        continue
                        
                # Keras Dense: (In, Out) -> PyTorch: (Out, In)
                if len(w_np.shape) == 2 and len(pt_param.shape) == 2:
                    w_t = w_np.T
                    if w_t.shape == pt_param.shape:
                        pt_param.copy_(torch.tensor(w_t))
                        print(f"  Mapped {key} ({w_np.shape}) -> {pt_name} {pt_param.shape}")
                        pt_param_idx += 1
                        continue
                        
                # 1D (Bias/BN): Match directly
                if len(w_np.shape) == 1 and len(pt_param.shape) == 1:
                    if w_np.shape == pt_param.shape:
                        pt_param.copy_(torch.tensor(w_np))
                        print(f"  Mapped {key} ({w_np.shape}) -> {pt_name} {pt_param.shape}")
                        pt_param_idx += 1
                        continue
        
        print(f"[Model] Successfully mapped {pt_param_idx}/{len(pt_params)} parameters")
        if pt_param_idx < len(pt_params):
             print("[Model] Warning: Partial mapping. Some layers initialized randomly.")
             
        return model

    except Exception as e:
        print(f"[Model] H5 Loading failed: {e}")
        raise e
