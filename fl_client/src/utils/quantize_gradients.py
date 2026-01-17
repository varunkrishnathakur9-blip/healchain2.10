# Gradient Quantization Utilities
# ===============================
# Converts floating-point gradients to quantized integers for BSGS

import torch
from typing import Tuple
from config.gradient_bounds import QUANTIZATION_SCALE, MAX_QUANTIZED_VALUE


def quantize_gradients(grads: torch.Tensor, scale: int = QUANTIZATION_SCALE) -> Tuple[torch.Tensor, int]:
    """
    Convert float32 gradients to quantized int64 values.
    
    Args:
        grads: Float32 gradient tensor
        scale: Quantization scale factor
        
    Returns:
        Tuple of (quantized_grads, scale_used)
    """
    # Clamp to prevent overflow
    clamped_grads = torch.clamp(grads, -MAX_QUANTIZED_VALUE/scale, MAX_QUANTIZED_VALUE/scale)
    
    # Quantize to integers
    quantized = (clamped_grads * scale).long()
    
    return quantized, scale


def dequantize_gradients(quantized_grads: torch.Tensor, scale: int = QUANTIZATION_SCALE) -> torch.Tensor:
    """
    Convert quantized integers back to float32 gradients.
    
    Args:
        quantized_grads: Quantized integer tensor
        scale: Quantization scale factor
        
    Returns:
        Float32 gradient tensor
    """
    return quantized_grads.float() / scale


def validate_quantized_range(quantized_grads: torch.Tensor) -> bool:
    """
    Validate that quantized gradients are within safe bounds.
    
    Args:
        quantized_grads: Quantized gradient tensor
        
    Returns:
        True if within bounds, False otherwise
    """
    max_val = quantized_grads.abs().max().item()
    return max_val <= MAX_QUANTIZED_VALUE
