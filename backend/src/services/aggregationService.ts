import { prisma } from "../config/database.config.js";
import { TaskStatus, BlockStatus } from "@prisma/client";

type CandidateMetadata = {
  round?: number;
  modelLink?: string;
  candidateHash?: string;
  participants?: string[];
  scoreCommits?: string[];
  aggregatorPK?: string;
  signatureA?: string;
  artifactHash?: string;
  modelMetadata?: unknown;
  candidateTimestamp?: bigint;
};

/**
 * M4: Accept aggregated model metadata
 * Aggregation is fully off-chain (aggregator)
 */
export async function submitCandidate(
  taskID: string,
  modelHash: string,
  accuracy: bigint,
  metadata: CandidateMetadata = {}
) {
  const task = await prisma.task.findUnique({ where: { taskID } });

  if (!task || ![TaskStatus.OPEN, TaskStatus.AGGREGATING].includes(task.status as any)) {
    throw new Error(`Task not in aggregation phase (status=${task?.status ?? "missing"})`);
  }

  const existing = await prisma.block.findUnique({
    where: { taskID }
  });

  if (existing) {
    throw new Error("Candidate already submitted");
  }

  const block = await prisma.$transaction(async (tx) => {
    const created = await tx.block.create({
      data: {
        taskID,
        round: Number.isFinite(metadata.round as number)
          ? Number(metadata.round)
          : (task as any).currentRound ?? null,
        modelHash,
        modelLink: metadata.modelLink?.trim() || null,
        accuracy,
        candidateHash: metadata.candidateHash?.trim() || null,
        participants: Array.isArray(metadata.participants) ? metadata.participants : [],
        scoreCommits: Array.isArray(metadata.scoreCommits) ? metadata.scoreCommits : [],
        aggregatorPK: metadata.aggregatorPK?.trim() || null,
        signatureA: metadata.signatureA?.trim() || null,
        artifactHash: metadata.artifactHash?.trim() || null,
        modelMetadata: (metadata.modelMetadata ?? null) as any,
        candidateTimestamp: metadata.candidateTimestamp ?? null,
        status: BlockStatus.FINALIZED
      }
    });

    // Candidate submission starts M5 verification, not M7 reveal.
    const taskUpdate: any = { status: TaskStatus.AGGREGATING };
    if (typeof metadata.modelLink === "string" && metadata.modelLink.trim().length > 0) {
      // Persist latest global model link so next round starts from W_round.
      taskUpdate.initialModelLink = metadata.modelLink.trim();
    }

    await tx.task.update({
      where: { taskID },
      data: taskUpdate
    });

    return created;
  });

  return block;
}

/**
 * Algorithm 4 (Lines 35-40): Reset task for a new FL round
 * - Clears all existing gradients for the task
 * - Increments the current round counter
 * - Resets task status to OPEN to allow new submissions
 */
export async function resetRound(taskID: string, modelLink?: string) {
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

    // 2. Increment round, carry-forward model link (if provided), and reset status
    const taskUpdate: any = {
      currentRound: { increment: 1 },
      status: TaskStatus.OPEN
    };
    if (typeof modelLink === "string" && modelLink.trim().length > 0) {
      taskUpdate.initialModelLink = modelLink.trim();
    }

    const updatedTask = await tx.task.update({
      where: { taskID },
      data: taskUpdate
    });

    return updatedTask;
  });
}
