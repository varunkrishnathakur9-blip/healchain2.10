from eth_hash.auto import keccak

def solidity_keccak(*args: bytes) -> bytes:
    return keccak(b"".join(args))
