from ecdsa import SigningKey, NIST256p
import binascii
import json

def gen_data(task_id, miner_id, ciphertext):
    sk = SigningKey.generate(curve=NIST256p)
    vk = sk.get_verifying_key()
    
    # Aggregator expects x_hex,y_hex
    x = format(vk.pubkey.point.x(), 'x').zfill(64)
    y = format(vk.pubkey.point.y(), 'x').zfill(64)
    pubkey_str = f"0x{x},0x{y}"
    
    score_commit = f"0xCommit_{miner_id}"
    
    # Canonical message construction (from collector.py)
    ciphertext_concat = ",".join(ciphertext)
    parts = [
        task_id,
        ciphertext_concat,
        score_commit,
        pubkey_str
    ]
    message = "|".join(parts).encode("utf-8")
    
    # Sign
    sig_bytes = sk.sign(message)
    # Aggregator expects hex
    sig_hex = binascii.hexlify(sig_bytes).decode("utf-8")
    
    return {
        "miner_pk": pubkey_str,
        "score_commit": score_commit,
        "signature": sig_hex,
        "ciphertext": ciphertext
    }

TASK_ID = "task_027"
CT = ["0xmockpoint1,0xmockpoint2", "0xmockpoint3,0xmockpoint4"]
MINERS = [
    "0xbe884ed9ea8bddba74f661c363f182eff6e30248",
    "0x88525bde5e667ab53c499702b72c9bda119ec85b", # Wait, this might be publisher/aggregator, but let's see
    "0x2cf0e11b0d406af92666c567641012ec19aecc95",
    "0xa4d20280bad6d03816129377b1ff6b38e1c5bf52"
]

results = []
for i, addr in enumerate(MINERS):
    data = gen_data(TASK_ID, i+1, CT)
    data["miner_address"] = addr
    results.append(data)

with open("realistic_task_027_data.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print("Saved to realistic_task_027_data.json")
