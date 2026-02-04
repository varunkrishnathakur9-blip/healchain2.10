
try:
    from ecdsa import SigningKey, NIST256p
    import hashlib
    print("ECDSA Library: Found")
except ImportError:
    print("ECDSA Library: NOT FOUND")

try:
    from Crypto.PublicKey import ECC
    from Crypto.Signature import DSS
    from Crypto.Hash import SHA256
    print("PyCryptodome: Found")
except ImportError:
    print("PyCryptodome: NOT FOUND")

import binascii

# Test Data
priv_hex = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
msg = b"test_message"

print("\n--- Testing ECDSA (Current) ---")
try:
    sk_bytes = bytes.fromhex(priv_hex[2:])
    sk = SigningKey.from_string(sk_bytes, curve=NIST256p)
    sig = sk.sign(msg, hashfunc=hashlib.sha256)
    print(f"Success! Signature Length: {len(sig)} bytes")
    print(f"Hex: {binascii.hexlify(sig).decode()}")
except Exception as e:
    print(f"FAILED: {e}")

print("\n--- Testing PyCryptodome (Proposed) ---")
try:
    key = ECC.construct(curve='P-256', d=int(priv_hex[2:], 16))
    h = SHA256.new(msg)
    signer = DSS.new(key, 'fips-186-3')
    
    # Check default format
    sig_p = signer.sign(h)
    print(f"Default Signature Length: {len(sig_p)} bytes")
    print(f"Hex: {binascii.hexlify(sig_p).decode()}")
    
    # If length matches (64 bytes), it's raw (r|s).
    if len(sig_p) == 64:
        print("Format: Raw (r|s)")
    else:
        print("Format: Likely DER")

except Exception as e:
    print(f"FAILED: {e}")
