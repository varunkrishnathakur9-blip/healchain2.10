import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from web3 import Web3
from config.settings import RPC_URL
from config.chain import ABI_REWARD, REWARD_DISTRIBUTION_ADDRESS

w3 = Web3(Web3.HTTPProvider(RPC_URL))

contract = w3.eth.contract(
    address=Web3.to_checksum_address(REWARD_DISTRIBUTION_ADDRESS),
    abi=ABI_REWARD
)

# Check if we can call view functions
try:
    # Check if accuracy has been revealed for our test tasks
    for task_id in ['test_task_001', 'test_task_002']:
        print(f"\nChecking task: {task_id}")
        
        try:
            accuracy_revealed = contract.functions.accuracyRevealed(task_id).call()
            print(f"  Accuracy revealed: {accuracy_revealed}")
        except Exception as e:
            print(f"  Error checking accuracy revealed: {e}")
        
        try:
            rewards_distributed = contract.functions.rewardsDistributed(task_id).call()
            print(f"  Rewards distributed: {rewards_distributed}")
        except Exception as e:
            print(f"  Error checking rewards distributed: {e}")
            
        try:
            total_score = contract.functions.totalScore(task_id).call()
            print(f"  Total score: {total_score}")
        except Exception as e:
            print(f"  Error checking total score: {e}")

except Exception as e:
    print(f"Error checking contract: {e}")

print("\n✅ Task status check completed")
