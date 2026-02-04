
import time
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from crypto.nddfe import encrypt_update, load_public_key
from crypto.keys import derive_public_key

print("Testing PyCryptodome Migration...")

# 1. Test Key Derivation
priv_key_hex = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
pub_key = derive_public_key(priv_key_hex)
print(f"Derived Public Key: {pub_key}")

# 2. Test Key Loading
pt = load_public_key(pub_key)
print(f"Loaded Point: {pt}")

# 3. Test Encryption Speed
print("\n--- Speed Test ---")
# Create mock gradients (10k params, 90% zero)
deltas = [0] * 9000 + [123, -45, 678, -99] * 250
deltas = deltas[:10000]

start = time.time()
ciphertext = encrypt_update(
    delta_prime=deltas,
    pk_tp_hex=pub_key,  # Reuse same key for test
    pk_agg_hex=pub_key, # Reuse same key for test
    sk_miner=int(priv_key_hex, 16),
    ctr=1,
    task_id="test_task"
)
duration = time.time() - start
print(f"Encryption of 10k params took: {duration:.4f}s")
print(f"Projected time for 25.7M params: {(duration * 2570):.2f}s ({(duration * 2570)/60:.2f} mins)")
print(f"Ciphertext length: {len(ciphertext)}")
print(f"First Ciphertext: {ciphertext[0]}")
if len(ciphertext) == 10000:
    print("✅ SUCCESS: Encryption works and length matches.")
else:
    print("❌ FAILURE: Length mismatch.")
