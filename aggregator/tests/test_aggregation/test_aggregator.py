# HealChain Aggregator - Aggregation Tests
# Unit tests for aggregation logic

"""
Tests for aggregation.aggregator
================================

Validates:
- Secure aggregation pipeline (Module M4)
- Correct interaction between:
    collector → ndd-fe → bsgs → verifier
- Deterministic aggregation of signed gradients

This test is backend-free and consensus-free.
"""

import random
from math import isclose

from crypto.ec_utils import G, point_add, point_mul, serialize_hex_point
from crypto.ndd_fe import ndd_fe_decrypt
from crypto.bsgs import recover_discrete_log, dequantize_vector
from aggregation.aggregator import secure_aggregate
from aggregation.verifier import verify_recovered_aggregate
from state.key_manager import KeyManager


# -------------------------------------------------------------------
# Synthetic Helpers
# -------------------------------------------------------------------

def _encrypt_synthetic(delta, pkA):
    """
    Deterministic miner-side encryption with r_i = 1.
    """
    base_mask = point_mul(G, 1)
    ciphertext = []
    for v in delta:
        Ui = base_mask if v == 0 else point_add(base_mask, point_mul(pkA, v))
        ciphertext.append(serialize_hex_point(Ui))
    return ciphertext


class _MockKeyManager:
    """
    Minimal KeyManager stub for aggregation tests.
    """
    def __init__(self, skA, pkA):
        self.skA = skA
        self.pkA = pkA
        self.pkTP = point_mul(G, 1)
        self.skFE = 1

    def parse_ciphertext_point(self, s):
        from crypto.ec_utils import parse_point
        return parse_point(s)


# -------------------------------------------------------------------
# Core Aggregation Test
# -------------------------------------------------------------------

def test_secure_aggregation_pipeline():
    """
    End-to-end secure aggregation (M4):
    ciphertexts → decrypted points → BSGS → verification
    """

    # ------------------------------------------------------------
    # Setup synthetic keys
    # ------------------------------------------------------------
    skA = 11
    pkA = point_mul(G, skA)

    keys = _MockKeyManager(skA, pkA)

    # ------------------------------------------------------------
    # Synthetic miner updates (quantized ints)
    # ------------------------------------------------------------
    miner_updates = [
        [5, -3, 7],
        [-2, 4, 1],
        [6, -1, -5],
    ]

    weights = [1, 1, 1]
    keys.skFE = sum(weights)

    submissions = []

    for i, vec in enumerate(miner_updates):
        submissions.append({
            "miner_pk": f"miner{i}",
            "ciphertext": _encrypt_synthetic(vec, pkA),
            "score_commit": f"commit{i}",
        })

    # ------------------------------------------------------------
    # Secure aggregation
    # ------------------------------------------------------------
    aggregate_update = secure_aggregate(
        submissions=submissions,
        skFE=keys.skFE,
        skA=keys.skA,
        pkTP=keys.pkTP,
        weights=weights,
    )

    expected_average = [
        sum(weights[i] * v[j] for i, v in enumerate(miner_updates)) / sum(weights)
        for j in range(len(miner_updates[0]))
    ]

    for got, expected in zip(aggregate_update, expected_average):
        assert isclose(got * 1_000_000, expected, rel_tol=0, abs_tol=1e-9)


def test_secure_aggregation_normalizes_non_uniform_weights():
    """
    secure_aggregate returns sum(alpha_i * g_i) / sum(alpha_i), not the raw sum.
    """
    skA = 11
    pkA = point_mul(G, skA)
    keys = _MockKeyManager(skA, pkA)

    miner_updates = [
        [10, -5],
        [0, 15],
    ]
    weights = [2, 3]
    keys.skFE = sum(weights)

    submissions = [
        {
            "miner_pk": f"miner{i}",
            "ciphertext": _encrypt_synthetic(vec, pkA),
            "score_commit": f"commit{i}",
        }
        for i, vec in enumerate(miner_updates)
    ]

    aggregate_update = secure_aggregate(
        submissions=submissions,
        skFE=keys.skFE,
        skA=keys.skA,
        pkTP=keys.pkTP,
        weights=weights,
    )

    expected_average = [
        sum(weights[i] * v[j] for i, v in enumerate(miner_updates)) / sum(weights)
        for j in range(len(miner_updates[0]))
    ]

    for got, expected in zip(aggregate_update, expected_average):
        assert isclose(got * 1_000_000, expected, rel_tol=0, abs_tol=1e-9)

