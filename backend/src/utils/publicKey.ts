/**
 * Normalize miner public key format to canonical:
 *   x_hex,y_hex (lowercase, no 0x prefix)
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

