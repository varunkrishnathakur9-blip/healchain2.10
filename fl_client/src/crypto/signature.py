# HealChain FL Client - Signature Generation
# ECDSA signature utilities

"""
HealChain Signature Generation Utilities
====================================

Implements ECDSA signature generation for miner submissions.
Uses secp256r1 curve for compatibility with aggregator.
"""


from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256
import binascii

def sign_message(*, private_key: str, message: bytes) -> str:
    """
    Sign canonical message using miner private key.
    Uses PyCryptodome (Deterministic ECDSA).
    
    Returns:
    --------
    signature_hex : str
        Hex-encoded signature (Raw r||s format, 64 bytes for P-256)
    """
    try:
        # Parse private key - strip '0x' prefix if present
        private_key_clean = private_key.strip()
        if private_key_clean.startswith('0x') or private_key_clean.startswith('0X'):
            private_key_clean = private_key_clean[2:]
        
        # Load Private Key
        d_int = int(private_key_clean, 16)
        key = ECC.construct(curve='P-256', d=d_int)
        
        # Hash Message
        h = SHA256.new(message)
        
        # Sign (Deterministic ECDSA - RFC 6979 is default for DSS 'fips-186-3')
        signer = DSS.new(key, 'fips-186-3')
        signature = signer.sign(h)
        
        # Return hex signature
        return binascii.hexlify(signature).decode()
        
    except Exception as e:
        raise ValueError(f"Signature generation failed: {e}") from e


def generate_miner_signature(
    *,
    task_id: str,
    ciphertext: str,
    score_commit: str,
    miner_pk: str,
    miner_private_key: str
) -> tuple[str, str]:
    """
    Generate signature for miner submission.
    """
    # Build canonical message (exact same as aggregator)
    canonical_message = f"{task_id}|{ciphertext}|{score_commit}|{miner_pk}"
    message_bytes = canonical_message.encode("utf-8")
    
    # Generate signature
    signature = sign_message(
        private_key=miner_private_key,
        message=message_bytes
    )
    
    return signature, canonical_message
