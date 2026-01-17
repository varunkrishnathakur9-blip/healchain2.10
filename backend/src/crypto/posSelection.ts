/**
 * HealChain Backend - Proof of Stake (PoS) Aggregator Selection
 * Implements Algorithm 2.1 from BTP Report Section 4.3
 * 
 * Selects aggregator from registered miners based on their on-chain stakes
 * using deterministic weighted random selection.
 * 
 * IMPORTANT: Stakes are now validated from the StakeRegistry smart contract
 * to ensure proper PoS implementation with on-chain stake management.
 * 
 * The selection is deterministic: the same taskID with the same miners
 * will always select the same aggregator, ensuring consistency and
 * preventing manipulation.
 */

import { prisma } from "../config/database.config.js";
import { createHash } from "crypto";
import { getStakes, isMinerEligible, getMinStake, getAvailableStake } from "../contracts/stakeRegistry.js";

/**
 * Generate a deterministic random BigInt from a seed string
 * Uses SHA-256 hash to ensure deterministic randomness
 * 
 * @param seed - Seed string (e.g., taskID)
 * @param max - Maximum value (exclusive)
 * @returns Deterministic random BigInt in [0, max)
 */
function deterministicRandom(seed: string, max: bigint): bigint {
  // Create a hash of the seed
  const hash = createHash('sha256').update(seed).digest();
  
  // Convert hash bytes to BigInt
  // Use first 16 bytes (128 bits) to avoid overflow with large stakes
  let value = BigInt(0);
  for (let i = 0; i < 16 && i < hash.length; i++) {
    value = (value << 8n) | BigInt(hash[i]);
  }
  
  // Ensure value is positive and within range
  value = value < 0n ? -value : value;
  
  // Scale to [0, max) range
  return value % max;
}

/**
 * Select aggregator using Proof of Stake (PoS)
 * 
 * Algorithm 2.1 from BTP Report:
 * 1. Get miners with verified proofs (Algorithm 2 requirement)
 * 2. Validate miners have sufficient on-chain stakes
 * 3. Get on-chain stakes from StakeRegistry contract
 * 4. Calculate total stake
 * 5. Deterministic weighted random selection based on on-chain stakes
 * 
 * IMPORTANT: 
 * - Only considers miners with verified proofs (Algorithm 2 requirement)
 * - Only considers miners with eligible stakes (>= MIN_STAKE)
 * - Stakes are validated from on-chain StakeRegistry contract
 * 
 * The selection is deterministic: same taskID + same miners + same stakes = same aggregator.
 * This ensures:
 * - Consistency across multiple calls
 * - Verifiability (anyone can recompute the selection)
 * - Prevention of manipulation
 * - True PoS with on-chain stake validation
 * 
 * @param taskID - Task identifier (used as seed for deterministic selection)
 * @returns Selected miner address
 * @throws Error if no eligible miners found
 */
