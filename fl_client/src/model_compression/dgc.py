import torch

def dgc_compress(grad, threshold=0.9, max_magnitude=None):
    """
    Gradient compression with DGC (Deep Gradient Compression).
    
    Args:
        grad: Input gradient tensor
        threshold: Sparsity threshold (0.9 = keep 10% largest gradients)
        max_magnitude: Optional bound for gradient clipping
    
    Returns:
        Compressed gradient tensor
    """
    # Apply gradient clipping if bound provided
    if max_magnitude is not None:
        grad = torch.clamp(grad, -max_magnitude, max_magnitude)
    
    flat = grad.flatten()
    k = int(len(flat) * (1 - threshold))
    _, idx = torch.topk(torch.abs(flat), k)
    mask = torch.zeros_like(flat)
    mask[idx] = flat[idx]
    return mask.reshape(grad.shape)
