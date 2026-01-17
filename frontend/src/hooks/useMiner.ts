/**
 * HealChain Frontend - useMiner Hook
 * Hook for miner registration and management
 */

'use client';

import { useState, useCallback } from 'react';
import { minerAPI, type Miner } from '@/lib/api';
import { useWallet } from './useWallet';

export function useMiner() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { address, signMessage, createAuthMessage, isConnected } = useWallet();

  // M2: Register as miner for a task
  // Algorithm 2: Requires miner proof (IPFS link or system proof) and public key (recommended)
  const registerMiner = useCallback(
    async (taskID: string, proof: string, publicKey?: string) => {
      if (!isConnected || !address) {
        throw new Error('Wallet not connected');
      }

      if (!proof || proof.trim() === '') {
        throw new Error('Miner proof is required (Algorithm 2)');
      }

      setLoading(true);
      setError(null);

      try {
        // Create authentication message
        const message = createAuthMessage(address);
        const signature = await signMessage(message);

        // Register miner with proof and public key (Algorithm 2 requirement)
        const result = await minerAPI.register({
          taskID,
          address,
          proof,  // Algorithm 2: Miner proof (required)
          publicKey: publicKey || undefined,  // Algorithm 2: Miner public key (recommended for key derivation)
          message,
          signature,
        });

        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to register miner');
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [address, isConnected, signMessage, createAuthMessage]
  );

  return {
    registerMiner,
    loading,
    error,
  };
}

