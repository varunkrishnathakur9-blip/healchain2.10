import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

REWARD_DISTRIBUTION_ADDRESS = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
ESCROW_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

reward_data = json.loads(
    (BASE / "abis" / "RewardDistribution.json").read_text()
)
ABI_REWARD = reward_data["abi"]
