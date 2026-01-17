import { prisma } from "../config/database.config.js";
import { TaskStatus } from "@prisma/client";
import { selectAggregatorViaPoS, getMinerStake } from "../crypto/posSelection.js";
import { deriveFunctionalEncryptionKey, validateKeyDerivationInputs } from "../crypto/keyDerivation.js";
import { secureDeliverKey } from "../crypto/keyDelivery.js";
import { verifyMinerProof } from "./minerProofVerification.js";
import { isMinerEligible, getMinStake, getAvailableStake } from "../contracts/stakeRegistry.js";

/**
 * M2: Register a miner for a task
 * Algorithm 2 from BTP Report Section 4.3
 * 
 * Algorithm 2 Requirements:
 * 1. Miner submits response with public key (pki) and proof (proofi)
 * 2. VerifyMinerProof(r.pki, r.proofi, taskPool[taskID].meta.D) must return TRUE
 * 3. Only if proof is valid, miner is added to validMiners
 * 4. Miner selection and key derivation proceed only after proof verification
 */
export async function registerMiner(
  taskID: string,
  address: string,
  publicKey?: string,
  stake?: bigint,
  proof?: string  // Algorithm 2: Miner proof (IPFS link or system proof)
) {
  // Check if task exists
  const task = await prisma.task.findUnique({
    where: { taskID }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  // Check if task is in a valid state for registration
  if (task.status !== TaskStatus.CREATED && task.status !== TaskStatus.OPEN) {
    throw new Error(`Task ${taskID} is not accepting miner registrations (status: ${task.status})`);
  }

  // Check if deadline has passed
  const now = BigInt(Math.floor(Date.now() / 1000));
  if (task.deadline < now) {
    throw new Error(`Task ${taskID} registration deadline has passed`);
  }

  // Algorithm 2: Verify miner proof (REQUIRED)
  if (!proof || proof.trim() === '') {
    throw new Error("Miner proof is required (Algorithm 2). Please provide IPFS link or system proof.");
  }

  // Algorithm 2: VerifyMinerProof(r.pki, r.proofi, taskPool[taskID].meta.D)
  const proofValid = await verifyMinerProof(
    publicKey || address,  // r.pki (miner public key)
    proof,                    // r.proofi (miner proof)
    task.dataset             // taskPool[taskID].meta.D (dataset requirements)
  );

  if (!proofValid) {
    throw new Error(`Miner proof verification failed (Algorithm 2). Proof must be valid IPFS link or system proof matching dataset requirements (${task.dataset}).`);
  }

  // Check if miner is already registered (using unique constraint)
  const existingMiner = await prisma.miner.findUnique({
    where: {
      taskID_address: {
        taskID,
        address: address.toLowerCase()
      }
    }
  });

  if (existingMiner) {
    throw new Error(`Miner ${address} is already registered for task ${taskID}`);
  }

  // Algorithm 2.1: Validate miner has sufficient on-chain stake for PoS selection
  // Check eligibility from StakeRegistry contract
  let onChainStake: bigint;
  let isEligible: boolean;
  
  try {
    onChainStake = await getAvailableStake(address);
    isEligible = await isMinerEligible(address);
  } catch (error) {
    console.warn(`Error checking on-chain stake for miner ${address}:`, error);
    // If contract call fails, warn but allow registration (may be network issue)
    // PoS selection will validate stakes again and fail if invalid
    onChainStake = BigInt(0);
    isEligible = false;
  }

  // Warn if miner is not eligible (but allow registration - PoS selection will filter)
  if (!isEligible) {
    const minStake = await getMinStake().catch(() => BigInt(0));
    console.warn(
      `Miner ${address} registered for task ${taskID} but may not be eligible for aggregator selection. ` +
      `On-chain stake: ${onChainStake.toString()} wei, required: ${minStake.toString()} wei. ` +
      `Miner will not be selected as aggregator unless stake is sufficient.`
    );
  }

  // Algorithm 2: Only create miner if proof is valid
  // Create miner registration with public key, on-chain stake, and verified proof
  // Use on-chain stake for record-keeping (stake parameter is ignored, always use on-chain value)
  const miner = await prisma.miner.create({
    data: {
      taskID,
      address: address.toLowerCase(),
      publicKey: publicKey || null,
      stake: onChainStake,        // Use on-chain stake from StakeRegistry
      proof: proof,                // Algorithm 2: Store miner proof
      proofVerified: true          // Algorithm 2: Mark proof as verified
    }
  });

  // Algorithm 2: Only proceed with miner selection and key derivation after proof verification
  // Auto-finalize miners if we have enough (>= task.minMiners) with verified proofs
  const currentMiners = await prisma.miner.findMany({
    where: { 
      taskID,
      proofVerified: true  // Only count miners with verified proofs
    }
  });

  // Get task-specific min miners requirement
  const minMinersRequired = task.minMiners || 3; // Default to 3 if not set (for legacy tasks)

  if (currentMiners.length >= minMinersRequired && task.status === TaskStatus.CREATED) {
    // Automatically finalize miners and select aggregator (Algorithm 2)
    // This only happens after all miners have verified proofs
    try {
      await finalizeMiners(taskID);
    } catch (err) {
      // If finalization fails, log but don't fail registration
      console.warn(`Failed to auto-finalize miners for task ${taskID}:`, err);
    }
  }

  return miner;
}

/**
 * M2: Finalize miners & select aggregator
 * Implements Algorithm 2 from BTP Report Section 4.3
 * 
 * Steps:
 * 1. PoS-based aggregator selection (Algorithm 2.1)
 * 2. NDD-FE key derivation (Algorithm 2.2)
 * 3. Secure key delivery (Algorithm 2.3)
 */
export async function finalizeMiners(taskID: string) {
  // Get task to access min/max miners requirements
  const task = await prisma.task.findUnique({
    where: { taskID }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  // Get task-specific min/max miners requirements
  const minMinersRequired = task.minMiners || 3; // Default to 3 if not set (for legacy tasks)
  const maxMinersAllowed = task.maxMiners || 5; // Default to 5 if not set (for legacy tasks)

  // Algorithm 2: Only consider miners with verified proofs
  const miners = await prisma.miner.findMany({
    where: { 
      taskID,
      proofVerified: true  // Algorithm 2: Only miners with verified proofs
    },
    orderBy: {
      address: 'asc' // Deterministic order
    }
  });

  if (miners.length < minMinersRequired) {
    throw new Error(`Insufficient miners with verified proofs (Algorithm 2). Need at least ${minMinersRequired}, have ${miners.length}`);
  }

  // Check if we exceed max miners (warn - aggregator will cap submissions during aggregation)
  if (miners.length > maxMinersAllowed) {
    console.warn(
      `Task ${taskID} has ${miners.length} miners with verified proofs, but maxMiners is set to ${maxMinersAllowed}. ` +
      `Aggregator will cap submissions at ${maxMinersAllowed} during aggregation.`
    );
  }

  // Step 1: PoS-based aggregator selection (Algorithm 2.1)
  // Note: All eligible miners can be selected as aggregator, but aggregation will cap at maxMiners
  const aggregatorAddress = await selectAggregatorViaPoS(taskID);

  // Step 2: Validate key derivation inputs
  const canDeriveKey = await validateKeyDerivationInputs(taskID);
  if (!canDeriveKey) {
    console.warn(`Cannot derive key for task ${taskID}: missing public keys or nonce`);
    // Continue without key derivation (fallback mode)
  }

  // Step 3: Derive NDD-FE key (Algorithm 2.2)
  let skFE: bigint | null = null;
  let keyDelivered = false;
  
  if (canDeriveKey) {
    try {
      skFE = await deriveFunctionalEncryptionKey(taskID);
      
      // Step 4: Secure key delivery (Algorithm 2.3)
      await secureDeliverKey(taskID, aggregatorAddress, skFE);
      keyDelivered = true;
    } catch (err) {
      console.warn(`Key derivation/delivery failed for task ${taskID}:`, err);
      // Continue without key derivation (fallback: aggregator uses env var)
    }
  }

  // Update task status and store aggregator
  await prisma.task.update({
    where: { taskID },
    data: {
      status: TaskStatus.OPEN,
      aggregatorAddress: aggregatorAddress.toLowerCase()
    }
  });

  return {
    aggregator: aggregatorAddress,
    minerCount: miners.length,
    keyDerived: skFE !== null,
    keyDelivered
  };
}