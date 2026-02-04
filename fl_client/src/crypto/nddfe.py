# crypto/nddfe.py
# =========================================
# HealChain NDD-FE (FL-Client / Miner Side)
# Implements Section 3.3 & Module M3
# Optimizations:
# 1. Zero-Skip (10x-100x speedup)
# 2. PyCryptodome (100x speedup vs tinyec)
# =========================================

from Crypto.PublicKey import ECC
from hashlib import sha256
import time

# ---- Curve parameters (secp256r1 aka P-256) ----
CURVE_NAME = 'P-256'
# G and N are accessible via ECC.EccPoint and ECC._curves if needed, 
# but we work with High Level Objects where possible.

# ---------- Utilities ----------

def _hash_to_scalar(*args: bytes) -> int:
    """Hash input to a scalar in the curve field (modulo N)."""
    h = sha256(b"".join(args)).digest()
    # Get curve order N for P-256
    # PyCryptodome 3.16+
    curve_order = int(ECC._curves['P-256'].order)
    return int.from_bytes(h, "big") % curve_order


def _point_to_bytes(pt) -> bytes:
    """Serialize point to bytes (x||y)."""
    # pt is an ECC.EccPoint
    # We want 32-byte BE integers.
    return int(pt.x).to_bytes(32, "big") + int(pt.y).to_bytes(32, "big")


def _point_to_hex(pt) -> str:
    """Serialize point to '0x...,0x...' hex format."""
    # Matches the legacy format: 0x<64-hex>,0x<64-hex>
    return f"0x{int(pt.x):064x},0x{int(pt.y):064x}"


def load_public_key(pubkey_hex: str):
    """
    Load public key from string 'x,y' or '0x...,0x...'. 
    Supports both Hex and Decimal inputs.
    Returns an ECC.EccPoint.
    """
    try:
        x_str, y_str = pubkey_hex.split(",")
        x_str = x_str.strip()
        y_str = y_str.strip()
        
        # Parse X
        if x_str.lower().startswith("0x"):
            x = int(x_str, 16)
        elif any(c in "abcdef" for c in x_str.lower()):
            x = int(x_str, 16)
        else:
            try:
                x = int(x_str)
            except ValueError:
                x = int(x_str, 16)

        # Parse Y
        if y_str.lower().startswith("0x"):
            y = int(y_str, 16)
        elif any(c in "abcdef" for c in y_str.lower()):
            y = int(y_str, 16)
        else:
            try:
                y = int(y_str)
            except ValueError:
                y = int(y_str, 16)
                     
        # Validate point is on curve by constructing a key
        # PyCryptodome validates on construction if we make a key, 
        # or we can just make a point.
        pt = ECC.EccPoint(x, y, curve=CURVE_NAME)
        return pt
    except Exception as e:
        raise ValueError(f"Failed to parse public key '{pubkey_hex}': {e}")


# ---------- Core NDD-FE Encryption ----------

def encrypt_update(
    delta_prime: list[int],
    *,
    pk_tp_hex: str,        # g^{s_TP}
    pk_agg_hex: str,       # g^{s_A}
    sk_miner: int,         # s_i
    ctr: int,
    task_id: str,
    progress_callback=None # Optional callback(percent, message)
):
    """
    Implements:
        U_i[j] = g^{r_i} * pk_A^{Δ'_i[j]}

    Args:
        delta_prime: Quantized gradient values
        pk_tp_hex: Trusted party public key
        pk_agg_hex: Aggregator public key
        sk_miner: Miner private key (int)
        ctr: Counter
        task_id: Task ID
    """
    
    # 1. Parse Public Keys (ECC.EccPoint)
    pk_tp = load_public_key(pk_tp_hex)
    pk_agg = load_public_key(pk_agg_hex)

    # 2. Derive Shared Secret / r_i
    # pk_tp^{s_i} = s_i * pk_tp
    # PyCryptodome supports Scalar * Point -> Point
    # Using Point * Scalar for safety against __rmul__ issues
    pk_tp_pow_si = pk_tp * sk_miner

    # r_i = H(pk_tp^{s_i} || ctr || task_id)
    ri = _hash_to_scalar(
        _point_to_bytes(pk_tp_pow_si),
        ctr.to_bytes(8, "big"),
        task_id.encode()
    )

    # 3. Base Mask: g^{r_i}
    # We need Generator Point G.
    G_x = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
    G_y = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
    G = ECC.EccPoint(G_x, G_y, curve=CURVE_NAME)

    base_mask = G * ri  # Point * Scalar
    base_mask_hex = _point_to_hex(base_mask)

    # 4. Encrypt Gradients
    ciphertext = []
    total_params = len(delta_prime)
    
    print(f"[Crypto] Encrypting {total_params} parameters using PyCryptodome...")
    
    # Sparsity Stats
    non_zeros = sum(1 for x in delta_prime if x != 0)
    sparsity = (1 - (non_zeros / total_params)) * 100
    print(f"[Crypto] Sparsity: {sparsity:.2f}% (Active Operations: {non_zeros})")
    
    log_interval = max(1, total_params // 100) # 1%

    for i, val in enumerate(delta_prime):
        # Progress Logging
        if i % log_interval == 0 and i > 0:
             percent = (i / total_params) * 100
             msg = f"[Crypto] Checkpoint: {percent:.1f}% ({i}/{total_params})"
             # print(msg, flush=True) # Reduce spam if callback handles it?
             # Let's verify callback usage
             if progress_callback:
                 progress_callback(percent, msg)
             else:
                 print(msg, flush=True)

        if val == 0:
            ciphertext.append(base_mask_hex)
            continue
            
        # Homomorphic Ops
        # Ui = base_mask + val * pk_agg
        
        # Note: val can be negative?
        # If val is negative, val * pk_agg works in PyCryptodome?
        # Usually scalars are unsigned.
        # If BSGS quantization guarantees positive integers?
        # delta_prime is from 'quantize_gradients'.
        # BSGS needs positive inputs?
        # If val < 0, mathematically: -val * pk_agg = val * (-pk_agg).
        # But usually we work in finite fields.
        # Check quantize_gradients.py. It clamps then casts to long. Could be negative.
        # If negative, 'val * Point' might fail if library expects unsigned scalar.
        # Solution: Use modulo arithmetic for scalar if needed, or check support.
        # PyCryptodome source: checks if scalar < 0.
        
        # Safety: dgc compression produces raw values. quantize_gradients scales them.
        # If val is negative, `val * pk_agg` should be `-abs(val) * pk_agg`.
        # PyCryptodome 3.x supports negative scalar mul?
        # If not, `(-val) * (-pk_agg)` or `N - val`.
        
        if val < 0:
             # Negate point (y -> -y mod p) then multiply by abs(val)
             # point negation: -P = (x, p-y)
             # PyCryptodome point negation: -point
             grad_term = (-pk_agg) * abs(val)
        else:
             grad_term = pk_agg * val

        Ui = base_mask + grad_term
        ciphertext.append(_point_to_hex(Ui))

    if progress_callback:
        progress_callback(100, "Encryption Complete")

    return ciphertext
