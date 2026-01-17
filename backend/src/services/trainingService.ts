import { prisma } from "../config/database.config.js";
import { TaskStatus, GradientStatus } from "@prisma/client";

/**
 * M3: Store encrypted update metadata
 * Algorithm 3: Stores ciphertext (encrypted gradient) for aggregator decryption
 */
export async function submitGradient(input: {
  taskID: string;
  minerAddress: string;
  scoreCommit: string;
  encryptedHash: string;
  ciphertext?: string; // JSON array of EC points ["x_hex,y_hex", ...]
  signature?: string; // Miner signature for submission verification
}) {
  const task = await prisma.task.findUnique({
    where: { taskID: input.taskID }
  });

  if (!task || task.status !== TaskStatus.OPEN) {
    throw new Error("Task not accepting updates");
  }

  // Check for existing submission from this miner
  const existing = await prisma.gradient.findFirst({
    where: {
      taskID: input.taskID,
      minerAddress: input.minerAddress.toLowerCase()
    }
  });

  if (existing) {
    throw new Error("Gradient already submitted by this miner for this task");
  }

  return prisma.gradient.create({
    data: {
      taskID: input.taskID,
      minerAddress: input.minerAddress.toLowerCase(),
      scoreCommit: input.scoreCommit,
      encryptedHash: input.encryptedHash,
      ciphertext: input.ciphertext || null, // Store ciphertext if provided
      signature: input.signature || null, // Store signature if provided
      status: GradientStatus.COMMITTED
    }
  });
}