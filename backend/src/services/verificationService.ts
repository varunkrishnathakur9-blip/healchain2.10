/**
 * HealChain Backend - Verification Service
 * Implements Algorithm 5 from BTP Report Section 4.6
 * 
 * M5: Miner Verification Feedback (Consensus)
 */

import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";
import { normalizeMinerPublicKey } from "../utils/publicKey.js";
import {
  canonicalFeedbackMessage,
  verifyFeedbackSignature,
} from "../crypto/feedbackSignature.js";
import { verifyCandidateBlockSignature } from "../crypto/candidateSignature.js";

/**
 * M5: Submit miner verification vote
 * 
 * Algorithm 5 from BTP Report:
 * Miner verifies candidate block and votes VALID/INVALID
 */
export async function submitVerification(
  taskID: string,
  minerAddress: string,
  minerPublicKey: string,
  candidateHash: string,
  verdict: "VALID" | "INVALID",
  reason: string,
  message?: string,
  signature?: string
) {
  const normalizedAddress = minerAddress.toLowerCase();
  const normalizedCandidateHash = String(candidateHash || "").trim();
  if (!normalizedCandidateHash) {
    throw new Error("candidateHash is required");
  }
  const minerPkRaw = String(minerPublicKey || "").trim();
  if (!minerPkRaw) {
    throw new Error("miner_pk is required");
  }
  const normalizedMinerPk = normalizeMinerPublicKey(minerPkRaw);
  if (typeof reason !== "string") {
    throw new Error("reason must be a string");
  }
  const reasonText = reason;
  if (!signature || typeof signature !== "string") {
    throw new Error("signature is required");
  }

  const canonicalMsg = canonicalFeedbackMessage(
    taskID,
    normalizedCandidateHash,
    verdict,
    reasonText,
    minerPkRaw
  ).toString("utf-8");

  // Ensure payload message (if provided) is exactly the canonical value.
  if (typeof message === "string" && message.length > 0 && message !== canonicalMsg) {
    throw new Error("message does not match canonical feedback payload");
  }

  const sigValid = verifyFeedbackSignature({
    taskID,
    candidateHash: normalizedCandidateHash,
    verdict,
    reason: reasonText,
    minerPk: minerPkRaw,
    signatureHex: signature,
  });
  if (!sigValid) {
    throw new Error("Invalid miner feedback signature");
  }

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

  // Verification belongs to the post-candidate, pre-publish phase.
  // Keep REVEAL_OPEN/VERIFIED for backward compatibility with tasks created
  // before status-alignment patches.
  if (
    task.status !== TaskStatus.AGGREGATING &&
    task.status !== TaskStatus.REVEAL_OPEN &&
    task.status !== TaskStatus.VERIFIED
  ) {
    throw new Error(`Task ${taskID} is not in verification phase`);
  }

  // Check if miner is registered
  const miner = task.miners.find(m => m.address.toLowerCase() === normalizedAddress);
  if (!miner) {
    throw new Error(`Miner ${minerAddress} not registered for task ${taskID}`);
  }
  if (!miner.publicKey) {
    throw new Error(`Miner ${minerAddress} has no registered public key`);
  }
  const registeredMinerPk = normalizeMinerPublicKey(miner.publicKey);
  if (registeredMinerPk !== normalizedMinerPk) {
    throw new Error("miner_pk does not match registered miner public key");
  }

  // Check if block exists
  if (!task.block) {
    throw new Error(`No candidate block for task ${taskID}`);
  }
  const block = task.block as any;

  if ((task.block as any).candidateHash && (task.block as any).candidateHash !== normalizedCandidateHash) {
    throw new Error("candidateHash does not match current candidate block");
  }

  const candidateParticipants = ((task.block as any).participants || []).map((v: string) =>
    normalizeMinerPublicKey(v)
  );
  if (candidateParticipants.length > 0 && !candidateParticipants.includes(normalizedMinerPk)) {
    throw new Error("Miner is not in candidate participant list");
  }

  // ------------------------------------------------------------------
  // Strict Algorithm-5 Step 1 (backend-side): verify aggregator signature
  // over HASH(B), with B canonicalized exactly as candidate construction.
  // ------------------------------------------------------------------
  if (!block.aggregatorPK || !block.signatureA || !block.candidateTimestamp) {
    throw new Error("Candidate block is missing aggregator signature fields");
  }

  const blockAccuracyScaled =
    typeof block.accuracy === "bigint"
      ? Number(block.accuracy)
      : Number(block.accuracy ?? 0);

  if (!Number.isFinite(blockAccuracyScaled)) {
    throw new Error("Candidate block has invalid accuracy");
  }

  const signatureValid = verifyCandidateBlockSignature({
    taskID: task.taskID,
    round:
      typeof block.round === "number"
        ? block.round
        : Number((task as any).currentRound ?? 1),
    modelHash: String(block.modelHash || ""),
    modelLink: String(block.modelLink || ""),
    accuracy: blockAccuracyScaled / 1_000_000,
    participants: Array.isArray(block.participants)
      ? block.participants.map((v: unknown) => String(v))
      : [],
    scoreCommits: Array.isArray(block.scoreCommits)
      ? block.scoreCommits.map((v: unknown) => String(v))
      : [],
    aggregatorPK: String(block.aggregatorPK || ""),
    candidateTimestamp: block.candidateTimestamp,
    candidateHash: String(block.candidateHash || ""),
    signatureA: String(block.signatureA || ""),
  });

  if (!signatureValid) {
    throw new Error("Invalid candidate block aggregator signature");
  }

  // ------------------------------------------------------------------
  // Strict Algorithm-5 Step 2 (backend-side): this miner's scoreCommit
  // must be present in B.scoreCommits.
  // ------------------------------------------------------------------
  const minerGradient = await prisma.gradient.findFirst({
    where: {
      taskID,
      minerAddress: normalizedAddress,
    },
    orderBy: { createdAt: "desc" },
    select: { scoreCommit: true },
  });

  if (!minerGradient?.scoreCommit) {
    throw new Error("missing scoreCommit for miner");
  }

  const blockScoreCommits = Array.isArray(block.scoreCommits)
    ? block.scoreCommits.map((v: unknown) => String(v))
    : [];

  if (!blockScoreCommits.includes(String(minerGradient.scoreCommit))) {
    throw new Error("missing scoreCommit");
  }

  // Check if already voted
  const existing = await prisma.verification.findUnique({
    where: {
      taskID_minerAddress_candidateHash: {
        taskID,
        minerAddress: normalizedAddress,
        candidateHash: normalizedCandidateHash,
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
      minerAddress: normalizedAddress,
      candidateHash: normalizedCandidateHash,
      verdict,
      reason: reasonText,
      message: canonicalMsg,
      signature
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
      block: true,
      verifications: true
    }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  const currentCandidateHash = (task.block as any)?.candidateHash || "";
  const verifications = currentCandidateHash
    ? task.verifications.filter(v => v.candidateHash === currentCandidateHash)
    : task.verifications;

  const participantCount = Array.isArray((task.block as any)?.participants)
    ? ((task.block as any).participants as string[]).length
    : 0;
  const totalMiners = participantCount > 0 ? participantCount : task.miners.length;
  const majorityRequired = Math.ceil(totalMiners * 0.5); // strict majority

  const validVotes = verifications.filter(v => v.verdict === "VALID").length;
  const invalidVotes = verifications.filter(v => v.verdict === "INVALID").length;

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
          address: true,
          publicKey: true,
        }
      }
    }
  });
}
