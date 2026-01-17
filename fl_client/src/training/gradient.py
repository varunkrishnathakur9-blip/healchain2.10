import torch

def validate_gradient_bounds(grads, max_magnitude):
    """Ensure gradients are within safe bounds for quantization."""
    max_val = grads.abs().max().item()
    if max_val > max_magnitude:
        raise ValueError(f"Gradient magnitude {max_val} exceeds bound {max_magnitude}")
    return grads

def compute_gradient(model):
    grads = []
    for p in model.parameters():
        grads.append(p.grad.flatten())
    flat_grads = torch.cat(grads)
    
    # Validate bounds for BSGS compatibility
    from config.gradient_bounds import MAX_GRAD_MAGNITUDE
    validate_gradient_bounds(flat_grads, MAX_GRAD_MAGNITUDE)
    
    return flat_grads
