from web3 import Web3
from utils.serialization import encode_score_uint

def reveal_score(
    w3: Web3,
    contract,
    task_id: str,
    score: float,
    nonce_hex: str,
    score_commit_hex: str,
    signer
):
    score_uint = encode_score_uint(score)
    nonce_bytes32 = bytes.fromhex(nonce_hex)
    score_commit_bytes = bytes.fromhex(score_commit_hex)

    if len(nonce_bytes32) != 32:
        raise ValueError("Nonce must be exactly 32 bytes")

    tx = contract.functions.revealScore(
        task_id,
        score_uint,
        nonce_bytes32,
        score_commit_bytes
    ).build_transaction({
        "from": signer.address,
        "nonce": w3.eth.get_transaction_count(signer.address),
        "chainId": w3.eth.chain_id,
        "gas": 200_000
    })

    signed = signer.sign_transaction(tx)
    return w3.eth.send_raw_transaction(signed.raw_transaction)
