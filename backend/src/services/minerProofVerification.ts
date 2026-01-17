/**
 * HealChain Backend - Miner Proof Verification
 * Implements Algorithm 2: VerifyMinerProof function
 * 
 * Algorithm 2 Requirement (BTP Report Section 4.3):
 * VerifyMinerProof(r.pki, r.proofi, taskPool[taskID].meta.D)
 * 
 * Verifies that miner has valid proof for the dataset requirements (D)
 */

import { prisma } from "../config/database.config.js";

/**
 * Verify miner proof against task dataset requirements
 * 
 * Algorithm 2: VerifyMinerProof(r.pki, r.proofi, taskPool[taskID].meta.D)
 * 
 * @param publicKey - Miner's public key (r.pki)
 * @param proof - Miner's proof (r.proofi) - IPFS link or system proof
 * @param dataset - Task dataset requirements (D)
 * @returns true if proof is valid, false otherwise
 */
export async function verifyMinerProof(
  publicKey: string,
  proof: string,
  dataset: string
): Promise<boolean> {
  // Basic validation
  if (!proof || proof.trim() === '') {
    return false;
  }

  // Validate proof format
  // Proof can be:
  // 1. IPFS link: ipfs://Qm... or https://ipfs.io/ipfs/Qm...
  // 2. HTTP/HTTPS URL: https://...
  // 3. System proof (JSON string with validation data)
  
  const proofTrimmed = proof.trim();
  
  // Check if it's an IPFS link
  if (proofTrimmed.startsWith('ipfs://') || proofTrimmed.includes('/ipfs/')) {
    // Extract IPFS hash
    const ipfsHash = extractIPFSHash(proofTrimmed);
    if (!ipfsHash || ipfsHash.length < 10) {
      return false; // Invalid IPFS hash
    }
    
    // For now, accept valid IPFS format
    // In production, you might want to:
    // - Verify the IPFS content exists
    // - Check the content matches dataset requirements
    // - Validate proof structure
    return true;
  }
  
  // Check if it's an HTTP/HTTPS URL
  if (proofTrimmed.startsWith('http://') || proofTrimmed.startsWith('https://')) {
    try {
      const url = new URL(proofTrimmed);
      // Basic URL validation
      // In production, you might want to:
      // - Verify the URL is accessible
      // - Check the content matches dataset requirements
      return url.hostname.length > 0;
    } catch {
      return false; // Invalid URL
    }
  }
  
  // Check if it's a JSON system proof
  try {
    const proofData = JSON.parse(proofTrimmed);
    // Validate proof structure
    // Expected structure: { dataset: string, capabilities: string[], ... }
    if (proofData.dataset && proofData.dataset === dataset) {
      return true;
    }
    // If no dataset match, still accept if it's valid JSON with required fields
    if (proofData.capabilities && Array.isArray(proofData.capabilities)) {
      return true;
    }
  } catch {
    // Not JSON, continue to other checks
  }
  
  // For MVP: Accept any non-empty proof
  // In production, implement stricter validation based on your proof requirements
  return proofTrimmed.length > 0;
}

/**
 * Extract IPFS hash from various IPFS link formats
 */
function extractIPFSHash(proof: string): string | null {
  // Format 1: ipfs://Qm...
  if (proof.startsWith('ipfs://')) {
    return proof.substring(7);
  }
  
  // Format 2: https://ipfs.io/ipfs/Qm... or https://gateway.pinata.cloud/ipfs/Qm...
  const ipfsMatch = proof.match(/\/ipfs\/([a-zA-Z0-9]+)/);
  if (ipfsMatch && ipfsMatch[1]) {
    return ipfsMatch[1];
  }
  
  // Format 3: Qm... (direct hash)
  if (/^[a-zA-Z0-9]{10,}$/.test(proof)) {
    return proof;
  }
  
  return null;
}

/**
 * Validate proof content matches dataset requirements
 * 
 * This is a placeholder for more sophisticated proof validation.
 * In production, you might:
 * - Download and verify IPFS content
 * - Check proof contains required dataset metadata
 * - Verify cryptographic signatures on proof
 */
export async function validateProofContent(
  proof: string,
  dataset: string
): Promise<boolean> {
  // For MVP: Basic validation
  // In production: Implement full proof content validation
  
  // If proof is IPFS link, you might want to:
  // 1. Download content from IPFS
  // 2. Verify content structure
  // 3. Check content matches dataset requirements
  
  // For now, return true if proof format is valid
  return verifyMinerProof('', proof, dataset);
}

