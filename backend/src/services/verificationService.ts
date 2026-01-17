/**
 * HealChain Backend - Verification Service
 * Implements Algorithm 5 from BTP Report Section 4.6
 * 
 * M5: Miner Verification Feedback (Consensus)
 */

import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";

/**
 * M5: Submit miner verification vote
 * 
 * Algorithm 5 from BTP Report:
 * Miner verifies candidate block and votes VALID/INVALID
 */
export async function submitVerification(
  taskID: string,
  minerAddress: string,
  verdict: "VALID" | "INVALID",
  signature?: string
) {
  // Check if task exists and is in verification phase
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: true,
      block: true
    }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  if (task.status !== TaskStatus.REVEAL_OPEN && task.status !== TaskStatus.VERIFIED) {
    throw new Error(`Task ${taskID} is not in verification phase`);
  }

  // Check if miner is registered
  const miner = task.miners.find(m => m.address.toLowerCase() === minerAddress.toLowerCase());
  if (!miner) {
    throw new Error(`Miner ${minerAddress} not registered for task ${taskID}`);
  }

  // Check if block exists
  if (!task.block) {
    throw new Error(`No candidate block for task ${taskID}`);
  }

  // Check if already voted
  const existing = await prisma.verification.findUnique({
    where: {
      taskID_minerAddress: {
        taskID,
        minerAddress: minerAddress.toLowerCase()
      }
    }
  });

  if (existing) {
    throw new Error(`Miner ${minerAddress} already voted for task ${taskID}`);
  }

  // Store verification vote
  const verification = await prisma.verification.create({
    data: {
      taskID,
      minerAddress: minerAddress.toLowerCase(),
      verdict,
      signature: signature || null
    }
  });

  return verification;
}

/**
 * M5: Get consensus result
 * 
 * Checks if majority of miners voted VALID
 * Algorithm 5: valid_votes ≥ (50% × miners)
 */
export async function getConsensusResult(taskID: string): Promise<{
  approved: boolean;
  validVotes: number;
  invalidVotes: number;
  totalMiners: number;
  majorityRequired: number;
}> {
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: true,
      verifications: true
    }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  const totalMiners = task.miners.length;
  const majorityRequired = Math.ceil(totalMiners * 0.5); // 50% majority

  const validVotes = task.verifications.filter(v => v.verdict === "VALID").length;
  const invalidVotes = task.verifications.filter(v => v.verdict === "INVALID").length;

  const approved = validVotes >= majorityRequired;

  return {
    approved,
    validVotes,
    invalidVotes,
    totalMiners,
    majorityRequired
  };
}

/**
 * Get all verifications for a task
 */
export async function getVerifications(taskID: string) {
  return prisma.verification.findMany({
    where: { taskID },
    include: {
      miner: {
        select: {
          address: true
        }
      }
    }
  });
}
