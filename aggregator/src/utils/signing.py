# HealChain Aggregator - Signing Utilities
# candidate signature helpers

"""
ECDSA signing helpers for aggregator-owned messages.

Used by:
- M4 candidate block signing (signatureA)
"""

import hashlib
import binascii

from ecdsa import NIST256p, SigningKey
from ecdsa.util import sigencode_string


def sign_bytes_with_scalar(*, private_scalar: int, message: bytes) -> str:
    """
    Deterministically sign bytes with secp256r1 private scalar.

    Parameters:
    -----------
    private_scalar : int
        Aggregator private key scalar (skA)
    message : bytes
        Message bytes to sign

    Returns:
    --------
    signature_hex : str
        Hex-encoded raw signature (r||s, 64 bytes for P-256)
    """
    if private_scalar <= 0:
        raise ValueError("private_scalar must be a positive integer")

    sk = SigningKey.from_secret_exponent(private_scalar, curve=NIST256p)
    sig_bytes = sk.sign_deterministic(
        message,
        hashfunc=hashlib.sha256,
        sigencode=sigencode_string,
    )
    return binascii.hexlify(sig_bytes).decode("ascii")


def sign_hash_hex_with_scalar(*, private_scalar: int, hash_hex: str) -> str:
    """
    Sign a precomputed hash (hex) with secp256r1 private scalar.
    """
    token = (hash_hex or "").strip().lower()
    if token.startswith("0x"):
        token = token[2:]
    if len(token) != 64:
        raise ValueError("hash_hex must be a 32-byte (64 hex chars) digest")
    try:
        digest_bytes = bytes.fromhex(token)
    except Exception as e:
        raise ValueError(f"Invalid hash_hex: {hash_hex!r}") from e

    return sign_bytes_with_scalar(private_scalar=private_scalar, message=digest_bytes)

