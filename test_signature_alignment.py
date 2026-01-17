#!/usr/bin/env python3
"""
Test script to verify signature alignment between FL client and aggregator.
"""

import sys
import os

# Add paths
sys.path.insert(0, 'fl_client/src')
sys.path.insert(0, 'aggregator/src')

from fl_client.crypto.signature import generate_miner_signature
from aggregator.utils.validation import verify_signature

def test_signature_flow():
    """Test complete signature generation and verification flow."""
    
    print("🔐 Testing Signature Alignment...")
    
    # Test data
    task_id = "test_task_001"
    ciphertext = ["0xmockpoint1,0xmockpoint2", "0xmockpoint3,0xmockpoint4"]
    score_commit = "0xabc123def456"
    miner_pk = "0x331Ad92A1938028c8F2770BC9F5001eD67d9177B"
    miner_private_key = "0x" + "0" * 64  # Mock private key
    
    try:
        # Generate signature (FL client)
        signature, canonical_msg = generate_miner_signature(
            task_id=task_id,
            ciphertext=ciphertext,
            score_commit=score_commit,
            miner_pk=miner_pk,
            miner_private_key=miner_private_key
        )
        
        print(f"✅ Signature generated: {signature[:20]}...")
        print(f"✅ Canonical message: {canonical_msg}")
        
        # Verify signature (Aggregator)
        # Convert list to string for canonical message (as aggregator does)
        ciphertext_concat = ",".join(ciphertext)
        canonical_message_bytes = f"{task_id}|{ciphertext_concat}|{score_commit}|{miner_pk}".encode("utf-8")
        
        is_valid = verify_signature(
            public_key=miner_pk,
            message=canonical_message_bytes,
            signature=signature
        )
        
        if is_valid:
            print("✅ Signature verification: PASSED")
            print("🎉 Signature alignment is PERFECT!")
            return True
        else:
            print("❌ Signature verification: FAILED")
            print("⚠️ Signature alignment needs fixing")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_signature_flow()
    sys.exit(0 if success else 1)
