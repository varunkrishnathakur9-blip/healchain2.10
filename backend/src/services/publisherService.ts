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

  const participantSource: string[] =
    Array.isArray(b.participants) && b.participants.length > 0
      ? b.participants.map((v: unknown) => String(v))
      : miners.map((v) => String(v));
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
  let backendSignerAddress = "";
  try {
    const runner: any = (blockPublisher as any).runner;
    if (runner && typeof runner.getAddress === "function") {
      backendSignerAddress = String(await runner.getAddress()).toLowerCase();
    }
  } catch {
    // Non-fatal; used only for clearer safety diagnostics.
  }
  try {
    tx = await (blockPublisher as any)[
      "publishBlock(string,bytes32,uint256,address,address[],bytes32[])"
    ](
      taskID,
      normalizedModelHash,
      accuracy,
      normalizedAggregator,
      normalizedParticipants,
      normalizedScoreCommits
    );
  } catch (err: any) {
    const msg = String(err?.shortMessage || err?.message || err || "");
    const looksLikeAbiMismatch =
      msg.includes("missing revert data") || msg.includes("CALL_EXCEPTION");
    if (!looksLikeAbiMismatch) {
      throw err;
    }

    // Legacy contract path (no explicit aggregator argument).
    // To preserve strict identity semantics, only allow this path when
    // backend signer is already the selected aggregator address.
    if (
      backendSignerAddress &&
      normalizedAggregator &&
      backendSignerAddress !== normalizedAggregator.toLowerCase()
    ) {
      throw new Error(
        `Legacy BlockPublisher fallback would set aggregator=msg.sender (${backendSignerAddress}) ` +
          `but selected task aggregator is ${normalizedAggregator}. ` +
          "Refusing publish to avoid reward-routing inconsistency. " +
          "Set BACKEND_PRIVATE_KEY to selected aggregator key, or redeploy contracts with explicit aggregator publish support."
      );
    }

    try {
      tx = await (blockPublisher as any)[
        "publishBlock(string,bytes32,uint256,address[],bytes32[])"
      ](
        taskID,
        normalizedModelHash,
        accuracy,
        normalizedParticipants,
        normalizedScoreCommits
      );
    } catch (legacyErr: any) {
      // Last fallback for very old contracts.
      tx = await (blockPublisher as any)[
        "publishBlock(string,bytes32,uint256,bytes32[])"
      ](taskID, normalizedModelHash, accuracy, normalizedScoreCommits);
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
