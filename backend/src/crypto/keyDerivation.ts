/**
 * HealChain Backend - NDD-FE Key Derivation
 * Implements Algorithm 2: Key Derivation from BTP Report Section 4.3
 * 
 * Derives the functional encryption key (skFE) from:
 * - Publisher address
 * - Miner public keys
 * - Task ID
 * - Nonce (from M1 task creation)
 */

import { keccak256, toUtf8Bytes } from "ethers";
import { prisma } from "../config/database.config.js";

/**
 * Derive NDD-FE functional encryption key (skFE)
 * 
 * Algorithm 2.2 from BTP Report:
 * skFE = H(publisherAddr || minerPKs || taskID || nonce)
 * 
 * Where:
 * - publisherAddr: Task publisher's wallet address
 * - minerPKs: Sorted list of miner public keys (deterministic order)
 * - taskID: Unique task identifier
 * - nonce: Nonce from M1 task creation (nonceTP)
 * 
 * @param taskID - Task identifier
 * @returns skFE as BigInt (scalar in curve order)
 */
export async function deriveFunctionalEncryptionKey(taskID: string): Promise<bigint> {
  // Get task with miners
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: {
        orderBy: {
          address: 'asc' // Deterministic order
        }
      }
    }
  });

  if (!task) {
    throw new Error(`Task ${taskID} not found`);
  }

  if (!task.miners || task.miners.length === 0) {
    throw new Error(`No miners registered for task ${taskID}`);
  }

  // Collect miner public keys (must be present)
  const minerPublicKeys = task.miners
    .map(m => m.publicKey)
    .filter(pk => pk !== null && pk !== undefined);

  if (minerPublicKeys.length !== task.miners.length) {
    throw new Error(`Some miners missing public keys for task ${taskID}`);
  }

  // Build deterministic input string
  // Format: publisher || pk1 || pk2 || ... || taskID || nonce
  const inputParts = [
    task.publisher.toLowerCase(), // Normalize address
    ...minerPublicKeys.sort(), // Already sorted by address, but sort PKs for extra safety
    taskID,
    task.nonceTP
  ];

  const inputString = inputParts.join('||');

  // Hash to scalar (modulo curve order)
  // Using keccak256 (SHA-3) as specified in BTP report
  const hash = keccak256(toUtf8Bytes(inputString));
  
  // Convert to BigInt and reduce modulo curve order
  // secp256r1 curve order: 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
  const CURVE_ORDER = BigInt('0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551');
  const skFE = BigInt('0x' + hash.slice(2)) % CURVE_ORDER;

  // Ensure non-zero (very unlikely but check anyway)
  if (skFE === 0n) {
    throw new Error("Derived skFE is zero (extremely unlikely)");
  }

  return skFE;
}

/**
 * Validate that key derivation inputs are complete
 */
export async function validateKeyDerivationInputs(taskID: string): Promise<boolean> {
  const task = await prisma.task.findUnique({
    where: { taskID },
    include: {
      miners: true
    }
  });

  if (!task) return false;
  const minMinersRequired = task.minMiners || 3; // Default to 3 for legacy tasks
  if (!task.miners || task.miners.length < minMinersRequired) return false;
  if (!task.nonceTP) return false;

  // Check all miners have public keys
  const allHavePKs = task.miners.every(m => m.publicKey !== null && m.publicKey !== undefined);
  return allHavePKs;
}

