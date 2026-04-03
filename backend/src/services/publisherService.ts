import { prisma } from "../config/database.config.js";
import { blockPublisher } from "../contracts/blockPublisher.js";
import { TaskStatus } from "@prisma/client";
import { verifyCandidateBlockSignature } from "../crypto/candidateSignature.js";
import { normalizeMinerPublicKey } from "../utils/publicKey.js";

/**
 * M6: Publish block on-chain after verification
 */
export async function publishOnChain(
  taskID: string,
  _modelHash?: string,
  _accuracy?: bigint,
  _miners: string[] = [],
  _scoreCommits: string[] = []
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

  // Helpful guard: if this BlockPublisher already has a block for taskID,
  // strict contracts will reject republish ("Block exists").
  try {
    const meta = await (blockPublisher as any).getBlockMeta(taskID);
    const existingModelHash = String(meta?.[0] || "");
    if (existingModelHash && !/^0x0{64}$/i.test(existingModelHash)) {
      throw new Error(
        `Block already exists on current BlockPublisher for ${taskID}. ` +
        `Use a fresh BlockPublisher deployment for re-publish continuity fixes.`
      );
    }
  } catch (metaErr: any) {
    // If this read fails, continue and let publish path surface a precise error.
    // (Some legacy deployments may not expose getBlockMeta consistently.)
    if (
      typeof metaErr?.message === "string" &&
      metaErr.message.includes("Block already exists on current BlockPublisher")
    ) {
      throw metaErr;
    }
  }

  const publishableStatuses = new Set<TaskStatus>([
    TaskStatus.AGGREGATING,
    TaskStatus.VERIFIED,
    TaskStatus.REVEAL_OPEN,
  ]);
  if (!publishableStatuses.has(task.status as TaskStatus)) {
    throw new Error("Task not ready for publishing");
  }
  if (!task.aggregatorAddress) {
    throw new Error("Task has no selected aggregator. Cannot execute strict M6 publish.");
  }

  const b = block as any;
  if (
    !b.candidateHash ||
    !b.signatureA ||
    !b.aggregatorPK ||
    b.candidateTimestamp == null ||
    !b.modelHash ||
    !b.modelLink ||
    typeof b.round !== "number" ||
    b.round <= 0
  ) {
    throw new Error(
      "Candidate block is incomplete for strict M6 publish (round/modelLink/hash/signature/aggregatorPK required)"
    );
  }
  if (!Array.isArray(b.participants) || b.participants.length === 0) {
    throw new Error("Candidate block participants are missing for strict M6 publish");
  }
  if (!Array.isArray(b.scoreCommits) || b.scoreCommits.length === 0) {
    throw new Error("Candidate block scoreCommits are missing for strict M6 publish");
  }
  if (b.participants.length !== b.scoreCommits.length) {
    throw new Error(
      `Candidate block participants/scoreCommits mismatch (${b.participants.length}/${b.scoreCommits.length})`
    );
  }

  const signatureOk = verifyCandidateBlockSignature({
    taskID,
    round: b.round,
    modelHash: String(b.modelHash),
    modelLink: String(b.modelLink),
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
  const totalMiners = participantCount;
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

  // Canonical M6 source of truth is the signed candidate metadata in DB.
  const normalizedModelHash = toBytes32(String(b.modelHash), "modelHash");
  const normalizedAccuracy = BigInt(b.accuracy);
  const normalizedScoreCommits: `0x${string}`[] = b.scoreCommits.map((v: unknown, i: number) =>
    toBytes32(String(v), `scoreCommits[${i}]`)
  );
  const isAddressHex = (value: string): boolean =>
    /^0x[0-9a-fA-F]{40}$/.test(String(value || "").trim());

  // Build pk->address lookup so legacy candidate participants encoded as miner_pk
  // can still be published in strict M6 contracts expecting address[].
  const taskMiners = await prisma.miner.findMany({
    where: { taskID },
    select: { address: true, publicKey: true },
  });
  const pkToAddress = new Map<string, string>();
  for (const m of taskMiners) {
    if (!m.publicKey) continue;
    try {
      pkToAddress.set(normalizeMinerPublicKey(m.publicKey), m.address.toLowerCase());
    } catch {
      // Ignore malformed stored keys; they will fail mapping later if needed.
    }
  }

  const selectedAggregatorMiner = taskMiners.find(
    (m) => m.address.toLowerCase() === String(task.aggregatorAddress).toLowerCase()
  );
  if (!selectedAggregatorMiner?.publicKey) {
    throw new Error(
      "Selected aggregator public key is missing from miner registry; strict M6 identity binding failed"
    );
  }
  const normalizedCandidateAggregatorPK = normalizeMinerPublicKey(String(b.aggregatorPK));
  const normalizedSelectedAggregatorPK = normalizeMinerPublicKey(
    String(selectedAggregatorMiner.publicKey)
  );
  if (normalizedCandidateAggregatorPK !== normalizedSelectedAggregatorPK) {
    throw new Error(
      "Candidate aggregatorPK does not match selected task aggregator public key"
    );
  }

  const toAddress = (value: string, label: string): `0x${string}` => {
    const raw = String(value || "").trim();

    // Normal path: participant is already an EVM address.
    if (isAddressHex(raw)) {
      return raw.toLowerCase() as `0x${string}`;
    }

    // Legacy path: participant is miner_pk "x,y". Map it to registered miner address.
    try {
      const normalizedPk = normalizeMinerPublicKey(raw);
      const mapped = pkToAddress.get(normalizedPk);
      if (mapped && isAddressHex(mapped)) {
        return mapped.toLowerCase() as `0x${string}`;
      }
    } catch {
      // Fall through to throw below.
    }

    throw new Error(
      `${label} must be address hex or mappable miner_pk, got: ${value}`
    );
  };

  const participantSource: string[] = b.participants.map((v: unknown) => String(v));
  const normalizedParticipants = participantSource.map((v, i) =>
    toAddress(v, `participants[${i}]`)
  );
  const normalizedAggregator = toAddress(
    String((task as any).aggregatorAddress || ""),
    "aggregatorAddress"
  );
  if (normalizedParticipants.length == 0) {
    throw new Error("participants must not be empty for M6 publish");
  }
  if (normalizedParticipants.length !== normalizedScoreCommits.length) {
    throw new Error(
      `participants/scoreCommits length mismatch (${normalizedParticipants.length}/${normalizedScoreCommits.length})`
    );
  }

  // Strict M6 publish with explicit aggregator address to avoid
  // msg.sender/backend-relayer identity drift in on-chain rewards.
  let tx: any;
  try {
    tx = await (blockPublisher as any)[
      "publishBlock(string,bytes32,uint256,address,address[],bytes32[])"
    ](
      taskID,
      normalizedModelHash,
      normalizedAccuracy,
      normalizedAggregator,
      normalizedParticipants,
      normalizedScoreCommits
    );
  } catch (err: any) {
    const msg = String(err?.shortMessage || err?.message || err || "");
    const looksLikeAbiMismatch =
      msg.includes("missing revert data") || msg.includes("CALL_EXCEPTION");
    if (looksLikeAbiMismatch) {
      throw new Error(
        "Strict M6 publish requires BlockPublisher with explicit aggregator overload and metadata getters. " +
        "Current contract appears legacy/incompatible. Redeploy M6/M7 contracts and update BACKEND/FRONTEND addresses."
      );
    }
    throw err;
  }

  // Wait for mining so strict post-publish validation can run deterministically.
  const receipt = await tx.wait();
  if (!receipt || receipt.status !== 1n) {
    throw new Error("M6 publish transaction failed on-chain");
  }

  // Strict Algorithm-6 metadata verification on-chain.
  let meta: any;
  let onChainParticipants: string[] = [];
  let onChainScoreCommits: string[] = [];
  try {
    meta = await (blockPublisher as any).getBlockMeta(taskID);
    onChainParticipants = (await (blockPublisher as any).getParticipants(taskID)).map((v: unknown) =>
      String(v).toLowerCase()
    );
    onChainScoreCommits = (await (blockPublisher as any).getScoreCommits(taskID)).map((v: unknown) =>
      String(v).toLowerCase()
    );
  } catch {
    throw new Error(
      "Strict M6 metadata validation failed: BlockPublisher getters unavailable/incompatible. " +
      "Redeploy M6/M7 contracts with current BlockPublisher.sol."
    );
  }

  const onChainAggregator = String(meta?.[2] || "").toLowerCase();
  const onChainModelHash = String(meta?.[0] || "").toLowerCase();
  const onChainAccuracy = BigInt(meta?.[1] ?? 0);
  const expectedParticipants = normalizedParticipants.map((v) => v.toLowerCase());
  const expectedScoreCommits = normalizedScoreCommits.map((v: `0x${string}`) =>
    String(v).toLowerCase()
  );

  if (onChainAggregator !== normalizedAggregator.toLowerCase()) {
    throw new Error(
      `Strict M6 metadata mismatch: on-chain aggregator ${onChainAggregator} != expected ${normalizedAggregator.toLowerCase()}`
    );
  }
  if (onChainModelHash !== normalizedModelHash.toLowerCase()) {
    throw new Error(
      `Strict M6 metadata mismatch: on-chain modelHash ${onChainModelHash} != expected ${normalizedModelHash.toLowerCase()}`
    );
  }
  if (onChainAccuracy !== normalizedAccuracy) {
    throw new Error(
      `Strict M6 metadata mismatch: on-chain accuracy ${onChainAccuracy.toString()} != expected ${normalizedAccuracy.toString()}`
    );
  }
  if (onChainParticipants.length !== expectedParticipants.length) {
    throw new Error(
      `Strict M6 metadata mismatch: participants length ${onChainParticipants.length} != expected ${expectedParticipants.length}`
    );
  }
  for (let i = 0; i < expectedParticipants.length; i++) {
    if (onChainParticipants[i] !== expectedParticipants[i]) {
      throw new Error(
        `Strict M6 metadata mismatch at participants[${i}]: ${onChainParticipants[i]} != expected ${expectedParticipants[i]}`
      );
    }
  }
  if (onChainScoreCommits.length !== expectedScoreCommits.length) {
    throw new Error(
      `Strict M6 metadata mismatch: scoreCommits length ${onChainScoreCommits.length} != expected ${expectedScoreCommits.length}`
    );
  }
  for (let i = 0; i < expectedScoreCommits.length; i++) {
    if (onChainScoreCommits[i] !== expectedScoreCommits[i]) {
      throw new Error(
        `Strict M6 metadata mismatch at scoreCommits[${i}]: ${onChainScoreCommits[i]} != expected ${expectedScoreCommits[i]}`
      );
    }
  }

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
