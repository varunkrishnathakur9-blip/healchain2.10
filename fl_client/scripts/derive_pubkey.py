#!/usr/bin/env python3
"""
HealChain FL Client - NDD-FE Public Key Derivation
==================================================

Derives the NDD-FE public key (secp256r1) from MINER_PRIVATE_KEY.
The public key is used for Algorithm 2.2 key derivation during miner registration.

Formula: pk = g^sk where:
- g is the secp256r1 generator point
- sk is the miner's private key
- pk is the public key (EC point: x_hex,y_hex)

Usage:
    python scripts/derive_pubkey.py
    python scripts/derive_pubkey.py 0xYourPrivateKey
    python scripts/derive_pubkey.py YourPrivateKeyWithout0x
"""

import os
import sys
import argparse

# Ensure we can import from parent directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tinyec import registry


def derive_public_key(sk_hex: str) -> str:
    """
    Derive NDD-FE public key from private key.
    
    Args:
        sk_hex: Private key as hex string (with or without 0x prefix)
    
    Returns:
        Public key in format "x_hex,y_hex" (64 hex digits each)
    """
    # Remove 0x prefix if present
    if sk_hex.startswith('0x') or sk_hex.startswith('0X'):
        sk_hex = sk_hex[2:]
    
    # Validate hex string
    if not all(c in '0123456789abcdefABCDEF' for c in sk_hex):
        raise ValueError(f"Invalid hex string: {sk_hex[:20]}...")
    
    # Get curve and generator
    curve = registry.get_curve("secp256r1")
    G = curve.g
    
    # Convert to integer
    try:
        sk_miner = int(sk_hex, 16)
    except ValueError as e:
        raise ValueError(f"Invalid hex string: {sk_hex[:20]}...") from e
    
    # Compute public key: pk = g^sk (scalar multiplication)
    pk_point = sk_miner * G
    
    # Format as x_hex,y_hex (64 hex digits each, zero-padded)
    pk_hex = f"{pk_point.x:064x},{pk_point.y:064x}"
    
    return pk_hex


def main():
    parser = argparse.ArgumentParser(
        description="Derive NDD-FE public key from MINER_PRIVATE_KEY",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use MINER_PRIVATE_KEY from environment
  python scripts/derive_pubkey.py
  
  # Use explicit private key
  python scripts/derive_pubkey.py 0x1234...abcd
  
  # Output only the public key (for scripts)
  python scripts/derive_pubkey.py --quiet
        """
    )
    parser.add_argument(
        "private_key",
        nargs="?",
        help="Private key as hex string (optional, uses MINER_PRIVATE_KEY env var if not provided)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Output only the public key (no formatting)"
    )
    
    args = parser.parse_args()
    
    # Get private key from argument or environment
    if args.private_key:
        sk_hex = args.private_key
    else:
        sk_hex = os.getenv("MINER_PRIVATE_KEY", "")
        if not sk_hex:
            print("Error: MINER_PRIVATE_KEY not found in environment.")
            print("Usage: python scripts/derive_pubkey.py <private_key_hex>")
            print("   or: export MINER_PRIVATE_KEY=0x... && python scripts/derive_pubkey.py")
            sys.exit(1)
    
    try:
        # Derive public key
        pk_hex = derive_public_key(sk_hex)
        
        if args.quiet:
            # Output only the public key (for scripts/piping)
            print(pk_hex)
        else:
            # Pretty output
            print("=" * 70)
            print("NDD-FE Public Key Derivation (secp256r1)")
            print("=" * 70)
            print()
            
            # Show private key (masked for security)
            sk_display = sk_hex.replace('0x', '').replace('0X', '')
            if len(sk_display) > 20:
                sk_display = sk_display[:10] + "..." + sk_display[-10:]
            print(f"Private Key: 0x{sk_display}")
            print()
            print(f"Public Key:  {pk_hex}")
            print()
            print("=" * 70)
            print()
            print("📋 Copy this public key for miner registration:")
            print()
            print(f"   {pk_hex}")
            print()
            print("=" * 70)
            print()
            print("ℹ️  This public key is used for:")
            print("   • Algorithm 2.2: Key derivation (NDD-FE)")
            print("   • Miner registration in the frontend")
            print("   • Format: x_hex,y_hex (64 hex digits each)")
            print()
            
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
