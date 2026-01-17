import { keccak256, solidityPacked } from "ethers";

/**
 * Verify commit–reveal equality
 * Used ONLY for off-chain sanity checks
 */
export function verifyCommitReveal(
  value: bigint,
  nonceHex: string,
  expectedCommit: string
): boolean {
  const computed = keccak256(
    solidityPacked(
      ["uint256", "bytes32"],
      [value, `0x${nonceHex}`]
    )
  );

  return computed === expectedCommit;
}
