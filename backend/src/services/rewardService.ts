import { rewardDistribution } from "../contracts/rewardDistribution.js";
import { prisma } from "../config/database.config.js";

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
  try {
    const tx = await rewardDistribution["distribute(string)"](taskID);
    return tx;
  } catch (strictErr: any) {
    const task = await prisma.task.findUnique({
      where: { taskID },
      include: {
        miners: {
          select: { address: true },
        },
      },
    });
    const miners = (task?.miners || []).map((m) => String(m.address));
    if (miners.length === 0) {
      throw new Error(
        `Strict distribute failed (${
          strictErr?.shortMessage || strictErr?.message || strictErr
        }) and no miners available for legacy distribute(taskID, miners).`
      );
    }

    const tx = await rewardDistribution["distribute(string,address[])"](
      taskID,
      miners
    );
    return tx;
  }
}
