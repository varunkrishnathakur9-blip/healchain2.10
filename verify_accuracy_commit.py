#!/usr/bin/env python3
"""
Verify accuracy commit with 6 decimal precision.
Tests accuracy range from 40.000000 to 60.000000
"""

from eth_hash.auto import keccak
import sys

def compute_accuracy_commit(accuracy: float, nonce_hex: str) -> str:
    """
    Compute keccak256 commit for accuracy + nonce (M7a format).
    Format: keccak256(accuracy_uint256 || nonce_bytes32)
    where accuracy_uint256 = accuracy * 1e6 (scaled)
    """
    try:
        # Convert accuracy to uint256 (scaled by 1e6)
        # This matches the frontend: Math.floor(accuracy * 1e6)
        accuracy_uint256 = int(accuracy * 1e6)
        accuracy_bytes = accuracy_uint256.to_bytes(32, byteorder='big')
        
        # Clean nonce hex - remove 0x prefix
        nonce_hex_clean = nonce_hex.strip()
        if nonce_hex_clean.lower().startswith('0x'):
            nonce_hex_clean = nonce_hex_clean[2:]
        
        # Validate nonce is exactly 64 hex chars (32 bytes)
        if len(nonce_hex_clean) != 64:
            raise ValueError(f"Nonce must be 64 hex chars (32 bytes), got {len(nonce_hex_clean)}")
        
        nonce_bytes = bytes.fromhex(nonce_hex_clean)
        
        # Compute keccak256
        commit = keccak(accuracy_bytes + nonce_bytes)
        return '0x' + commit.hex()
    except Exception as e:
        raise ValueError(f"Error computing commit: {str(e)}")


def main():
    # From the user's reveal form screenshot
    nonce_input = "5c8d93825407dd37b253260f4f98aab603fe80901f34684ee4cf703b3b8c78402"
    stored_commit = "0xbc3301534c56bf4debefcfa7809f865cf935c829db9c9db9616cb0782b4eba24"
    
    # Clean nonce
    nonce = nonce_input.strip()
    if nonce.lower().startswith('0x'):
        nonce = nonce[2:]
    
    # Validate nonce format
    if len(nonce) != 64:
        print(f"ERROR: Nonce must be 64 hex chars, but got {len(nonce)}")
        print(f"Nonce: {nonce_input}")
        sys.exit(1)
    
    stored_commit_lower = stored_commit.lower()
    
    print("=" * 90)
    print("Accuracy Commit Verification (6 Decimal Precision)")
    print("=" * 90)
    print(f"Nonce:          {nonce}")
    print(f"Nonce length:   {len(nonce)} chars ({len(nonce)//2} bytes)")
    print(f"Stored Commit:  {stored_commit}")
    print(f"Testing range:  40.000000 to 60.000000 (step: 0.000001)")
    print("=" * 90)
    print()
    
    matches = []
    
    # Two-stage search:
    # Stage 1: Coarse search with 0.01 precision to narrow down
    print("[Stage 1] Coarse search (0.01 precision)...")
    candidates = []
    
    for accuracy_int in range(4000, 6001):
        accuracy = accuracy_int / 100.0
        try:
            computed = compute_accuracy_commit(accuracy, nonce)
            if computed.lower() == stored_commit_lower:
                candidates.append((accuracy, computed))
                print(f"  ✓ MATCH at {accuracy}!")
        except Exception as e:
            print(f"  Error at {accuracy}: {e}")
            sys.exit(1)
    
    if candidates:
        print(f"Found {len(candidates)} candidate(s) in coarse search")
        print()
        
        # Stage 2: Refine around candidates with 6 decimal precision
        print("[Stage 2] Fine search (0.000001 precision) around candidates...")
        for candidate_accuracy, _ in candidates:
            # Search ±0.01 around the candidate
            start = int((candidate_accuracy - 0.01) * 1e6)
            end = int((candidate_accuracy + 0.01) * 1e6)
            
            for accuracy_uint in range(start, end + 1):
                accuracy = accuracy_uint / 1e6
                try:
                    computed = compute_accuracy_commit(accuracy, nonce)
                    if computed.lower() == stored_commit_lower:
                        matches.append((accuracy, computed))
                        print(f"  ✓ MATCH FOUND at accuracy: {accuracy}")
                except Exception as e:
                    pass
    else:
        print("No matches in coarse search. Trying fine search on full range...")
        print()
        print("[Stage 2] Fine search (0.000001 precision) on full range...")
        print("This may take a minute or two...")
        
        # Full fine search
        for accuracy_uint in range(40000000, 60000001, 1):
            accuracy = accuracy_uint / 1e6
            
            # Show progress every 1 million iterations
            if accuracy_uint % 1000000 == 0:
                print(f"  Progress: {accuracy:.6f}", end='\r')
            
            try:
                computed = compute_accuracy_commit(accuracy, nonce)
                if computed.lower() == stored_commit_lower:
                    matches.append((accuracy, computed))
                    print(f"  ✓ MATCH FOUND at accuracy: {accuracy}                    ")
            except Exception as e:
                print(f"Error at {accuracy}: {e}")
                sys.exit(1)
    
    print()
    print("=" * 90)
    
    if matches:
        print(f"✓ SUCCESS! Found {len(matches)} matching accuracy value(s):")
        print()
        for accuracy, commit in matches:
            print(f"  Accuracy: {accuracy:.6f}")
            print(f"  Commit:   {commit}")
            print()
        print("=" * 90)
        print(f"Use accuracy: {matches[0][0]:.6f} for the M7a reveal form")
    else:
        print("✗ NO MATCHES FOUND in range 40.000000 to 60.000000")
        print()
        print("Sample computations for reference:")
        for test_accuracy in [40.0, 55.23, 55.230000, 60.0]:
            try:
                computed = compute_accuracy_commit(test_accuracy, nonce)
                print(f"  {test_accuracy}: {computed}")
            except Exception as e:
                print(f"  {test_accuracy}: Error - {e}")
        print()
        print("=" * 90)
        print("TROUBLESHOOTING:")
        print("1. Verify nonce is correct (from task publishing M1)")
        print("2. Verify stored commit is from the task database")
        print("3. Check if the accuracy format should include address/task_id")
        print("4. Verify the hashing function (should be keccak256)")
        print("=" * 90)


if __name__ == '__main__':
    main()
