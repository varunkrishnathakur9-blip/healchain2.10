# HealChain Aggregator - Validation Utilities
# input validation

"""
HealChain Signature Validation Utilities
========================================

Implements real ECDSA signature verification over secp256r1.

Used by:
- aggregation/collector.py (Module M4)
- consensus verification paths

Security-critical.
"""

from typing import Tuple
import os
import binascii
import logging

from ecdsa import VerifyingKey, NIST256p, BadSignatureError

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _parse_public_key(pubkey_str: str) -> VerifyingKey:
    """
    Parse public key from format:
        "x_hex,y_hex"
    """
    try:
        x_hex, y_hex = pubkey_str.split(",")
        x = int(x_hex, 16)
        y = int(y_hex, 16)

        pubkey_bytes = (
            x.to_bytes(32, "big") +
            y.to_bytes(32, "big")
        )

        return VerifyingKey.from_string(
            pubkey_bytes,
            curve=NIST256p
        )
    except Exception as e:
        raise ValueError("Invalid public key format") from e


def _parse_signature(sig_hex: str) -> bytes:
    """
    Parse DER-encoded ECDSA signature from hex string.
    """
    try:
        return binascii.unhexlify(sig_hex)
    except Exception as e:
        raise ValueError("Invalid signature encoding") from e


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def verify_signature(
    *,
    public_key: str,
    message: bytes,
    signature: str
) -> bool:
    """
    Verify ECDSA signature over secp256r1.

    Parameters:
    -----------
    public_key : str
        "x_hex,y_hex"

    message : bytes
        Canonical message bytes

    signature : str
        DER-encoded ECDSA signature (hex)

    Returns:
    --------
    True if valid, False otherwise
    """

    try:
        import hashlib
        vk = _parse_public_key(public_key)
        sig_bytes = _parse_signature(signature)

        vk.verify(sig_bytes, message, hashfunc=hashlib.sha256)
        return True

    except BadSignatureError:
        logger.warning("Invalid ECDSA signature")
        return False

    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False
