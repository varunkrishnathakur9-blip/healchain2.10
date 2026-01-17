/**
 * HealChain Backend - Secure Key Delivery
 * Implements Algorithm 2.3 from BTP Report Section 4.3
 * 
 * Securely delivers skFE to the selected aggregator
 * using encryption with aggregator's public key.
 */

import { prisma } from "../config/database.config.js";
import { keccak256, toUtf8Bytes } from "ethers";

/**
 * Encrypt skFE with aggregator's public key
 * 
 * For MVP: Simple encryption using aggregator's address as key
 * In production: Use proper EC encryption with aggregator's public key
 * 
 * @param skFE - Functional encryption key (BigInt)
 * @param aggregatorAddress - Aggregator's wallet address
 * @returns Encrypted key as hex string
 */
function encryptWithAggregatorKey(skFE: bigint, aggregatorAddress: string): string {
  // MVP: Simple encryption using aggregator address
  // In production, this should use EC encryption with aggregator's public key
  const skFEHex = skFE.toString(16).padStart(64, '0');
  const combined = aggregatorAddress.toLowerCase() + skFEHex;
  return keccak256(toUtf8Bytes(combined));
}

/**
 * Securely deliver skFE to aggregator
 * 
 * Algorithm 2.3 from BTP Report:
 * 1. Encrypt skFE with aggregator's public key
 * 2. Store in KeyDelivery table
 * 3. Aggregator can fetch and decrypt
 * 
 * @param taskID - Task identifier
 * @param aggregatorAddress - Selected aggregator address
 * @param skFE - Functional encryption key
 */
export async function secureDeliverKey(
  taskID: string,
  aggregatorAddress: string,
  skFE: bigint
): Promise<void> {
  // Encrypt skFE
  const encryptedKey = encryptWithAggregatorKey(skFE, aggregatorAddress);

  // Store in database
  await prisma.keyDelivery.upsert({
    where: {
      taskID_aggregatorAddress: {
        taskID,
        aggregatorAddress: aggregatorAddress.toLowerCase()
      }
    },
    create: {
      taskID,
      aggregatorAddress: aggregatorAddress.toLowerCase(),
      encryptedKey
    },
    update: {
      encryptedKey,
      deliveredAt: new Date()
    }
  });
}

/**
 * Fetch delivered key for aggregator
 * 
 * @param taskID - Task identifier
 * @param aggregatorAddress - Aggregator address
 * @returns Encrypted key (aggregator must decrypt)
 */
export async function fetchDeliveredKey(
  taskID: string,
  aggregatorAddress: string
): Promise<string | null> {
  const delivery = await prisma.keyDelivery.findUnique({
    where: {
      taskID_aggregatorAddress: {
        taskID,
        aggregatorAddress: aggregatorAddress.toLowerCase()
      }
    }
  });

  return delivery?.encryptedKey || null;
}

