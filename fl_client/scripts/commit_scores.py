import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from web3 import Web3
from config.settings import RPC_URL
from config.chain import ABI_REWARD, REWARD_DISTRIBUTION_ADDRESS
from state.local_store import load_state
from chain.wallet import load_wallet

w3 = Web3(Web3.HTTPProvider(RPC_URL))
signer = load_wallet()

contract = w3.eth.contract(
    address=Web3.to_checksum_address(REWARD_DISTRIBUTION_ADDRESS),
    abi=ABI_REWARD
)

state = load_state()

print("Available contract functions:")
functions = [func['name'] for func in contract.abi if func['type'] == 'function']
print(functions)

for task_id, data in state.items():
    if not data.get("committed", False):
        print(f"\n[M7] Committing score for {task_id}")
        print(f"  Score: {data['score']}")
        print(f"  Commit: {data['commit']}")
        
        # Check if there's a commitScore function
        if 'commitScore' in functions:
            try:
                tx = contract.functions.commitScore(
                    task_id,
                    data['commit']
                ).build_transaction({
                    "from": signer.address,
                    "nonce": w3.eth.get_transaction_count(signer.address),
                    "chainId": w3.eth.chain_id,
                    "gas": 200_000
                })
                
                signed = signer.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                print(f"  Commit transaction: {tx_hash.hex()}")
                
                # Wait for confirmation
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"  Confirmed in block: {receipt.blockNumber}")
                
                # Mark as committed
                state[task_id]["committed"] = True
                
            except Exception as e:
                print(f"  Error committing: {e}")
        else:
            print("  commitScore function not found - trying direct reveal...")
            
            # Try direct reveal
            try:
                from chain.reveal_tx import reveal_score
                tx_hash = reveal_score(
                    w3=w3,
                    contract=contract,
                    task_id=task_id,
                    score=data["score"],
                    nonce_hex=data["nonce"],
                    signer=signer
                )
                print(f"  Reveal transaction: {tx_hash.hex()}")
                state[task_id]["revealed"] = True
            except Exception as e:
                print(f"  Error revealing: {e}")

# Save updated state
from state.local_store import save_state
save_state(state)
print("\n✅ State updated")
