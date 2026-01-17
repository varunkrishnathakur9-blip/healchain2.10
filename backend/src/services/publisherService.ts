import { prisma } from "../config/database.config.js";
import { escrow } from "../contracts/escrow.js";
import { TaskStatus } from "@prisma/client";

/**
 * M6: Publish block on-chain after verification
 */
export async function publishOnChain(
  taskID: string,
  modelHash: string,
  accuracy: bigint,
  miners: string[]
) {
  const task = await prisma.task.findUnique({ where: { taskID } });
  const block = await prisma.block.findUnique({ where: { taskID } });

  if (!task || !block || task.status !== TaskStatus.REVEAL_OPEN) {
    throw new Error("Task not ready for publishing");
  }

  // Smart contract enforces correctness
  const tx = await escrow.publishBlock(
    taskID,
    modelHash,
    accuracy,
    miners,
    [] // scoreCommits already known on-chain / not duplicated
  );

  await prisma.task.update({
    where: { taskID },
    data: {
      status: TaskStatus.REVEAL_CLOSED,
      publishTx: tx.hash
    }
  });

  return tx.hash;
}