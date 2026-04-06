import { createHash, createPrivateKey, createSign } from "crypto";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import { prisma } from "../dist/config/database.config.js";
import {
  computeCandidateHashHex,
  verifyCandidateBlockSignature,
} from "../dist/crypto/candidateSignature.js";
import { normalizeMinerPublicKey } from "../dist/utils/publicKey.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..", "..");

function toBase64Url(buf) {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function strip0x(v) {
  const s = String(v ?? "").trim();
  if (s.startsWith("0x") || s.startsWith("0X")) {
    return s.slice(2);
  }
  return s;
}

function hexToBuf32(hexLike, label) {
  const clean = strip0x(hexLike).toLowerCase();
  if (!/^[0-9a-f]+$/.test(clean)) {
    throw new Error(`${label} is not valid hex`);
  }
  const buf = Buffer.from(clean.length % 2 === 0 ? clean : `0${clean}`, "hex");
  if (buf.length > 32) {
    throw new Error(`${label} is larger than 32 bytes`);
  }
  if (buf.length === 32) return buf;
  const out = Buffer.alloc(32);
  buf.copy(out, 32 - buf.length);
  return out;
}

function readEnvFile(filePath) {
  const out = new Map();
  if (!fs.existsSync(filePath)) return out;
  const text = fs.readFileSync(filePath, "utf8");
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const k = line.slice(0, eq).trim();
    const v = line.slice(eq + 1).trim();
    out.set(k, v);
  }
  return out;
}

function parseScalar(raw) {
  const token = String(raw ?? "").trim();
  if (!token) throw new Error("AGGREGATOR_SK is empty");
  if (token.startsWith("0x") || token.startsWith("0X")) {
    return BigInt(token);
  }
  if (!/^[0-9]+$/.test(token)) {
    throw new Error("AGGREGATOR_SK must be decimal or 0x hex");
  }
  return BigInt(token);
}

function loadAggregatorSk() {
  if (process.env.AGGREGATOR_SK && String(process.env.AGGREGATOR_SK).trim()) {
    return parseScalar(process.env.AGGREGATOR_SK);
  }
  const envPath = path.join(REPO_ROOT, "aggregator", ".env");
  const envMap = readEnvFile(envPath);
  const fromFile = envMap.get("AGGREGATOR_SK");
  if (!fromFile) {
    throw new Error(
      "AGGREGATOR_SK not found in env or aggregator/.env. Set AGGREGATOR_SK before running recovery."
    );
  }
  return parseScalar(fromFile);
}

async function sha256FileHex(filePath) {
  return await new Promise((resolve, reject) => {
    const hash = createHash("sha256");
    const stream = fs.createReadStream(filePath);
    stream.on("error", reject);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolve(hash.digest("hex")));
  });
}

function readFilePrefix(filePath, bytes = 4096) {
  const fd = fs.openSync(filePath, "r");
  try {
    const buf = Buffer.alloc(bytes);
    const read = fs.readSync(fd, buf, 0, bytes, 0);
    return buf.slice(0, read).toString("utf8");
  } finally {
    fs.closeSync(fd);
  }
}

async function loadLatestArtifact(taskID) {
  const artifactDir = path.join(REPO_ROOT, "aggregator", "artifacts");
  if (!fs.existsSync(artifactDir)) {
    throw new Error(`Artifact directory not found: ${artifactDir}`);
  }

  const re = new RegExp(`^${taskID}_round(\\d+)\\.json$`);
  const matches = fs
    .readdirSync(artifactDir, { withFileTypes: true })
    .filter((d) => d.isFile() && re.test(d.name))
    .map((d) => {
      const m = re.exec(d.name);
      return {
        name: d.name,
        round: Number(m?.[1] ?? 0),
        fullPath: path.join(artifactDir, d.name),
      };
    })
    .sort((a, b) => b.round - a.round);

  if (matches.length === 0) {
    throw new Error(
      `No local model artifact found for ${taskID} in ${artifactDir}. Expected ${taskID}_roundN.json`
    );
  }

  const latest = matches[0];
  const artifactHash = await sha256FileHex(latest.fullPath);

  // Artifact JSON is canonical and starts with:
  // {"num_parameters":<n>,"weights":[...]}
  // Parse only header to avoid loading huge files.
  const prefix = readFilePrefix(latest.fullPath, 8192);
  const m = prefix.match(/"num_parameters"\s*:\s*(\d+)/);
  if (!m) {
    throw new Error(
      `Could not parse num_parameters from artifact header: ${latest.name}`
    );
  }
  const parsedNum = Number(m[1]);
  if (!Number.isFinite(parsedNum) || parsedNum <= 0) {
    throw new Error(`Invalid num_parameters in artifact header: ${m[1]}`);
  }

  return {
    round: latest.round,
    fullPath: latest.fullPath,
    artifactHash,
    numParameters: parsedNum,
  };
}

