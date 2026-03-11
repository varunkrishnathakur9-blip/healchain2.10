import { prisma } from "../config/database.config.js";
import { TaskStatus, GradientStatus } from "@prisma/client";
import { normalizeMinerPublicKey } from "../utils/publicKey.js";

const HEX_POINT_RE = /^(0x)?[0-9a-fA-F]+,(0x)?[0-9a-fA-F]+$/;

type SparseCiphertextPayload = {
  format: "sparse";
  totalSize: number;
  nonzeroIndices: number[];
  values: string[];
  baseMask: string;
};

function isHexPointEncoding(value: unknown): value is string {
  return typeof value === "string" && HEX_POINT_RE.test(value.trim());
}

function parseAndValidateSparseCiphertext(raw: string): string {
  let parsed: any;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(
      "ciphertext must be a JSON object in sparse format: " +
      "{format,totalSize,nonzeroIndices,values,baseMask}"
    );
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("ciphertext must be a JSON object in sparse format");
  }

  if (parsed.format !== "sparse") {
    throw new Error("ciphertext.format must be 'sparse'");
  }

  const totalSize = parsed.totalSize;
  if (!Number.isInteger(totalSize) || totalSize <= 0) {
    throw new Error("ciphertext.totalSize must be a positive integer");
  }

  const nonzeroIndices = parsed.nonzeroIndices;
  if (!Array.isArray(nonzeroIndices)) {
    throw new Error("ciphertext.nonzeroIndices must be an array of integers");
  }

  const values = parsed.values ?? parsed.ciphertext;
  if (!Array.isArray(values)) {
    throw new Error("ciphertext.values must be an array of EC points");
  }

  const baseMask = parsed.baseMask;
  if (!isHexPointEncoding(baseMask)) {
    throw new Error("ciphertext.baseMask must be a valid EC point x_hex,y_hex");
  }

  if (nonzeroIndices.length !== values.length) {
    throw new Error("ciphertext nonzeroIndices/values length mismatch");
  }

  const seen = new Set<number>();
  for (const idx of nonzeroIndices) {
    if (!Number.isInteger(idx) || idx < 0 || idx >= totalSize) {
      throw new Error("ciphertext.nonzeroIndices contains out-of-range index");
    }
    if (seen.has(idx)) {
      throw new Error("ciphertext.nonzeroIndices contains duplicates");
    }
    seen.add(idx);
  }

  for (const point of values) {
    if (!isHexPointEncoding(point)) {
      throw new Error("ciphertext.values contains invalid EC point encoding");
    }
  }

  const normalized: SparseCiphertextPayload = {
    format: "sparse",
    totalSize,
    nonzeroIndices,
    values,
    baseMask,
  };

  // Store canonical sparse payload structure for downstream consumers.
  return JSON.stringify(normalized);
}

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
  ciphertext: string; // JSON array of EC points ["x_hex,y_hex", ...]
  signature?: string; // Miner signature for submission verification
}) {
  const normalizedAddress = input.minerAddress.toLowerCase();
  const normalizedPublicKey = input.minerPublicKey?.trim()
    ? normalizeMinerPublicKey(input.minerPublicKey)
    : undefined;

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

  if (typeof input.ciphertext !== "string" || !input.ciphertext.trim()) {
    throw new Error("ciphertext is required for gradient submission");
  }
  if (/mockpoint|0xmock/i.test(input.ciphertext)) {
    throw new Error(
      "Invalid ciphertext payload: mock point markers detected. " +
      "Client must submit real NDD-FE ciphertext."
    );
  }
  const normalizedCiphertext = parseAndValidateSparseCiphertext(input.ciphertext);

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
  const minerRegisteredPk = miner.publicKey
    ? (() => {
        try {
          return normalizeMinerPublicKey(miner.publicKey);
        } catch {
          return miner.publicKey.trim().toLowerCase();
        }
      })()
    : null;

  if (minerRegisteredPk && minerRegisteredPk !== normalizedPublicKey) {
    throw new Error(
      "Submitted miner_pk does not match registered publicKey for this miner. " +
      "Key rotation during a task is not allowed."
    );
  }

  const taskMiners = await prisma.miner.findMany({
    where: {
      taskID: input.taskID,
      address: {
        not: normalizedAddress
      }
    },
    select: {
      address: true,
      publicKey: true
    }
  });
  const duplicateKeyMiner = taskMiners.find((m) => {
    if (!m.publicKey) return false;
    try {
      return normalizeMinerPublicKey(m.publicKey) === normalizedPublicKey;
    } catch {
      return m.publicKey.trim().toLowerCase() === normalizedPublicKey;
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
      ciphertext: normalizedCiphertext, // Canonical sparse encrypted gradient payload
      signature: input.signature || null, // Store signature if provided
      status: GradientStatus.COMMITTED
    }
  });
}
