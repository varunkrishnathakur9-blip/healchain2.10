from Crypto.PublicKey import ECC

# Define Generator G for P-256
CURVE_NAME = 'P-256'
G_x = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
G_y = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
G = ECC.EccPoint(G_x, G_y, curve=CURVE_NAME)

def derive_public_key(sk_hex: str) -> str:
    """
    Derive NDD-FE public key from private key hex string.
    Returns "x_hex,y_hex" format.
    """
    if sk_hex.startswith('0x') or sk_hex.startswith('0X'):
        sk_hex = sk_hex[2:]
        
    sk_miner = int(sk_hex, 16)
    
    # Calculate Public Point = sk * G
    pk_point = G * sk_miner
    
    return f"0x{int(pk_point.x):064x},0x{int(pk_point.y):064x}"
