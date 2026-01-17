// src/contracts/stakeRegistry.ts
import { JsonRpcProvider, Contract, Wallet } from "ethers";
import { env } from "../config/env.js";

import stakeRegistryArtifact from "../../../contracts/artifacts/src/StakeRegistry.sol/StakeRegistry.json" with { type: "json" };

const provider = new JsonRpcProvider(env.RPC_URL);
const signer = new Wallet(env.BACKEND_PRIVATE_KEY, provider);

const STAKE_REGISTRY_ADDRESS = env.STAKE_REGISTRY_ADDRESS;

// Only create contract instance if address is configured
export const stakeRegistry = STAKE_REGISTRY_ADDRESS
  ? new Contract(
      STAKE_REGISTRY_ADDRESS,
      stakeRegistryArtifact.abi,
      signer
    )
  : null;

/**
 * Get available stake for a miner (for PoS selection)
 * @param minerAddress Address of the miner
 * @returns Available stake amount (BigInt)
 */
export async function getAvailableStake(minerAddress: string): Promise<bigint> {
  if (!stakeRegistry) {
    console.warn('StakeRegistry contract not configured. Returning 0 stake.');
    return BigInt(0);
  }
  try {
    const stake = await stakeRegistry.getAvailableStake(minerAddress);
    return BigInt(stake.toString());
  } catch (error) {
    console.error(`Error getting stake for miner ${minerAddress}:`, error);
    return BigInt(0);
  }
}

/**
 * Check if miner is eligible for aggregator selection
 * @param minerAddress Address of the miner
 * @returns True if miner has at least minimum stake
 */
export async function isMinerEligible(minerAddress: string): Promise<boolean> {
  if (!stakeRegistry) {
    console.warn('StakeRegistry contract not configured. Returning false for eligibility.');
    return false;
  }
  try {
    return await stakeRegistry.isEligible(minerAddress);
  } catch (error) {
    console.error(`Error checking eligibility for miner ${minerAddress}:`, error);
    return false;
  }
}

/**
 * Get stakes for multiple miners (for PoS selection)
 * @param minerAddresses Array of miner addresses
 * @returns Object with stakes array and total stake
 */
export async function getStakes(minerAddresses: string[]): Promise<{
  stakes: bigint[];
  totalStake: bigint;
}> {
  if (!stakeRegistry) {
    console.warn('StakeRegistry contract not configured. Returning zero stakes.');
    return {
      stakes: minerAddresses.map(() => BigInt(0)),
      totalStake: BigInt(0),
    };
  }
  try {
    const result = await stakeRegistry.getStakes(minerAddresses);
    const stakes = result.stakes.map((s: any) => BigInt(s.toString()));
    const totalStake = BigInt(result.totalTotalStake.toString());
    return { stakes, totalStake };
  } catch (error) {
    console.error(`Error getting stakes for miners:`, error);
    // Return zeros if error
    return {
      stakes: minerAddresses.map(() => BigInt(0)),
      totalStake: BigInt(0),
    };
  }
}

/**
 * Get full stake information for a miner
 * @param minerAddress Address of the miner
 * @returns Stake information object
 */
export async function getStakeInfo(minerAddress: string): Promise<{
  availableStake: bigint;
  totalStake: bigint;
  pendingWithdrawal: bigint;
  unlockTime: bigint;
}> {
  if (!stakeRegistry) {
    console.warn('StakeRegistry contract not configured. Returning zero stake info.');
    return {
      availableStake: BigInt(0),
      totalStake: BigInt(0),
      pendingWithdrawal: BigInt(0),
      unlockTime: BigInt(0),
    };
  }
  try {
    const result = await stakeRegistry.getStake(minerAddress);
    return {
      availableStake: BigInt(result.availableStake.toString()),
      totalStake: BigInt(result.totalStake.toString()),
      pendingWithdrawal: BigInt(result.pendingWithdrawal.toString()),
      unlockTime: BigInt(result.unlockTime.toString()),
    };
  } catch (error) {
    console.error(`Error getting stake info for miner ${minerAddress}:`, error);
    return {
      availableStake: BigInt(0),
      totalStake: BigInt(0),
      pendingWithdrawal: BigInt(0),
      unlockTime: BigInt(0),
    };
  }
}

/**
 * Get minimum stake required
 * @returns Minimum stake amount (BigInt)
 */
export async function getMinStake(): Promise<bigint> {
  if (!stakeRegistry) {
    console.warn('StakeRegistry contract not configured. Returning 0 for minimum stake.');
    return BigInt(0);
  }
  try {
    const minStake = await stakeRegistry.MIN_STAKE();
    return BigInt(minStake.toString());
  } catch (error) {
    console.error(`Error getting minimum stake:`, error);
    return BigInt(0);
  }
}
