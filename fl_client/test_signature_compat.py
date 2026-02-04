#!/usr/bin/env python3
"""
Test signature compatibility between PyCryptodome (FL Client) and ecdsa (Aggregator)
"""

import hashlib
import binascii

# FL Client Side (PyCryptodome)
print("=== FL Client (PyCryptodome) ===")
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256

priv_hex = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
message = b"test_canonical_message"

# Generate key and signature with PyCryptodome
key_crypto = ECC.construct(curve='P-256', d=int(priv_hex, 16))
h = SHA256.new(message)
signer = DSS.new(key_crypto, 'fips-186-3')
sig_crypto = signer.sign(h)

# Extract public key coordinates
pub_x = int(key_crypto.pointQ.x)
pub_y = int(key_crypto.pointQ.y)
pub_key_str = f"0x{pub_x:064x},0x{pub_y:064x}"

print(f"Public Key: {pub_key_str}")
print(f"Signature (hex): {binascii.hexlify(sig_crypto).decode()}")
print(f"Signature length: {len(sig_crypto)} bytes")

# Aggregator Side (ecdsa library)
print("\n=== Aggregator (ecdsa) ===")
from ecdsa import VerifyingKey, NIST256p

# Parse public key from FL client format
x_hex, y_hex = pub_key_str.split(",")
x = int(x_hex, 16)
y = int(y_hex, 16)
pubkey_bytes = x.to_bytes(32, "big") + y.to_bytes(32, "big")
vk = VerifyingKey.from_string(pubkey_bytes, curve=NIST256p)

# Verify signature
try:
    vk.verify(sig_crypto, message, hashfunc=hashlib.sha256)
    print("✅ Signature VERIFIED successfully!")
except Exception as e:
    print(f"❌ Signature verification FAILED: {e}")