export async function selectAggregatorViaPoS(taskID: string): Promise<string> {
  // Check if StakeRegistry is configured
  const { stakeRegistry } = await import("../contracts/stakeRegistry.js");
  if (!stakeRegistry) {
    throw new Error(
      "StakeRegistry contract not configured. Please deploy StakeRegistry contract and set STAKE_REGISTRY_ADDRESS in environment variables."
    );
  }

  // Algorithm 2: Only consider miners with verified proofs
  const miners = await prisma.miner.findMany({
    where: { 
      taskID,
      proofVerified: true  // Algorithm 2: Only miners with verified proofs
    },
    orderBy: {
      address: 'asc' // Deterministic order for consistency
    }
  });

  if (miners.length === 0) {
    throw new Error("No miners with verified proofs registered for task (Algorithm 2)");
  }

  // Filter miners by on-chain eligibility (must have >= MIN_STAKE)
  const eligibleMiners: { address: string; stake: bigint }[] = [];
  const minerAddresses = miners.map(m => m.address);
  
  // Check eligibility for all miners in parallel
  const eligibilityChecks = await Promise.all(
    minerAddresses.map(async (address) => {
      const eligible = await isMinerEligible(address);
      return { address, eligible };
    })
  );

  // Filter to only eligible miners
  for (let i = 0; i < miners.length; i++) {
    const check = eligibilityChecks[i];
    if (check.eligible) {
      eligibleMiners.push({ address: miners[i].address, stake: BigInt(0) }); // Stake will be fetched next
    }
  }

  if (eligibleMiners.length === 0) {
    // Check minimum stake requirement
    const minStake = await getMinStake();
    throw new Error(
      `No eligible miners with sufficient stake found (Algorithm 2.1). ` +
      `Need at least ${minStake.toString()} wei staked on-chain. ` +
      `Found ${miners.length} miners with verified proofs, but none meet stake requirement.`
    );
  }

  // Get on-chain stakes for eligible miners
  const eligibleAddresses = eligibleMiners.map(m => m.address);
  const { stakes: onChainStakes, totalStake } = await getStakes(eligibleAddresses);

  // Validate we got stakes for all eligible miners
  if (onChainStakes.length !== eligibleMiners.length) {
    throw new Error(
      `Stake retrieval mismatch: expected ${eligibleMiners.length} stakes, got ${onChainStakes.length}`
    );
  }

  // Update miner stakes with on-chain values
  for (let i = 0; i < eligibleMiners.length; i++) {
    eligibleMiners[i].stake = onChainStakes[i];
  }

  // Calculate total stake (should match returned total, but recalculate for safety)
  const calculatedTotalStake = onChainStakes.reduce((sum, stake) => sum + stake, BigInt(0));

  if (calculatedTotalStake === 0n || totalStake === 0n) {
    throw new Error(
      "Total stake is zero. All eligible miners must have staked funds on-chain for PoS selection."
    );
  }

  // Use the on-chain total stake for consistency
  const finalTotalStake = totalStake > calculatedTotalStake ? totalStake : calculatedTotalStake;

  // Deterministic weighted random selection
  // Include stakes in seed to ensure selection changes if stakes change
  const stakeString = onChainStakes.map(s => s.toString()).join(',');
  const addressString = eligibleAddresses.map(a => a.toLowerCase()).join(',');
  const seed = `${taskID}:${addressString}:${stakeString}`;
  
  // Generate deterministic random number in [0, finalTotalStake)
  const random = deterministicRandom(seed, finalTotalStake);

  // Find miner based on weighted selection
  // Each miner's probability is proportional to their on-chain stake
  let cumulative = BigInt(0);
  for (let i = 0; i < eligibleMiners.length; i++) {
    cumulative += eligibleMiners[i].stake;
    if (random < cumulative) {
      // Update database with actual on-chain stake for record-keeping
      await prisma.miner.updateMany({
        where: {
          taskID,
          address: eligibleMiners[i].address.toLowerCase(),
        },
        data: {
          stake: eligibleMiners[i].stake,
        },
      });
      return eligibleMiners[i].address;
    }
  }

  // Fallback: return first eligible miner (should never reach here due to math)
  // This handles edge case where random == finalTotalStake (impossible due to modulo, but safety check)
  const selectedMiner = eligibleMiners[0];
  await prisma.miner.updateMany({
    where: {
      taskID,
      address: selectedMiner.address.toLowerCase(),
    },
    data: {
      stake: selectedMiner.stake,
    },
  });
  return selectedMiner.address;
}

/**
 * Get miner stake from on-chain StakeRegistry
 * @param minerAddress Address of the miner
 * @param taskID Optional task ID (for database lookup if needed)
 * @returns On-chain available stake (BigInt)
 */
export async function getMinerStake(minerAddress: string, taskID?: string): Promise<bigint> {
  try {
    // Get stake from on-chain StakeRegistry contract
    const stake = await getAvailableStake(minerAddress);
    
    // Optionally update database record if taskID provided
    if (taskID) {
      await prisma.miner.updateMany({
        where: {
          taskID,
          address: minerAddress.toLowerCase(),
        },
        data: {
          stake: stake,
        },
      });
    }
    
    return stake;
  } catch (error) {
    console.error(`Error getting on-chain stake for miner ${minerAddress}:`, error);
    // Return 0 if error (miner not eligible)
    return BigInt(0);
  }
}

