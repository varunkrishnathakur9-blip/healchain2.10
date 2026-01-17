import torch

def gradient_l2_norm(delta_prime, scale=None):
    """
    Compute L2 norm of gradients.
    
    Args:
        delta_prime: Gradient tensor (float or quantized int)
        scale: If provided, dequantize first (for quantized gradients)
    
    Returns:
        L2 norm as float
    """
    if scale is not None and delta_prime.dtype != torch.float32:
        # Dequantize for accurate norm computation
        delta_prime = delta_prime.float() / scale
    
    return torch.norm(delta_prime, p=2).item()
