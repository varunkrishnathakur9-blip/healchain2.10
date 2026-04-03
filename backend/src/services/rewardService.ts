import { rewardDistribution } from "../contracts/rewardDistribution.js";
import { prisma } from "../config/database.config.js";
import { escrow } from "../contracts/escrow.js";
import { formatEther } from "ethers";

function normalizeAddress(addr: string): string {
  return String(addr || "").toLowerCase();
}

async function getMinerRevealScore(taskID: string, minerAddress: string): Promise<bigint> {
  if (!rewardDistribution) return 0n;
  try {
    const reveal = await rewardDistribution.minerReveals(taskID, minerAddress);
    const score = (reveal as any)?.score ?? (Array.isArray(reveal) ? reveal[0] : 0n);
    return typeof score === "bigint" ? score : BigInt(score || 0);
  } catch {
    return 0n;
  }
}

/**
 * Backfill Reward rows from on-chain M7 state.
 * - Useful when distribution is triggered directly from frontend wallet.
 * - Safe to call repeatedly; it replaces per-task reward rows atomically.
 */
export async function syncRewardRowsFromChain(taskID: string) {
  if (!rewardDistribution) return { synced: false, reason: "REWARD_CONTRACT_ADDRESS not configured" };

  let distributedOnChain = false;
  try {
    distributedOnChain = (await rewardDistribution.rewardsDistributed(taskID)) === true;
  } catch (error: any) {
    return {
      synced: false,
      reason: `Could not read rewardsDistributed(${taskID}): ${error?.message || error}`,
    };
  }

  if (!distributedOnChain) {
    return { synced: false, reason: "Rewards not distributed on-chain yet" };
  }

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
    return { synced: false, reason: "No miners found for task" };
  }

  // Collect actual payout amounts from Escrow RewardReleased events.
  const payoutsByMiner = new Map<string, bigint>();
  let txHashFromEvents: string | null = null;

  try {
    const filter = escrow.filters.RewardReleased(taskID);
    const logs = await escrow.queryFilter(filter, 0, "latest");

    for (const log of logs) {
      const recipient = String((log as any)?.args?.recipient || (log as any)?.args?.[1] || "");
      const amount = (log as any)?.args?.amount ?? (log as any)?.args?.[2] ?? 0n;
      const key = normalizeAddress(recipient);
      const prev = payoutsByMiner.get(key) || 0n;
      payoutsByMiner.set(key, prev + (typeof amount === "bigint" ? amount : BigInt(amount || 0)));
      txHashFromEvents = log.transactionHash || txHashFromEvents;
    }
  } catch {
    // Keep best-effort sync even if event query fails.
  }

  const now = new Date();
  const rows = await Promise.all(
    miners.map(async (minerAddress) => {
      const minerKey = normalizeAddress(minerAddress);
      const amountWei = payoutsByMiner.get(minerKey) || 0n;
      const score = await getMinerRevealScore(taskID, minerAddress);

      return {
        id: `${taskID}_${minerKey}`,
        taskID,
        minerAddress,
        score,
        amountETH: formatEther(amountWei),
        txHash: txHashFromEvents,
        status: "DISTRIBUTED",
        createdAt: now,
      };
    })
  );

  await prisma.$transaction(async (tx) => {
    await tx.reward.deleteMany({ where: { taskID } });
    await tx.reward.createMany({ data: rows });
  });

  return { synced: true, count: rows.length };
}

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
    // Wallet-triggered flows may bypass backend route, but when backend triggers M7c,
    // sync DB rows right after confirmation.
    try {
      await tx.wait();
      await syncRewardRowsFromChain(taskID);
    } catch {
      // Non-fatal: scheduler can backfill later.
    }
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
    try {
      await tx.wait();
      await syncRewardRowsFromChain(taskID);
    } catch {
      // Non-fatal: scheduler can backfill later.
    }
    return tx;
  }
}
