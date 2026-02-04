
import time
from tinyec import registry
from tinyec.ec import Point
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from Crypto.PublicKey import ECC
import random

# Setup Test Data
curve = registry.get_curve("secp256r1")
G = curve.g
priv_int = 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
priv_int2 = 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
cnt = 1000

print(f"Benchmarking {cnt} operations...")

# --- 1. TinyEC ---
start = time.time()
params = []
for _ in range(cnt):
    # Scalar Mul
    P = priv_int * G
    # Point Add
    Q = P + G
tinyec_time = time.time() - start
print(f"TinyEC: {tinyec_time:.4f}s ({cnt/tinyec_time:.0f} ops/s)")


# --- 2. PyCryptodome ---
# Check if pycryptodome supports addition
try:
    start = time.time()
    # Construct point from tinyec coords to ensure same curve
    key = ECC.construct(curve='P-256', d=priv_int)
    P_base = key.pointQ
    
    # Create another point
    key2 = ECC.construct(curve='P-256', d=priv_int2)
    Q_base = key2.pointQ
    
    for _ in range(cnt):
        # Scalar Mul (Optimization: PyCryptodome usually uses 'd' for scalar mul when constructing?)
        # Actually ECC.Point supports *
        P = P_base * 5  # Scalar mul
        
        # Point Add
        R = P + Q_base
        
    pycrypto_time = time.time() - start
    print(f"PyCryptodome: {pycrypto_time:.4f}s ({cnt/pycrypto_time:.0f} ops/s)")
except Exception as e:
    print(f"PyCryptodome Failed: {e}")
    pycrypto_time = 999


# --- 3. Cryptography ---
try:
    start = time.time()
    # Cryptography doesn't support point addition directly on high-level objects usually
    # But let's check
    priv = ec.derive_private_key(priv_int, ec.SECP256R1())
    pub = priv.public_key()
    
    # It supports ECDH, Signing... but scalar mul of arbitrary point?
    # No, it doesn't expose point * scalar or point + point in the high level API.
    # It relies on 'hazmat' which might be hard to use.
    
    # We can try to use private key scalar mul (by deriving new private key?)
    # But Point + Point is the blocker.
    
    # Test if we can access public_numbers
    pn = pub.public_numbers()
    
    print(f"Cryptography: High-level API does not support raw point arithmetic needed for NDD-FE (Homomorphic Encryption). Skipping speed test.")
except Exception as e:
    print(f"Cryptography Failed: {e}")