function computeModelHash({ modelLink, taskID, round, numParameters, artifactHash }) {
  const metaObj = {
    task_id: String(taskID),
    round: Number(round),
    num_parameters: Number(numParameters),
    model_type: "VectorModel",
    artifact_hash: String(artifactHash),
  };

  const metaBytes = Buffer.from(JSON.stringify(metaObj, Object.keys(metaObj).sort()), "utf8");
  return createHash("sha256")
    .update(Buffer.from(String(modelLink), "utf8"))
    .update(Buffer.from("|", "utf8"))
    .update(metaBytes)
    .digest("hex");
}

function signCandidateHashWithScalar({ hashHex, aggregatorPK, scalar }) {
  const pkNorm = normalizeMinerPublicKey(String(aggregatorPK));
  const [xHex, yHex] = pkNorm.split(",");
  if (!xHex || !yHex) {
    throw new Error("aggregatorPK format invalid");
  }
  const dHex = scalar.toString(16);
  const x = hexToBuf32(xHex, "aggregatorPK.x");
  const y = hexToBuf32(yHex, "aggregatorPK.y");
  const d = hexToBuf32(dHex, "AGGREGATOR_SK");

  const jwk = {
    kty: "EC",
    crv: "P-256",
    x: toBase64Url(x),
    y: toBase64Url(y),
    d: toBase64Url(d),
    ext: true,
  };

  const privateKey = createPrivateKey({ key: jwk, format: "jwk" });
  const digest = Buffer.from(strip0x(hashHex), "hex");
  const signer = createSign("sha256");
  signer.update(digest);
  signer.end();
  const sig = signer.sign({ key: privateKey, dsaEncoding: "ieee-p1363" });
  return sig.toString("hex");
}

