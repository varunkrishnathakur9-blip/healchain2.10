# HealChain Aggregator - Curve Configuration
# secp256r1 params (fixed)

"""
HealChain Aggregator – Curve Configuration
==========================================

Defines the elliptic curve parameters used throughout the aggregator.

IMPORTANT:
----------
- This file defines a GLOBAL CRYPTOGRAPHIC INVARIANT.
- It MUST match the FL-client and smart contract assumptions.
- Do NOT modify once deployed.

Curve:
------
- secp256r1 (NIST P-256)
"""

from tinyec import registry
from tinyec.ec import Curve, Point

# -------------------------------------------------------------------
# Curve Definition (FIXED)
# -------------------------------------------------------------------

curve: Curve = registry.get_curve("secp256r1")

# Base point (generator)
G: Point = curve.g

# Curve order (n)
N: int = curve.field.n

# Prime field modulus (p)
P: int = curve.field.p
