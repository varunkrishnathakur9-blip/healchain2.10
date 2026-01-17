import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from web3 import Web3
from config.settings import RPC_URL
from chain.wallet import load_wallet

w3 = Web3(Web3.HTTPProvider(RPC_URL))
signer = load_wallet()

print(f"RPC URL: {RPC_URL}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Miner Address: {signer.address}")
print(f"Miner Balance: {w3.eth.get_balance(signer.address)} wei")

# Check if we're connected to the right network
try:
    latest_block = w3.eth.get_block('latest')
    print(f"Latest Block: {latest_block.number}")
    print("✅ Connected to blockchain")
except Exception as e:
    print(f"❌ Blockchain connection error: {e}")
