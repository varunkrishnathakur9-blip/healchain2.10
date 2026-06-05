#!/usr/bin/env python3
"""
Verify accuracy commit with exact database values
"""

from eth_hash.auto import keccak

def verify_accuracy_commit(accuracy: float, nonce_hex: str, stored_commit: str) -> bool:
    """
    Verify if accuracy + nonce produces the stored commit hash.
    Format: keccak256(accuracy_uint256 || nonce_bytes32)
    """
    try:
        # Convert accuracy to uint256 (scaled by 1e6)
        accuracy_uint256 = int(accuracy * 1e6)
        accuracy_bytes = accuracy_uint256.to_bytes(32, byteorder='big')
        
        # Clean nonce hex
        nonce_hex_clean = nonce_hex.strip()
        if nonce_hex_clean.lower().startswith('0x'):
            nonce_hex_clean = nonce_hex_clean[2:]
        
        # Validate nonce length
        if len(nonce_hex_clean) != 64:
            print(f"ERROR: Nonce is {len(nonce_hex_clean)} chars, expected 64")
            return False
        
        nonce_bytes = bytes.fromhex(nonce_hex_clean)
        
        # Compute keccak256
        computed_commit = keccak(accuracy_bytes + nonce_bytes)
        computed_hex = '0x' + computed_commit.hex()
        
        stored_lower = stored_commit.lower()
        computed_lower = computed_hex.lower()
        
        print()
        print("=" * 90)
        print("Accuracy Commit Verification")
        print("=" * 90)
        print(f"Accuracy:        {accuracy}")
        print(f"Accuracy (uint): {accuracy_uint256}")
        print(f"Nonce:           {nonce_hex}")
        print()
        print(f"Stored Commit:   {stored_lower}")
        print(f"Computed Commit: {computed_lower}")
        print()
        
        if stored_lower == computed_lower:
            print("✓ ✓ ✓ MATCH VERIFIED ✓ ✓ ✓")
            print()
            print(f"The accuracy {accuracy} is CORRECT!")
            print(f"Use this for M7a Accuracy Reveal:")
            print(f"  - Accuracy: {accuracy}")
            print(f"  - Nonce: {nonce_hex}")
            print()
            return True
        else:
            print("✗ ✗ ✗ MISMATCH ✗ ✗ ✗")
            print()
            print("The accuracy does NOT match the stored commit.")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    # Exact values from database
    accuracy = 0.4023  # This is 40.23%
    nonce = "5c8d93825407dd37b2532604f98aab603fe80901f34684ee4cf703b3b8c78402"
    commit = "0xbc3301534c56bf4debefcfa7809f865cf935c829db9c9db9616cb0782b4eba24"
    
    result = verify_accuracy_commit(accuracy, nonce, commit)
    
    print("=" * 90)
    if result:
        print("✓ SUCCESS - Accuracy verified!")
    else:
        print("✗ FAILED - Accuracy does not match")
        print()
        print("Attempting nearby values...")
        print()
        
        # Try a few nearby values
        for test_acc in [40.23, 40.230000, 0.4023, 40.0, 55.23]:
            print(f"Testing {test_acc}...", end=" ")
            if verify_accuracy_commit(test_acc, nonce, commit):
                print("MATCH!")
                break
            print()


if __name__ == '__main__':
    main()
