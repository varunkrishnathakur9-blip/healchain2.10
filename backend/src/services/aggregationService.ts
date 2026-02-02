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

/**
 * Algorithm 4 (Lines 35-40): Reset task for a new FL round
 * - Clears all existing gradients for the task
 * - Increments the current round counter
 * - Resets task status to OPEN to allow new submissions
 */
export async function resetRound(taskID: string) {
  const task = await prisma.task.findUnique({ where: { taskID } });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  // Transaction to ensure atomicity
  return await prisma.$transaction(async (tx) => {
    // 1. Delete all gradients for this task
    await tx.gradient.deleteMany({
      where: { taskID }
    });

    // 2. Increment round and reset status
    const updatedTask = await tx.task.update({
      where: { taskID },
      data: {
        currentRound: { increment: 1 },
        status: TaskStatus.OPEN
      } as any
    });

    return updatedTask;
  });
}