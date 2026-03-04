import { prisma } from "../config/database.config.js";
import { TaskStatus, GradientStatus } from "@prisma/client";

/**
 * M3: Store encrypted update metadata
 * Algorithm 3: Stores ciphertext (encrypted gradient) for aggregator decryption
 */
export async function submitGradient(input: {
  taskID: string;
  minerAddress: string;
  minerPublicKey?: string; // Public key used to sign the submission
  scoreCommit: string;
  encryptedHash: string;
  ciphertext?: string; // JSON array of EC points ["x_hex,y_hex", ...]
  signature?: string; // Miner signature for submission verification
}) {
  const normalizedAddress = input.minerAddress.toLowerCase();
  const normalizedPublicKey = input.minerPublicKey?.trim();

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
      minerAddress: normalizedAddress
    }
  });

  if (existing) {
    throw new Error("Gradient already submitted by this miner for this task");
  }

  if (!normalizedPublicKey) {
    throw new Error("miner_pk (public key) is required for gradient submission");
  }

  const miner = await prisma.miner.findUnique({
    where: {
      taskID_address: {
        taskID: input.taskID,
        address: normalizedAddress
      }
    },
    select: {
      publicKey: true
    }
  });
  if (!miner) {
    throw new Error(`Miner ${normalizedAddress} is not registered for task ${input.taskID}`);
  }

  // Enforce one unique keypair per miner and uniqueness across miners in same task.
  if (miner.publicKey && miner.publicKey !== normalizedPublicKey) {
    throw new Error(
      "Submitted miner_pk does not match registered publicKey for this miner. " +
      "Key rotation during a task is not allowed."
    );
  }

  const duplicateKeyMiner = await prisma.miner.findFirst({
    where: {
      taskID: input.taskID,
      publicKey: normalizedPublicKey,
      address: {
        not: normalizedAddress
      }
    },
    select: {
      address: true
    }
  });
  if (duplicateKeyMiner) {
    throw new Error(
      `miner_pk is already used by miner ${duplicateKeyMiner.address} in task ${input.taskID}. ` +
      "Each miner must use a unique keypair."
    );
  }

  // Backfill only for legacy rows where publicKey was missing.
  if (!miner.publicKey) {
    await prisma.miner.update({
      where: {
        taskID_address: {
          taskID: input.taskID,
          address: normalizedAddress
        }
      },
      data: {
        publicKey: normalizedPublicKey
      }
    });
  }

  return prisma.gradient.create({
    data: {
      taskID: input.taskID,
      minerAddress: normalizedAddress,
      scoreCommit: input.scoreCommit,
      encryptedHash: input.encryptedHash,
      ciphertext: input.ciphertext || null, // Store ciphertext if provided
      signature: input.signature || null, // Store signature if provided
      status: GradientStatus.COMMITTED
    }
  });
}
