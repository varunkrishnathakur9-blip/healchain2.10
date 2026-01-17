from eth_account.messages import encode_defunct
from web3 import Web3

def verify_candidate(block, model_hash_expected):
    if block["modelHash"] != model_hash_expected:
        return False
    return True
