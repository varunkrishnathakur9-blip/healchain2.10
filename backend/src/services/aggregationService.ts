import { prisma } from "../config/database.config.js";
import { TaskStatus, BlockStatus } from "@prisma/client";

/**
 * M4: Accept aggregated model metadata
 * Aggregation is fully off-chain (aggregator)
 */
export async function submitCandidate(
  taskID: string,
  modelHash: string,
  accuracy: bigint
) {
  const task = await prisma.task.findUnique({ where: { taskID } });

  if (!task || task.status !== TaskStatus.OPEN) {
    throw new Error("Task not in aggregation phase");
  }

  const existing = await prisma.block.findUnique({
    where: { taskID }
  });

  if (existing) {
    throw new Error("Candidate already submitted");
  }

  const block = await prisma.block.create({
    data: {
      taskID,
      modelHash,
      accuracy,
      status: BlockStatus.FINALIZED
    }
  });

  await prisma.task.update({
    where: { taskID },
    data: { status: TaskStatus.REVEAL_OPEN }
  });

  return block;
}