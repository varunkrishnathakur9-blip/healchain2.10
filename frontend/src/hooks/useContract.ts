/**
 * HealChain Frontend - useContract Hook
 * Hook for interacting with HealChain smart contracts
 */

'use client';

import { useReadContract, useWriteContract, useWaitForTransactionReceipt, useSimulateContract, usePublicClient } from 'wagmi';
import { useAccount } from 'wagmi';
import { parseEther, formatEther } from 'viem';
import { ESCROW_ABI, REWARD_DISTRIBUTION_ABI, BLOCK_PUBLISHER_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { useMemo } from 'react';

export function useContract() {
  const { address, chainId } = useAccount();
  const publicClient = usePublicClient();
  const { writeContract, data: hash, isPending, error } = useWriteContract();
  const { isLoading: isConfirming, isSuccess: isConfirmed, data: receipt, error: receiptError } = useWaitForTransactionReceipt({
    hash,
    chainId: chainId, // Explicitly set chainId for proper network detection
    query: {
      enabled: !!hash && !!chainId, // Only check if we have both
      retry: true,
      retryCount: 20, // More retries for localhost
      retryDelay: (attemptIndex) => Math.min(1000 * (attemptIndex + 1), 5000), // Exponential backoff
      refetchInterval: (query) => {
        // Stop polling if we have a receipt or error
        if (query.state.data || query.state.error) return false;
        // Poll every 2 seconds for localhost
        return 2000;
      },
    },
  });

  const chainConfig = useMemo(() => {
    if (!chainId) return null;
    return getChainConfig(chainId);
  }, [chainId]);

  // M1: Publish task with escrow
  const publishTask = async (
    taskID: string,
    accuracyCommit: `0x${string}`,
    deadline: bigint,
    rewardETH: string
  ) => {
    if (!chainConfig) throw new Error('Chain not configured');
    if (!address) throw new Error('Wallet not connected');
    if (!publicClient) throw new Error('Public client not available');

    // Validate inputs before sending
    const rewardWei = parseEther(rewardETH);
    if (rewardWei === 0n) {
      throw new Error('Reward must be greater than 0');
    }
    
    const currentTimestamp = BigInt(Math.floor(Date.now() / 1000));
    if (deadline <= currentTimestamp) {
      throw new Error('Deadline must be in the future');
    }

    // Simulate the transaction first to catch revert reasons
    try {
      await publicClient.simulateContract({
        address: chainConfig.contracts.escrow as `0x${string}`,
        abi: ESCROW_ABI,
        functionName: 'publishTask',
        args: [taskID, accuracyCommit, deadline],
        value: rewardWei,
        account: address,
      });
    } catch (simError: any) {
      // Extract revert reason from simulation error
      // Check multiple possible locations for the revert reason
      let revertReason = simError?.details || 
                        simError?.cause?.details ||
                        simError?.cause?.reason || 
                        simError?.cause?.data?.message ||
                        simError?.shortMessage ||
                        simError?.message ||
                        'Transaction would revert';
      
      // Extract revert reason from "revert X" format
      // Try multiple patterns to capture the full revert reason
      let extractedReason = null;
      
      // Pattern 1: "VM Exception while processing transaction: revert Task exists\nVersion..."
      let match = revertReason.match(/VM Exception while processing transaction:\s*revert\s+([^\n]+)/i);
      if (match && match[1]) {
        extractedReason = match[1].trim();
      } else {
        // Pattern 2: "revert Task exists\nVersion..." or "revert Task exists"
        match = revertReason.match(/revert\s+([^\n]+)/i);
        if (match && match[1]) {
          extractedReason = match[1].trim();
        } else {
          // Pattern 3: Just "Task exists" (already extracted)
          extractedReason = revertReason.trim();
        }
      }
      
      if (extractedReason) {
        revertReason = extractedReason;
      }
      
      // Create a more descriptive error with the revert reason
      const error = new Error(`Transaction simulation failed: ${revertReason}`);
      (error as any).cause = simError;
      (error as any).revertReason = revertReason;
      (error as any).details = simError?.details || simError?.cause?.details;
      throw error;
    }

    return writeContract({
      address: chainConfig.contracts.escrow as `0x${string}`,
      abi: ESCROW_ABI,
      functionName: 'publishTask',
      args: [taskID, accuracyCommit, deadline],
      value: rewardWei,
    });
  };

  // Note: For reading contract data, use useReadContract hook directly in components
  // These functions are provided for reference but should be used with hooks

  // M7a: Reveal accuracy (Publisher)
  const revealAccuracy = async (
    taskID: string,
    accuracy: bigint,
    nonce: `0x${string}`,
    commitHash: `0x${string}`
  ) => {
    if (!chainConfig) throw new Error('Chain not configured');
    if (!chainConfig.contracts.rewardDistribution) {
      throw new Error('RewardDistribution contract not configured');
    }

    return writeContract({
      address: chainConfig.contracts.rewardDistribution as `0x${string}`,
      abi: REWARD_DISTRIBUTION_ABI,
      functionName: 'revealAccuracy',
      args: [taskID, accuracy, nonce, commitHash],
    });
  };

  // M7b: Reveal score (Miner)
  const revealScore = async (
    taskID: string,
    score: bigint,
    nonce: `0x${string}`,
    scoreCommit: `0x${string}`
  ) => {
    if (!chainConfig) throw new Error('Chain not configured');
    if (!chainConfig.contracts.rewardDistribution) {
      throw new Error('RewardDistribution contract not configured');
    }

    return writeContract({
      address: chainConfig.contracts.rewardDistribution as `0x${string}`,
      abi: REWARD_DISTRIBUTION_ABI,
      functionName: 'revealScore',
      args: [taskID, score, nonce, scoreCommit],
    });
  };

  // M7c: Distribute rewards
  const distributeRewards = async (taskID: string, miners: `0x${string}`[]) => {
    if (!chainConfig) throw new Error('Chain not configured');
    if (!chainConfig.contracts.rewardDistribution) {
      throw new Error('RewardDistribution contract not configured');
    }

    return writeContract({
      address: chainConfig.contracts.rewardDistribution as `0x${string}`,
      abi: REWARD_DISTRIBUTION_ABI,
      functionName: 'distribute',
      args: [taskID, miners],
    });
  };

  // Refund escrow if task deadline passed and not completed
  const refundEscrow = async (taskID: string) => {
    if (!chainConfig) throw new Error('Chain not configured');
    if (!address) throw new Error('Wallet not connected');

    return writeContract({
      address: chainConfig.contracts.escrow as `0x${string}`,
      abi: ESCROW_ABI,
      functionName: 'refundPublisher',
      args: [taskID],
    });
  };

  // Note: For reading contract data, use useReadContract hook directly in components

  return {
    publishTask,
    revealAccuracy,
    revealScore,
    distributeRewards,
    refundEscrow,
    isPending,
    isConfirming,
    isConfirmed,
    hash,
    error,
    receipt, // Expose receipt for components to check status
    receiptError, // Expose receipt error
    chainConfig,
  };
}

