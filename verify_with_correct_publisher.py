#!/usr/bin/env python3
"""
Verify accuracy commit with correct publisher address from database
"""

from eth_hash.auto import keccak

def verify_with_publisher(accuracy: float, nonce_hex: str, task_id: str, publisher: str, target_commit: str) -> bool:
    """Test accuracy commit: accuracy_uint256 || nonce || taskID || publisher"""
    accuracy_uint = int(accuracy * 1e6)
    accuracy_bytes = accuracy_uint.to_bytes(32, byteorder='big')
    
    nonce_clean = nonce_hex.strip()
    if nonce_clean.lower().startswith('0x'):
        nonce_clean = nonce_clean[2:]
    nonce_bytes = bytes.fromhex(nonce_clean)
    
    task_bytes = task_id.encode('utf-8')
    
    pub_clean = publisher.strip()
    if pub_clean.lower().startswith('0x'):
        pub_clean = pub_clean[2:]
    pub_bytes = bytes.fromhex(pub_clean)
    
    # This is how the form computes it (from frontend)
    # But we don't know if it includes publisher yet
    # Try simple format first: accuracy || nonce
    computed_simple = keccak(accuracy_bytes + nonce_bytes)
    hex_simple = '0x' + computed_simple.hex()
    
    if hex_simple.lower() == target_commit.lower():
        return True, "accuracy || nonce"
    
    # Try with taskID: accuracy || nonce || taskID
    computed_with_task = keccak(accuracy_bytes + nonce_bytes + task_bytes)
    hex_with_task = '0x' + computed_with_task.hex()
    
    if hex_with_task.lower() == target_commit.lower():
        return True, "accuracy || nonce || taskID"
    
    # Try with publisher: accuracy || nonce || taskID || publisher
    computed_full = keccak(accuracy_bytes + nonce_bytes + task_bytes + pub_bytes)
    hex_full = '0x' + computed_full.hex()
    
    if hex_full.lower() == target_commit.lower():
        return True, "accuracy || nonce || taskID || publisher"
    
    # Try publisher first: accuracy || nonce || publisher
    computed_pub_first = keccak(accuracy_bytes + nonce_bytes + pub_bytes)
    hex_pub_first = '0x' + computed_pub_first.hex()
    
    if hex_pub_first.lower() == target_commit.lower():
        return True, "accuracy || nonce || publisher"
    
    return False, None


def main():
    # Exact values from database query
    task_id = "task_040"
    publisher = "0xBF22041166BC98D1c890FF1C98a394486ba99eF0"
    nonce = "5c8d93825407dd37b2532604f98aab603fe80901f34684ee4cf703b3b8c78402"
    target_commit = "0xbc3301534c56bf4debefcfa7809f865cf935c829db9c9db9616cb0782b4eba24"
    target_accuracy = 0.4023
    
    print("=" * 90)
    print("Verify Accuracy Commit with Correct Publisher")
    print("=" * 90)
    print(f"TaskID:         {task_id}")
    print(f"Publisher:      {publisher}")
    print(f"Nonce:          {nonce}")
    print(f"Target Commit:  {target_commit}")
    print(f"DB Accuracy:    {target_accuracy}")
    print()
    print("Testing if accuracy 0.4023 matches...")
    print()
    
    match, fmt = verify_with_publisher(
        target_accuracy, 
        nonce, 
        task_id, 
        publisher, 
        target_commit
    )
    
    if match:
        print(f"✓ ✓ ✓ MATCH VERIFIED ✓ ✓ ✓")
        print()
        print(f"Format: {fmt}")
        print(f"Accuracy: {target_accuracy}")
        print(f"Nonce:    {nonce}")
        print()
        print("=" * 90)
        print("SUCCESS!")
        print()
        print("For M7a Accuracy Reveal form, enter:")
        print(f"  Accuracy:     {target_accuracy}")
        print(f"  Nonce:        {nonce}")
        print()
        print("=" * 90)
    else:
        print("✗ Still no match with target accuracy 0.4023")
        print()
        print("This means either:")
        print("  1. The targetAccuracy field is stored differently in DB")
        print("  2. The commit was computed with a different format")
        print("  3. The commit or nonce has an issue")


if __name__ == '__main__':
    main()
