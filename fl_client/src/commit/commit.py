import os
from eth_hash.auto import keccak
from utils.serialization import encode_score_uint

def commit_score(score: float, task_id: str, miner_address: str):
    nonce = os.urandom(32)  # bytes32

    score_uint = encode_score_uint(score)

    commit = keccak(
        score_uint.to_bytes(32, "big") +
        nonce +
        task_id.encode("utf-8") +
        bytes.fromhex(miner_address[2:])
    )

    return commit.hex(), nonce.hex()
