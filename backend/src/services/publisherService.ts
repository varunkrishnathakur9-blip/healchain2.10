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
  miners: string[],
  scoreCommits: string[] = []
) {
  const task = await prisma.task.findUnique({ where: { taskID } });
  const block = await prisma.block.findUnique({ where: { taskID } });

  if (!task || !block) {
    throw new Error("Task not ready for publishing");
  }

  const publishableStatuses = new Set<TaskStatus>([
    TaskStatus.AGGREGATING,
    TaskStatus.VERIFIED,
    TaskStatus.REVEAL_OPEN,
  ]);
  if (!publishableStatuses.has(task.status as TaskStatus)) {
    throw new Error("Task not ready for publishing");
  }

  // Smart contract enforces correctness
  const tx = await escrow.publishBlock(
    taskID,
    modelHash,
    accuracy,
    miners,
    scoreCommits
  );

  await prisma.task.update({
    where: { taskID },
    data: {
      // M6 complete -> M7 reveal window opens.
      status: TaskStatus.REVEAL_OPEN,
      publishTx: tx.hash
    }
  });

  return tx.hash;
}
