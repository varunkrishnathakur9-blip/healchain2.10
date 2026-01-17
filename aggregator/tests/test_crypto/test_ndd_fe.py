# HealChain Aggregator - NDD-FE Tests
# Unit tests for NDD-FE decryption

"""
Tests for crypto.ndd_fe
======================

Validates:
- Correctness of NDD-FE decryption
- Linear aggregation under weights
- Consistency with FL-client encryption math

This test is algebraic and deterministic.
It does NOT rely on backend, contracts, or BSGS.
"""

import random

from crypto.ec_utils import G, point_mul, serialize_point
from crypto.ndd_fe import ndd_fe_decrypt


# -------------------------------------------------------------------
# Helpers (synthetic miner-side encryption)
# -------------------------------------------------------------------

def _encrypt_update_synthetic(
    delta_prime,
    *,
    pkA,
):
    """
    Synthetic version of miner encryption with r_i = 0.

    Ui[j] = pkA^{Δ′[j]}

    This isolates FE correctness from randomness.
    """
    ciphertext = []
    for v in delta_prime:
        Ui = point_mul(pkA, v)
        ciphertext.append(serialize_point(Ui))
    return ciphertext


# -------------------------------------------------------------------
# Core Tests
# -------------------------------------------------------------------

def test_ndd_fe_single_miner_identity():
    """
    Single miner, weight = 1.

    Decrypt(pkA^{Δ′}) -> g^{Δ′}
    """
    skA = 7
    pkA = point_mul(G, skA)

    pkTP = point_mul(G, 11)   # arbitrary
    skFE = 0                 # removes FE mask completely

    delta_prime = [3, -5, 10]

    ciphertexts = [
        _encrypt_update_synthetic(delta_prime, pkA=pkA)
    ]

    weights = [1]

    recovered_points = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    expected = [point_mul(G, v) for v in delta_prime]

    assert recovered_points == expected, "Single-miner NDD-FE failed"


def test_ndd_fe_multiple_miners_weighted_sum():
    """
    Multiple miners, linear aggregation under weights.

    Decrypt(Σ pkA^{Δ′_i} * y_i) -> g^{Σ Δ′_i * y_i}
    """
    skA = 13
    pkA = point_mul(G, skA)

    pkTP = point_mul(G, 19)
    skFE = 0

    miner_updates = [
        [5, -2, 7],
        [-1, 4, 3],
        [2, 1, -6],
    ]

    weights = [1, 1, 1]

    ciphertexts = [
        _encrypt_update_synthetic(vec, pkA=pkA)
        for vec in miner_updates
    ]

    recovered_points = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    expected_sum = [
        sum(v[j] for v in miner_updates)
        for j in range(len(miner_updates[0]))
    ]

    expected_points = [point_mul(G, v) for v in expected_sum]

    assert recovered_points == expected_points, "Multi-miner NDD-FE failed"


def test_ndd_fe_weight_scaling():
    """
    Verify weight scaling:
    y_i != 1
    """
    skA = 17
    pkA = point_mul(G, skA)

    pkTP = point_mul(G, 23)
    skFE = 0

    delta1 = [2, 3]
    delta2 = [4, -1]

    weights = [2, 3]  # non-uniform weights

    ciphertexts = [
        _encrypt_update_synthetic(delta1, pkA=pkA),
        _encrypt_update_synthetic(delta2, pkA=pkA),
    ]

    recovered_points = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    expected_vals = [
        weights[0] * delta1[j] + weights[1] * delta2[j]
        for j in range(len(delta1))
    ]

    expected_points = [point_mul(G, v) for v in expected_vals]

    assert recovered_points == expected_points, "Weight scaling failed"
