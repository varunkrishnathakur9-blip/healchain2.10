from tinyec import registry

def derive_public_key(sk_hex: str) -> str:
    """
    Derive NDD-FE public key from private key hex string.
    Returns "x_hex,y_hex" format.
    """
    if sk_hex.startswith('0x') or sk_hex.startswith('0X'):
        sk_hex = sk_hex[2:]
        
    curve = registry.get_curve("secp256r1")
    G = curve.g
    sk_miner = int(sk_hex, 16)
    pk_point = sk_miner * G
    return f"0x{pk_point.x:064x},0x{pk_point.y:064x}"
