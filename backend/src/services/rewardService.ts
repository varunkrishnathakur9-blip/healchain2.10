import { rewardDistribution } from "../contracts/rewardDistribution.js";

/**
 * M7: Trigger reward distribution
 * TP + miners already revealed on-chain
 */
export async function distribute(
  taskID: string
) {
  if (!rewardDistribution) {
    throw new Error(
      "REWARD_CONTRACT_ADDRESS is not configured. Deploy/configure RewardDistribution for strict Algorithm-7 M7c."
    );
  }

  // Strict Algorithm-7 path: participants are resolved on-chain from published block.
  const tx = await rewardDistribution["distribute(string)"](taskID);
  return tx;
}
