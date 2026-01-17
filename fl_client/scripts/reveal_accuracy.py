import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from web3 import Web3
from config.settings import RPC_URL
from config.chain import ABI_REWARD, REWARD_DISTRIBUTION_ADDRESS
from chain.wallet import load_wallet

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Use the default account as publisher (has funds)
publisher = w3.eth.account.from_key(os.getenv("BACKEND_PRIVATE_KEY", "0xb3f515c29e8287af974f57f5baf47c6a7ab1c21e0bd2e306f07e2d3e66a063b4"))

contract = w3.eth.contract(
    address=Web3.to_checksum_address(REWARD_DISTRIBUTION_ADDRESS),
    abi=ABI_REWARD
)

print("Publisher account:", publisher.address)
print("Publisher balance:", w3.eth.get_balance(publisher.address), "wei")

# Reveal accuracy for test tasks
for task_id in ['test_task_001', 'test_task_002']:
    print(f"\n[M7a] Revealing accuracy for {task_id}")
    
    # Mock accuracy and nonce (in real workflow, this comes from publisher)
    accuracy = 850000000000000000  # 0.85 as uint256
    nonce = "0x" + "00" * 32  # Mock nonce
    commit_hash = "0x" + "00" * 32  # Mock commit hash
    
    try:
        tx = contract.functions.revealAccuracy(
            task_id,
            accuracy,
            nonce,
            commit_hash
        ).build_transaction({
            "from": publisher.address,
            "nonce": w3.eth.get_transaction_count(publisher.address),
            "chainId": w3.eth.chain_id,
            "gas": 200_000
        })
        
        signed = publisher.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Transaction: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"  Confirmed in block: {receipt.blockNumber}")
        
    except Exception as e:
        print(f"  Error: {e}")

print("\n✅ Accuracy reveal completed")
