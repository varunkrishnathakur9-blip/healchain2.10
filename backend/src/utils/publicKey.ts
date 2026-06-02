/**
 * Normalize miner public key format to canonical:
 *   x_hex,y_hex (lowercase, no 0x prefix)
 *
 * This function intentionally does not left-pad coordinates because candidate
 * hashes are signed over the exact canonical string used by the aggregator.
 */
export function normalizeMinerPublicKey(input: string): string {
  if (!input || typeof input !== "string") {
    throw new Error("publicKey must be a non-empty string");
  }

  const parts = input.split(",");
  if (parts.length !== 2) {
    throw new Error("publicKey must be in 'x_hex,y_hex' format");
  }

  const normPart = (part: string) => {
    const trimmed = part.trim();
    const noPrefix = trimmed.toLowerCase().startsWith("0x")
      ? trimmed.slice(2)
      : trimmed;

    if (!/^[0-9a-fA-F]+$/.test(noPrefix)) {
      throw new Error("publicKey contains non-hex characters");
    }

    return noPrefix.toLowerCase();
  };

  return `${normPart(parts[0])},${normPart(parts[1])}`;
}

/**
 * Normalize a public key for identity comparison.
 *
 * EC coordinates are integers, so `30ff...` and `030ff...` can represent the
 * same P-256 x coordinate. Use this only for equality/lookups, not for
 * candidate hash recomputation.
 */
export function normalizeMinerPublicKeyIdentity(input: string): string {
  const normalized = normalizeMinerPublicKey(input);
  const parts = normalized.split(",");
  if (parts.length !== 2) {
    throw new Error("publicKey must be in 'x_hex,y_hex' format");
  }

  const padCoordinate = (value: string, label: string): string => {
    if (value.length > 64) {
      throw new Error(`${label} is too large for P-256 coordinate size`);
    }
    return value.padStart(64, "0");
  };

  return `${padCoordinate(parts[0], "publicKey.x")},${padCoordinate(parts[1], "publicKey.y")}`;
}
