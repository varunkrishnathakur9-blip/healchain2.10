import { prisma } from "../config/database.config.js";
import { blockPublisher } from "../contracts/blockPublisher.js";
import { TaskStatus } from "@prisma/client";
import { verifyCandidateBlockSignature } from "../crypto/candidateSignature.js";

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
  if (!blockPublisher) {
    throw new Error(
      "BLOCK_PUBLISHER_ADDRESS is not configured in backend environment. " +
      "Set it in backend/.env.development (or production env) to enable M6 publish."
    );
  }

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
  const b = block as any;
  if (!b.candidateHash || !b.signatureA || !b.aggregatorPK || b.candidateTimestamp == null) {
    throw new Error("Candidate block is incomplete for M6 publish");
  }

  const signatureOk = verifyCandidateBlockSignature({
    taskID,
    round: typeof b.round === "number" ? b.round : Number((task as any).currentRound ?? 1),
    modelHash: String(b.modelHash || modelHash),
    modelLink: String(b.modelLink || ""),
    accuracy: Number(b.accuracy) / 1_000_000,
    participants: Array.isArray(b.participants) ? b.participants.map((v: unknown) => String(v)) : [],
    scoreCommits: Array.isArray(b.scoreCommits) ? b.scoreCommits.map((v: unknown) => String(v)) : [],
    aggregatorPK: String(b.aggregatorPK),
    candidateTimestamp: b.candidateTimestamp,
    candidateHash: String(b.candidateHash),
    signatureA: String(b.signatureA),
  });
  if (!signatureOk) {
    throw new Error("Candidate signature verification failed");
  }

  // Strict M6 gating: require majority VALID on the current candidate hash.
  const verifications = await prisma.verification.findMany({
    where: {
      taskID,
      candidateHash: String(b.candidateHash),
    },
    select: { verdict: true },
  });
  const participantCount = Array.isArray(b.participants) ? b.participants.length : 0;
  const totalMiners = participantCount > 0 ? participantCount : miners.length;
  const majorityRequired = Math.ceil(totalMiners * 0.5);
  const validVotes = verifications.filter((v) => v.verdict === "VALID").length;
  if (validVotes < majorityRequired) {
    throw new Error(
      `Cannot publish: insufficient valid feedback (${validVotes}/${majorityRequired})`
    );
  }

  const toBytes32 = (value: string, label: string): `0x${string}` => {
    const raw = String(value || "").trim().toLowerCase().replace(/^0x/, "");
    if (!/^[0-9a-f]{64}$/.test(raw)) {
      throw new Error(`${label} must be 32-byte hex, got: ${value}`);
    }
    return `0x${raw}`;
  };

  const normalizedModelHash = toBytes32(modelHash, "modelHash");
  const normalizedScoreCommits = (scoreCommits || []).map((v, i) =>
    toBytes32(v, `scoreCommits[${i}]`)
  );
  const toAddress = (value: string, label: string): `0x${string}` => {
    const raw = String(value || "").trim();
    if (!/^0x[0-9a-fA-F]{40}$/.test(raw)) {
      throw new Error(`${label} must be address hex, got: ${value}`);
    }
    return raw.toLowerCase() as `0x${string}`;
  };

  const participantSource: string[] =
    Array.isArray(b.participants) && b.participants.length > 0
      ? b.participants.map((v: unknown) => String(v))
      : miners.map((v) => String(v));
  const normalizedParticipants = participantSource.map((v, i) =>
    toAddress(v, `participants[${i}]`)
  );
  if (normalizedParticipants.length == 0) {
    throw new Error("participants must not be empty for M6 publish");
  }
  if (normalizedParticipants.length !== normalizedScoreCommits.length) {
    throw new Error(
      `participants/scoreCommits length mismatch (${normalizedParticipants.length}/${normalizedScoreCommits.length})`
    );
  }

  // M6 on-chain publish through BlockPublisher contract.
  const tx = await blockPublisher.publishBlock(
    taskID,
    normalizedModelHash,
    accuracy,
    normalizedParticipants,
    normalizedScoreCommits
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
