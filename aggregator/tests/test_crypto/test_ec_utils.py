# HealChain Aggregator - EC Utils Tests
# Unit tests for EC utilities

"""
Tests for crypto.ec_utils
========================

Validates:
- EC point serialization / parsing
- EC arithmetic correctness
- Curve invariants
"""

import sys
import os
import random

# Add src/ to Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

from crypto.ec_utils import (
    G,
    N,
    parse_point,
    serialize_point,
    point_add,
    point_mul,
    point_neg,
)


def test_ec_point_serialization_roundtrip():
    """
    serialize_point(parse_point(P)) == P
    """
    k = random.randint(1, N - 1)
    P = point_mul(G, k)

    serialized = serialize_point(P)
    parsed = parse_point(serialized)

    assert P == parsed, "EC serialization roundtrip failed"


def test_ec_addition_and_negation():
    """
    P + (-P) == identity
    """
    k = random.randint(1, N - 1)
    P = point_mul(G, k)

    neg = point_neg(P)
    result = point_add(P, neg)

    assert result is None or result.x is None, "P + (-P) should be identity"


def test_ec_scalar_multiplication_consistency():
    """
    (a + b)G == aG + bG
    """
    a = random.randint(1, N - 1)
    b = random.randint(1, N - 1)

    left = point_mul(G, a + b)
    right = point_add(point_mul(G, a), point_mul(G, b))

    assert left == right, "EC scalar distributivity failed"
