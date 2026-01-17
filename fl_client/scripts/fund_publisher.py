import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from web3 import Web3
from config.settings import RPC_URL

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Get the default account (has funds)
default_account = w3.eth.accounts[0] if w3.eth.accounts else w3.eth.default_account
publisher_address = "0x88525BdE5e667Ab53C499702B72c9Bda119EC85B"

print(f"Default Account: {default_account}")
print(f"Default Balance: {w3.eth.get_balance(default_account)} wei")
print(f"Publisher Address: {publisher_address}")
print(f"Publisher Balance: {w3.eth.get_balance(publisher_address)} wei")

# Fund the publisher account
if w3.eth.get_balance(default_account) > 0:
    # Send 1 ETH to publisher
    tx_hash = w3.eth.send_transaction({
        'from': default_account,
        'to': publisher_address,
        'value': w3.to_wei(1, 'ether')
    })
    print(f"Funding transaction sent: {tx_hash.hex()}")
    
    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}")
    print(f"New publisher balance: {w3.eth.get_balance(publisher_address)} wei")
else:
    print("❌ Default account has no funds to send")
