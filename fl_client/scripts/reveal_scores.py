import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Add src directory to Python path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from web3 import Web3
from chain.wallet import load_wallet
from chain.reveal_tx import reveal_score
from config.chain import ABI_REWARD, REWARD_DISTRIBUTION_ADDRESS
from state.local_store import load_state
from config.settings import RPC_URL

w3 = Web3(Web3.HTTPProvider(RPC_URL))
signer = load_wallet()

contract = w3.eth.contract(
    address=Web3.to_checksum_address(REWARD_DISTRIBUTION_ADDRESS),
    abi=ABI_REWARD
)

state = load_state()

for task_id, data in state.items():
    if not data["revealed"]:
        try:
            tx_hash = reveal_score(
                w3=w3,
                contract=contract,
                task_id=task_id,
                score=data["score"],
                nonce_hex=data["nonce"],
                score_commit_hex=data["commit"],
                signer=signer
            )
            print(f"[M7] Reveal sent for {task_id}: {tx_hash.hex()}")
            
            # Update state to mark as revealed
            state[task_id]["revealed"] = True
            
        except Exception as e:
            print(f"[WARN] Failed to reveal {task_id}: {e}")

# Save updated state
from state.local_store import save_state
save_state(state)
print("✅ State updated")
