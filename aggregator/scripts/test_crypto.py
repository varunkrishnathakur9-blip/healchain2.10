# HealChain Aggregator - Crypto Testing Script
# Script for testing cryptographic components

"""
HealChain Aggregator – Cryptography Test Script
===============================================

Purpose:
---------
Standalone cryptographic sanity checks for the Aggregator.

Tests:
------
1. EC point serialization / parsing
2. Signed bounded BSGS recovery
3. NDD-FE decrypt → BSGS → dequantize pipeline (synthetic test)

This script DOES NOT:
--------------------
- Contact backend
- Require smart contracts
- Require FL-client execution
"""

import sys
import os
import random

# ------------------------------------------------------------------
# Ensure src/ is on path
# ------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, SRC_DIR)

from crypto.ec_utils import G, point_mul, serialize_point, parse_point
from crypto.bsgs import recover_discrete_log, dequantize_vector
from crypto.ndd_fe import ndd_fe_decrypt
from utils.logging import setup_logging

from tinyec import registry

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

setup_logging(level="INFO")

curve = registry.get_curve("secp256r1")

print("\n==============================")
print(" HealChain Aggregator Crypto Test")
print("==============================\n")


# ------------------------------------------------------------------
# Test 1: EC Serialization
# ------------------------------------------------------------------

def test_ec_serialization():
    print("[TEST 1] EC point serialization")

    k = random.randint(1, 1_000_000)
    P = point_mul(G, k)

    s = serialize_point(P)
    P2 = parse_point(s)

    assert P == P2, "EC serialization mismatch"
    print("✔ EC serialization / parsing OK")


# ------------------------------------------------------------------
# Test 2: Signed BSGS Recovery
# ------------------------------------------------------------------

def test_bsgs_signed():
    print("[TEST 2] Signed BSGS recovery")

    # Test with smaller values that work with BSGS algorithm
    # BSGS works correctly but has performance limits for very large bounds
    test_values = [
        1,        # Small positive
        -1,       # Small negative
        1000,     # Medium positive
        -1000,    # Medium negative
        50000,    # Larger positive
        -50000,   # Larger negative
    ]

    for x in test_values:
        P = point_mul(G, x)
        recovered = recover_discrete_log(P)
        print(f"Testing x={x}, recovered={recovered}")
        assert recovered == x, f"BSGS failed for {x}"

    print("✔ Signed BSGS recovery OK")


# ------------------------------------------------------------------
# Test 3: Synthetic NDD-FE + BSGS Pipeline
# ------------------------------------------------------------------

def test_ndd_fe_pipeline():
    print("[TEST 3] NDD-FE → BSGS pipeline (synthetic)")

    # ------------------------------------------------------------
    # Synthetic parameters
    # ------------------------------------------------------------
    num_miners = 3
    vector_len = 5

    skA = 17
    pkA = skA * G

    skTP = 23
    pkTP = skTP * G

    skFE = 0  # mask = pkTP^0 = identity (simplified test)

    weights = [1] * num_miners

    # ------------------------------------------------------------
    # Create synthetic encrypted updates
    # ------------------------------------------------------------
    true_sum = [0] * vector_len
    ciphertexts = []

    for _ in range(num_miners):
        miner_vec = []
        ct_vec = []

        for j in range(vector_len):
            v = random.randint(-1000, 1000)
            miner_vec.append(v)
            true_sum[j] += v

            Ui = point_mul(pkA, v)  # g^{sA*v}
            ct_vec.append(serialize_point(Ui))

        ciphertexts.append(ct_vec)

    # ------------------------------------------------------------
    # NDD-FE decrypt
    # ------------------------------------------------------------
    recovered_points = ndd_fe_decrypt(
        ciphertexts=ciphertexts,
        weights=weights,
        pk_tp=pkTP,
        sk_fe=skFE,
        sk_agg=skA,
    )

    # ------------------------------------------------------------
    # BSGS recover
    # ------------------------------------------------------------
    recovered_ints = [recover_discrete_log(p) for p in recovered_points]

    assert recovered_ints == true_sum, "NDD-FE pipeline mismatch"

    print("✔ NDD-FE → BSGS pipeline OK")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    test_ec_serialization()
    test_bsgs_signed()
    test_ndd_fe_pipeline()

    print("\n🎉 All cryptographic tests PASSED\n")
