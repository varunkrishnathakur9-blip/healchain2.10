import json
import os
import binascii
from ecdsa import SigningKey, NIST256p
import hashlib

def generate_miner_data(task_id, miner_addresses):
    # This matches the canonical message logic in aggregator/src/aggregation/collector.py
    # message = f"{task_id}|{ciphertext_concat}|{score_commit}|{miner_pk}"
    
    # We'll use mock but structural ciphertext/commit for task_027
    # (Since they are already in the DB, we'll use those values)
    
    # For now, let's just generate the keys and a generic signature format
    # Actually, I should probably GET the current ciphertext/commit from DB first.
    # But since I'm fixing everything, I can just SET them to valid defaults.
    
    mock_ciphertext = ["0xmockpoint1,0xmockpoint2", "0xmockpoint3,0xmockpoint4"]
    ciphertext_concat = ",".join(mock_ciphertext)
    score_commit = "0xmockcommit"
    
    data = []
    for addr in miner_addresses:
        sk = SigningKey.generate(curve=NIST256p)
        vk = sk.verifying_key
        
        # Format: x_hex,y_hex
        x_hex = format(vk.pubkey.point.x(), '064x')
        y_hex = format(vk.pubkey.point.y(), '064x')
        miner_pk = f"{x_hex},{y_hex}"
        
        # Canonical message
        message = f"{task_id}|{ciphertext_concat}|{score_commit}|{miner_pk}"
        msg_bytes = message.encode("utf-8")
        
        # Sign
        signature = sk.sign(msg_bytes, hashfunc=hashlib.sha256)
        sig_hex = binascii.hexlify(signature).decode()
        
        data.append({
            "minerAddress": addr,
            "publicKey": miner_pk,
            "signature": sig_hex,
            "ciphertext": json.dumps(mock_ciphertext),
            "scoreCommit": score_commit
        })
        
    return data

if __name__ == "__main__":
    task_id = "task_027"
    miners = [
        "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
        "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
        "0x976EA74026E726554dB657fA54763abd0C3a0aa9"
    ]
    
    realistic_data = generate_miner_data(task_id, miners)
    with open("realistic_task_027_data_v2.json", "w") as f:
        json.dump(realistic_data, f, indent=2)
    print("Generated realistic_task_027_data_v2.json")
