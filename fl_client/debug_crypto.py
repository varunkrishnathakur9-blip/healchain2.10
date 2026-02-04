
from Crypto.PublicKey import ECC

print("Testing PyCryptodome Math...")
try:
    curve = 'P-256'
    G_x = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
    G_y = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
    G = ECC.EccPoint(G_x, G_y, curve=curve)
    print(f"G created. Type: {type(G)}")

    scalar = 5
    P = scalar * G
    print(f"scalar * G success: {P}")
    
    P2 = G * scalar
    print(f"G * scalar success: {P2}")
    
    print("Test passed")
except Exception as e:
    print(f"Test FAILED: {e}")
