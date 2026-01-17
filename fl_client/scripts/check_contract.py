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

print(f"Checking contract at: {REWARD_DISTRIBUTION_ADDRESS}")

try:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REWARD_DISTRIBUTION_ADDRESS),
        abi=ABI_REWARD
    )
    
    print("✅ Contract loaded successfully")
    
    # Check available functions
    functions = [func['name'] for func in contract.abi if func['type'] == 'function']
    print(f"Available functions: {functions}")
    
    # Check if revealScore exists
    if 'revealScore' in functions:
        print("✅ revealScore function found")
    else:
        print("❌ revealScore function NOT found")
        
    # Try to call a simple function to test contract
    try:
        # Try to get some contract state or call a view function
        if 'getScoreCommits' in functions:
            commits = contract.functions.getScoreCommits('test_task_002').call()
            print(f"Score commits for test_task_002: {commits}")
        else:
            print("getScoreCommits function not found")
    except Exception as e:
        print(f"Error calling contract function: {e}")
        
except Exception as e:
    print(f"❌ Error loading contract: {e}")
