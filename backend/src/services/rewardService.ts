import { escrow } from "../contracts/escrow.js";

/**
 * M7: Trigger reward distribution
 * TP + miners already revealed on-chain
 */
export async function distribute(
  taskID: string,
  miners: string[]
) {
  const tx = await escrow.distributeRewards(taskID, miners);
  return tx;
}
