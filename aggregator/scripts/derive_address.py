from eth_keys import keys
import os
from dotenv import load_dotenv

load_dotenv()
sk_str = os.getenv("AGGREGATOR_SK")
if sk_str:
    # Convert to hex then to keys
    sk_int = int(sk_str)
    sk_hex = hex(sk_int)[2:].zfill(64)
    sk = keys.PrivateKey(bytes.fromhex(sk_hex))
    print(f"Address: {sk.public_key.to_address()}")
else:
    print("AGGREGATOR_SK not found")
