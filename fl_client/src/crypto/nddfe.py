# crypto/nddfe.py
# =========================================
# HealChain NDD-FE (FL-Client / Miner Side)
# Implements Section 3.3 & Module M3
# =========================================

from tinyec import registry
from tinyec.ec import Point
from hashlib import sha256

# ---- Curve parameters (matches aggregator) ----
curve = registry.get_curve("secp256r1")
G = curve.g
N = curve.field.n


# ---------- Utilities ----------

def _hash_to_scalar(*args: bytes) -> int:
    h = sha256(b"".join(args)).digest()
    return int.from_bytes(h, "big") % N


def _point_to_bytes(pt) -> bytes:
    return pt.x.to_bytes(32, "big") + pt.y.to_bytes(32, "big")


def _point_to_hex(pt) -> str:
    return f"{pt.x:064x},{pt.y:064x}"


def load_public_key(pubkey_hex: str):
    """
    Load public key from string. Supports both Hex and Decimal formats.
    pubkey_hex format: 'x,y' where x,y are hex strings (0x prefix optional) or decimal strings.
    """
    try:
        x_str, y_str = pubkey_hex.split(",")
        x_str = x_str.strip()
        y_str = y_str.strip()
        
        # Heuristic: Check if hex or decimal
        # If starts with 0x, definitely hex
        if x_str.startswith("0x") or x_str.startswith("0X"):
            x = int(x_str, 16)
        else:
            # If no 0x, try decimal first (common in some configs)
            # If decimal fails or results in off-curve point, could try hex?
            # But usually purely numeric strings are decimal. 
            # Hex strings without 0x usually contain a-f characters.
            if any(c in "abcdefABCDEF" for c in x_str) or any(c in "abcdefABCDEF" for c in y_str):
                x = int(x_str, 16)
            else:
                try:
                    x = int(x_str)
                except ValueError:
                     # Fallback to hex if int fails (e.g. empty string or weird chars)
                     x = int(x_str, 16)

        # Same logic for Y
        if y_str.startswith("0x") or y_str.startswith("0X"):
            y = int(y_str, 16)
        else:
             if any(c in "abcdefABCDEF" for c in y_str):
                 y = int(y_str, 16)
             else:
                 try:
                     y = int(y_str)
                 except ValueError:
                     y = int(y_str, 16)
                     
        pt = Point(curve, x, y)
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
    task_id: str
):
    """
    Implements:
        U_i[j] = g^{r_i} * pk_A^{Δ'_i[j]}

    Args:
        delta_prime: Quantized gradient values (int64) for BSGS compatibility
        pk_tp_hex: Trusted party public key in hex format
        pk_agg_hex: Aggregator public key in hex format
        sk_miner: Miner private key
        ctr: Counter for randomness derivation
        task_id: Task identifier for binding

    Returns:
        List of serialized EC points (safe for transport)
    """
    
    # Validate input types for BSGS compatibility
    if not isinstance(delta_prime, list):
        raise TypeError("delta_prime must be a list")
    
    for i, val in enumerate(delta_prime):
        if not isinstance(val, int):
            raise TypeError(f"delta_prime[{i}] must be int, got {type(val)}")
        if abs(val) > 2**63 - 1:  # int64 safety check
            raise ValueError(f"delta_prime[{i}] = {val} exceeds int64 range")

    pk_tp = load_public_key(pk_tp_hex)
    pk_agg = load_public_key(pk_agg_hex)

    # ---- Step 1: pk_TP^{s_i} ----
    pk_tp_pow_si = sk_miner * pk_tp

    # ---- Step 2: derive r_i ----
    ri = _hash_to_scalar(
        _point_to_bytes(pk_tp_pow_si),
        ctr.to_bytes(8, "big"),
        task_id.encode()
    )

    # ---- Step 3: encrypt each compressed gradient entry ----
    # ---- Step 3: encrypt each compressed gradient entry ----
    ciphertext = []

    base_mask = ri * G  # g^{r_i}
    
    # Optimization: Precompute hex string for zero gradients
    # Since DGC makes >90% of gradients 0, valid * pk_agg is Point at Infinity (Identity)
    # So Ui = base_mask + Identity = base_mask
    base_mask_hex = _point_to_hex(base_mask)

    for val in delta_prime:
        if val == 0:
            ciphertext.append(base_mask_hex)
            continue
            
        # pk_A^{Δ′}
        grad_term = val * pk_agg

        Ui = base_mask + grad_term
        ciphertext.append(_point_to_hex(Ui))

    return ciphertext