async function main() {
  const taskID = String(process.argv[2] || "").trim();
  if (!taskID) {
    throw new Error("Usage: node scripts/recover_missing_block_candidate.mjs <taskID>");
  }

  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      block: true,
      miners: {
        select: { address: true, publicKey: true, proofVerified: true },
      },
      gradients: {
        select: { minerAddress: true, scoreCommit: true, createdAt: true },
      },
      verifications: {
        select: { candidateHash: true, verdict: true, createdAt: true },
      },
    },
  });

  if (!task) {
    throw new Error(`Task not found: ${taskID}`);
  }
  if (task.block) {
    throw new Error(`Task ${taskID} already has a Block row. Recovery is only for missing block.`);
  }
  if (!task.aggregatorAddress) {
    throw new Error(`Task ${taskID} has no selected aggregator`);
  }
  if (!task.initialModelLink) {
    throw new Error(`Task ${taskID} has no initialModelLink (used as candidate modelLink)`);
  }

  const uniqueHashes = Array.from(
    new Set(
      task.verifications
        .map((v) => String(v.candidateHash || "").trim().toLowerCase())
        .filter((v) => /^[0-9a-f]{64}$/.test(v))
    )
  );
  if (uniqueHashes.length !== 1) {
    throw new Error(
      `Expected exactly 1 candidateHash in verifications, got ${uniqueHashes.length}: ${JSON.stringify(uniqueHashes)}`
    );
  }
  const candidateHashTarget = uniqueHashes[0];

  const minVerificationTs = task.verifications.reduce((min, v) => {
    const t = Math.floor(new Date(v.createdAt).getTime() / 1000);
    return Math.min(min, t);
  }, Number.MAX_SAFE_INTEGER);
  if (!Number.isFinite(minVerificationTs) || minVerificationTs <= 0) {
    throw new Error("No verification timestamps available for candidate timestamp search");
  }

  const aggregatorMiner = task.miners.find(
    (m) => String(m.address).toLowerCase() === String(task.aggregatorAddress).toLowerCase()
  );
  if (!aggregatorMiner?.publicKey) {
    throw new Error("Selected aggregator public key is missing from miner records");
  }
  const aggregatorPK = normalizeMinerPublicKey(String(aggregatorMiner.publicKey));

  const pkByAddress = new Map(
    task.miners
      .filter((m) => !!m.publicKey)
      .map((m) => [String(m.address).toLowerCase(), normalizeMinerPublicKey(String(m.publicKey))])
  );

  const tuples = [];
  for (const g of task.gradients) {
    const addr = String(g.minerAddress).toLowerCase();
    const pk = pkByAddress.get(addr);
    if (!pk) {
      throw new Error(`Missing public key mapping for gradient miner ${g.minerAddress}`);
    }
    tuples.push([pk, String(g.scoreCommit)]);
  }
  if (tuples.length === 0) {
    throw new Error(`No gradients found for ${taskID}; cannot reconstruct candidate participants`);
  }
  tuples.sort((a, b) => String(a[0]).localeCompare(String(b[0])));
  const participants = tuples.map((t) => t[0]);
  const scoreCommits = tuples.map((t) => t[1]);

  const artifact = await loadLatestArtifact(taskID);
  const modelLink = String(task.initialModelLink);
  const round = artifact.round;
  const modelHash = computeModelHash({
    modelLink,
    taskID,
    round,
    numParameters: artifact.numParameters,
    artifactHash: artifact.artifactHash,
  });

  // Search window:
  // candidate timestamp should be before first verification, typically within minutes.
  // Use a safe 24h window to tolerate clock drift/manual delay.
  const searchEnd = minVerificationTs;
  const searchStart = Math.max(0, minVerificationTs - 24 * 60 * 60);

  let found = null;
  outer: for (let ts = searchStart; ts <= searchEnd; ts++) {
    for (let ai = 0; ai <= 100; ai++) {
      const accuracy = ai / 100;
      const h = computeCandidateHashHex(
        taskID,
        round,
        modelHash,
        modelLink,
        accuracy,
        participants,
        scoreCommits,
        aggregatorPK,
        ts
      );
      if (h === candidateHashTarget) {
        found = { accuracy, candidateTimestamp: ts };
        break outer;
      }
    }
  }

  if (!found) {
    throw new Error(
      "Could not reconstruct candidate timestamp/accuracy from available data. " +
        "Try expanding the search logic or re-run aggregation for this task."
    );
  }

  const skA = loadAggregatorSk();
  const signatureA = signCandidateHashWithScalar({
    hashHex: candidateHashTarget,
    aggregatorPK,
    scalar: skA,
  });

  const signatureValid = verifyCandidateBlockSignature({
    taskID,
    round,
    modelHash,
    modelLink,
    accuracy: found.accuracy,
    participants,
    scoreCommits,
    aggregatorPK,
    candidateTimestamp: found.candidateTimestamp,
    candidateHash: candidateHashTarget,
    signatureA,
  });
  if (!signatureValid) {
    throw new Error(
      "Internal check failed: reconstructed signature does not verify. Recovery aborted."
    );
  }

  const created = await prisma.block.create({
    data: {
      taskID,
      round,
      modelHash,
      modelLink,
      accuracy: BigInt(Math.round(found.accuracy * 1_000_000)),
      candidateHash: candidateHashTarget,
      participants,
      scoreCommits,
      aggregatorPK,
      signatureA,
      artifactHash: artifact.artifactHash,
      modelMetadata: {
        task_id: taskID,
        round,
        num_parameters: artifact.numParameters,
        model_type: "VectorModel",
      },
      candidateTimestamp: BigInt(found.candidateTimestamp),
      status: "FINALIZED",
    },
  });

  console.log(
    JSON.stringify(
      {
        ok: true,
        taskID,
        blockID: created.id,
        recovered: {
          round,
          modelLink,
          modelHash,
          accuracy: found.accuracy,
          candidateHash: candidateHashTarget,
          candidateTimestamp: found.candidateTimestamp,
          participants: participants.length,
          scoreCommits: scoreCommits.length,
        },
      },
      null,
      2
    )
  );
}

main()
  .catch((e) => {
    console.error(`RECOVERY_ERROR: ${e?.message || e}`);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
