#!/usr/bin/env python3
"""
HealChain Aggregator - Key Pair Generator
=========================================

Generate matching aggregator public/private key pair for .env configuration.
"""

import os
import sys
import secrets

# Add src/ to Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

from crypto.ec_utils import G, curve, serialize_point
from tinyec.ec import Point


def generate_key_pair():
    """Generate a matching aggregator key pair."""
    
    # Generate random private key (must be in valid range for secp256r1)
    # secp256r1 order is approximately 2^256, so we generate a random number
    # in a safe range (not too close to the order)
    max_sk = curve.field.n - 1
    skA = secrets.randbelow(max_sk) + 1  # Ensure > 0
    
    # Compute public key: pkA = skA * G
    pkA = skA * G
    
    # Serialize public key
    pkA_str = serialize_point(pkA)
    
    return skA, pkA_str


def main():
    """Generate and display key pair."""
    print("HealChain Aggregator - Key Pair Generator")
    print("=" * 60)
    print()
    
    skA, pkA_str = generate_key_pair()
    
    print("Generated matching key pair:")
    print()
    print("Add these to your .env file:")
    print("-" * 60)
    print(f"AGGREGATOR_SK={skA}")
    print(f"AGGREGATOR_PK={pkA_str}")
    print("-" * 60)
    print()
    print("Note: These keys are cryptographically secure and match each other.")
    print("Note: Keep AGGREGATOR_SK secret - it's your private key!")
    print()
    
    # Also generate FE key if needed
    max_fe = curve.field.n - 1
    skFE = secrets.randbelow(max_fe) + 1
    print("Optional: FE Function Key (if needed):")
    print(f"FE_FUNCTION_KEY={skFE}")
    print()


if __name__ == "__main__":
    main()

