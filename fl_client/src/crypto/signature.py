# HealChain FL Client - Signature Generation
# ECDSA signature utilities

"""
HealChain Signature Generation Utilities
====================================

Implements ECDSA signature generation for miner submissions.
Uses secp256r1 curve for compatibility with aggregator.
"""

import hashlib
import binascii
from typing import Tuple

from ecdsa import SigningKey, NIST256p


def sign_message(*, private_key: str, message: bytes) -> str:
    """
    Sign canonical message using miner private key.
    
    Parameters:
    -----------
    private_key : str
        Miner private key (hex string)
        
    message : bytes
        Canonical message to sign
        
    Returns:
    --------
    signature_hex : str
        DER-encoded ECDSA signature (hex)
    """
    try:
        # Parse private key - strip '0x' prefix if present
        private_key_clean = private_key.strip()
        if private_key_clean.startswith('0x') or private_key_clean.startswith('0X'):
            private_key_clean = private_key_clean[2:]
        
        # Validate hex string
        if not all(c in '0123456789abcdefABCDEF' for c in private_key_clean):
            raise ValueError(f"Invalid hex string in private key: {private_key[:10]}...")
        
        sk_bytes = bytes.fromhex(private_key_clean)
        sk = SigningKey.from_string(sk_bytes, curve=NIST256p)
        
        # Sign message with SHA-256 hash
        signature = sk.sign(message, hashfunc=hashlib.sha256)
        
        # Return DER-encoded hex signature
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
) -> Tuple[str, str]:
    """
    Generate signature for miner submission.
    
    Parameters:
    -----------
    task_id : str
        Task identifier
        
    ciphertext : str
        Ciphertext (concatenated)
        
    score_commit : str
        Score commitment
        
    miner_pk : str
        Miner public key (for canonical message)
        
    miner_private_key : str
        Miner private key (hex)
        
    Returns:
    --------
    signature_hex : str
        DER-encoded signature
        
    canonical_message : str
        The message that was signed
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
