import { createHash, createPublicKey, createVerify, KeyObject } from "crypto";
import { normalizeMinerPublicKey } from "../utils/publicKey.js";

type CandidateSignatureInput = {
  taskID: string;
  round: number;
  modelHash: string;
  modelLink: string;
  accuracy: number;
  participants: string[];
  scoreCommits: string[];
  aggregatorPK: string;
  candidateTimestamp: bigint | number | string;
  candidateHash: string;
  signatureA: string;
};

function _strip0x(v: string): string {
  return v.startsWith("0x") || v.startsWith("0X") ? v.slice(2) : v;
}

function _hexToFixedBuffer(hex: string, len: number, label: string): Buffer {
  const clean = _strip0x((hex || "").trim());
  if (!/^[0-9a-fA-F]+$/.test(clean)) {
    throw new Error(`${label} contains non-hex characters`);
  }
  const normalized = clean.length % 2 === 0 ? clean : `0${clean}`;
  const raw = Buffer.from(normalized, "hex");
  if (raw.length > len) {
    throw new Error(`${label} is too large for P-256 coordinate size`);
  }
  if (raw.length === len) {
    return raw;
  }
  const out = Buffer.alloc(len);
  raw.copy(out, len - raw.length);
  return out;
}

function _toBase64Url(buf: Buffer): string {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function _parsePublicKey(pk: string): KeyObject {
  const normalized = normalizeMinerPublicKey(pk);
  const parts = normalized.split(",");
  if (parts.length !== 2) {
    throw new Error("aggregatorPK must be in x_hex,y_hex format");
  }

  const x = _hexToFixedBuffer(parts[0], 32, "aggregatorPK.x");
  const y = _hexToFixedBuffer(parts[1], 32, "aggregatorPK.y");

  const jwk = {
    kty: "EC",
    crv: "P-256",
    x: _toBase64Url(x),
    y: _toBase64Url(y),
    ext: true,
  };

  return createPublicKey({ key: jwk as any, format: "jwk" });
}

function _parseRawSignature(signatureHex: string): Buffer {
  const clean = _strip0x((signatureHex || "").trim());
  if (!/^[0-9a-fA-F]+$/.test(clean)) {
    throw new Error("signatureA contains non-hex characters");
  }
  const normalized = clean.length % 2 === 0 ? clean : `0${clean}`;
  const sig = Buffer.from(normalized, "hex");
  if (sig.length !== 64) {
    throw new Error("signatureA must be raw r||s hex (64 bytes for P-256)");
  }
  return sig;
}

function _normalizeDigestHex(input: string, field: string): string {
  const clean = _strip0x((input || "").trim()).toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(clean)) {
    throw new Error(`${field} must be a 32-byte hex digest`);
  }
  return clean;
}

export function canonicalCandidateBlockMessage(
  taskID: string,
  round: number,
  modelHash: string,
  modelLink: string,
  accuracy: number,
  participants: string[],
  scoreCommits: string[],
  aggregatorPK: string,
  candidateTimestamp: bigint | number | string
): Buffer {
  const fields = [
    String(taskID),
    String(round),
    String(modelHash),
    String(modelLink),
    `${Number(accuracy).toFixed(8)}`,
    participants.map((v) => String(v)).join(","),
    scoreCommits.map((v) => String(v)).join(","),
    String(aggregatorPK),
    String(candidateTimestamp),
  ];
  return Buffer.from(fields.join("|"), "utf-8");
}

export function computeCandidateHashHex(
  taskID: string,
  round: number,
  modelHash: string,
  modelLink: string,
  accuracy: number,
  participants: string[],
  scoreCommits: string[],
  aggregatorPK: string,
  candidateTimestamp: bigint | number | string
): string {
  const canonical = canonicalCandidateBlockMessage(
    taskID,
    round,
    modelHash,
    modelLink,
    accuracy,
    participants,
    scoreCommits,
    aggregatorPK,
    candidateTimestamp
  );
  return createHash("sha256").update(canonical).digest("hex");
}

export function verifyCandidateBlockSignature(input: CandidateSignatureInput): boolean {
  const normalizedAggregatorPK = normalizeMinerPublicKey(input.aggregatorPK);
  const normalizedCandidateHash = _normalizeDigestHex(
    input.candidateHash,
    "candidateHash"
  );

  const recomputedHash = computeCandidateHashHex(
    input.taskID,
    Number(input.round),
    String(input.modelHash),
    String(input.modelLink),
    Number(input.accuracy),
    Array.isArray(input.participants) ? input.participants.map((v) => String(v)) : [],
    Array.isArray(input.scoreCommits) ? input.scoreCommits.map((v) => String(v)) : [],
    normalizedAggregatorPK,
    input.candidateTimestamp
  );

  if (recomputedHash !== normalizedCandidateHash) {
    return false;
  }

  const publicKey = _parsePublicKey(normalizedAggregatorPK);
  const signature = _parseRawSignature(input.signatureA);
  const msg = Buffer.from(normalizedCandidateHash, "hex");

  const verifier = createVerify("sha256");
  verifier.update(msg);
  verifier.end();
  return verifier.verify(
    { key: publicKey, dsaEncoding: "ieee-p1363" as const },
    signature
  );
}

