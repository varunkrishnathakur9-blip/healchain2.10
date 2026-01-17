# HealChain Aggregator - BSGS Tests
# Unit tests for BSGS algorithm

"""
Tests for crypto.bsgs
=====================

Validates:
- Signed discrete log recovery
- Boundary correctness
- Failure outside configured bounds

These tests rely on the FIXED HealChain BSGS configuration.
"""

import pytest

from crypto.ec_utils import G, point_mul, point_add
from crypto.bsgs import (
    recover_discrete_log,
    BSGS_MIN_BOUND,
    BSGS_MAX_BOUND,
)


# -------------------------------------------------------------------
# Core Signed Recovery Tests
# -------------------------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        0,
        1,
        -1,
        42,
        -42,
        123456,
        -123456,
        BSGS_MAX_BOUND,
        BSGS_MIN_BOUND,
    ],
)
def test_signed_bsgs_recovery(value):
    """
    recover_discrete_log(g^x) == x for signed values
    """
    P = point_mul(G, value)
    recovered = recover_discrete_log(P)

    assert recovered == value, f"BSGS failed for value {value}"


# -------------------------------------------------------------------
# Boundary Safety Tests
# -------------------------------------------------------------------

def test_bsgs_rejects_out_of_range_positive():
    """
    Values above max bound must not be recovered.
    """
    out_of_range = BSGS_MAX_BOUND + 1
    P = point_mul(G, out_of_range)

    with pytest.raises(ValueError):
        recover_discrete_log(P)


def test_bsgs_rejects_out_of_range_negative():
    """
    Values below min bound must not be recovered.
    """
    out_of_range = BSGS_MIN_BOUND - 1
    P = point_mul(G, out_of_range)

    with pytest.raises(ValueError):
        recover_discrete_log(P)


# -------------------------------------------------------------------
# Algebraic Consistency Test
# -------------------------------------------------------------------

def test_bsgs_additive_consistency():
    """
    BSGS(xG + yG) == x + y
    """
    x = 12345
    y = -6789

    P = point_add(point_mul(G, x), point_mul(G, y))
    recovered = recover_discrete_log(P)

    assert recovered == x + y, "Additive consistency failed"
