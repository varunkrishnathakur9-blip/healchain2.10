import { createPublicKey, createVerify, KeyObject } from "crypto";

type FeedbackVerifyInput = {
  taskID: string;
  candidateHash: string;
  verdict: "VALID" | "INVALID";
  reason: string;
  minerPk: string;
  signatureHex: string;
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

function _parsePublicKey(minerPk: string): KeyObject {
  const parts = (minerPk || "").split(",");
  if (parts.length !== 2) {
    throw new Error("miner_pk must be in x_hex,y_hex format");
  }

  const x = _hexToFixedBuffer(parts[0], 32, "miner_pk.x");
  const y = _hexToFixedBuffer(parts[1], 32, "miner_pk.y");

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
    throw new Error("signature contains non-hex characters");
  }
  const normalized = clean.length % 2 === 0 ? clean : `0${clean}`;
  const sig = Buffer.from(normalized, "hex");
  if (sig.length !== 64) {
    throw new Error("signature must be raw r||s hex (64 bytes for P-256)");
  }
  return sig;
}

export function canonicalFeedbackMessage(
  taskID: string,
  candidateHash: string,
  verdict: "VALID" | "INVALID",
  reason: string,
  minerPk: string
): Buffer {
  const fields = [
    String(taskID),
    String(candidateHash),
    String(verdict),
    String(reason),
    String(minerPk),
  ];
  return Buffer.from(fields.join("|"), "utf-8");
}

export function verifyFeedbackSignature(input: FeedbackVerifyInput): boolean {
  const message = canonicalFeedbackMessage(
    input.taskID,
    input.candidateHash,
    input.verdict,
    input.reason,
    input.minerPk
  );
  const publicKey = _parsePublicKey(input.minerPk);
  const signature = _parseRawSignature(input.signatureHex);

  const verifier = createVerify("sha256");
  verifier.update(message);
  verifier.end();
  return verifier.verify({ key: publicKey, dsaEncoding: "ieee-p1363" as const }, signature);
}

