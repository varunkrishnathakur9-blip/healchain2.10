from web3 import Account
import os

def load_wallet():
    return Account.from_key(os.getenv("MINER_PRIVATE_KEY"))
