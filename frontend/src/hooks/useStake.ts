/**
 * HealChain Frontend - useStake Hook
 * Hook for managing miner stakes via StakeRegistry contract
 * Implements on-chain PoS stake management for Algorithm 2.1
 */

'use client';

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { useAccount } from 'wagmi';
import { parseEther, formatEther } from 'viem';
import { STAKE_REGISTRY_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { useState, useCallback, useEffect } from 'react';

export function useStake() {
  const { address, chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const stakeRegistryAddress = chainConfig?.contracts.stakeRegistry as `0x${string}` | undefined;

  const { writeContract, data: hash, isPending, error } = useWriteContract();
  const { 
    isLoading: isConfirming, 
    isSuccess: isConfirmed, 
    error: receiptError 
  } = useWaitForTransactionReceipt({
    hash,
    chainId,
    query: {
      enabled: !!hash && !!chainId,
      retry: true,
      retryCount: 20,
      retryDelay: (attemptIndex) => Math.min(1000 * (attemptIndex + 1), 5000),
    },
  });

  // Read minimum stake requirement
  const { data: minStake, refetch: refetchMinStake } = useReadContract({
    address: stakeRegistryAddress,
    abi: STAKE_REGISTRY_ABI,
    functionName: 'MIN_STAKE',
    chainId,
    query: { enabled: !!stakeRegistryAddress },
  });

  // Read current available stake for connected address
  const { data: availableStake, refetch: refetchStake } = useReadContract({
    address: stakeRegistryAddress,
    abi: STAKE_REGISTRY_ABI,
    functionName: 'getAvailableStake',
    args: address ? [address] : undefined,
    chainId,
    query: { 
      enabled: !!stakeRegistryAddress && !!address,
      refetchInterval: 5000, // Refetch every 5 seconds
    },
  });

  // Check eligibility
  const { data: isEligible, refetch: refetchEligibility } = useReadContract({
    address: stakeRegistryAddress,
    abi: STAKE_REGISTRY_ABI,
    functionName: 'isEligible',
    args: address ? [address] : undefined,
    chainId,
    query: { 
      enabled: !!stakeRegistryAddress && !!address,
      refetchInterval: 5000,
    },
  });

  // Read full stake info
  const { data: stakeInfo, refetch: refetchStakeInfo } = useReadContract({
    address: stakeRegistryAddress,
    abi: STAKE_REGISTRY_ABI,
    functionName: 'getStake',
    args: address ? [address] : undefined,
    chainId,
    query: { enabled: !!stakeRegistryAddress && !!address },
  });

  // Refetch all stake data after successful deposit
  useEffect(() => {
    if (isConfirmed) {
      refetchStake();
      refetchEligibility();
      refetchStakeInfo();
    }
  }, [isConfirmed, refetchStake, refetchEligibility, refetchStakeInfo]);

  // Deposit stake
  const depositStake = useCallback(
    async (amount: string) => {
      if (!stakeRegistryAddress) {
        throw new Error('StakeRegistry contract address not configured');
      }
      if (!address) {
        throw new Error('Wallet not connected');
      }

      const amountWei = parseEther(amount);
      if (amountWei === 0n) {
        throw new Error('Deposit amount must be greater than 0');
      }

      writeContract({
        address: stakeRegistryAddress,
        abi: STAKE_REGISTRY_ABI,
        functionName: 'depositStake',
        value: amountWei,
      });
    },
    [stakeRegistryAddress, address, writeContract]
  );

  // Request withdrawal
  const requestWithdrawal = useCallback(
    async (amount: string) => {
      if (!stakeRegistryAddress) {
        throw new Error('StakeRegistry contract address not configured');
      }
      if (!address) {
        throw new Error('Wallet not connected');
      }

      const amountWei = parseEther(amount);
      if (amountWei === 0n) {
        throw new Error('Withdrawal amount must be greater than 0');
      }

      writeContract({
        address: stakeRegistryAddress,
        abi: STAKE_REGISTRY_ABI,
        functionName: 'requestWithdrawal',
        args: [amountWei],
      });
    },
    [stakeRegistryAddress, address, writeContract]
  );

  // Complete withdrawal
  const withdrawStake = useCallback(
    async () => {
      if (!stakeRegistryAddress) {
        throw new Error('StakeRegistry contract address not configured');
      }
      if (!address) {
        throw new Error('Wallet not connected');
      }

      writeContract({
        address: stakeRegistryAddress,
        abi: STAKE_REGISTRY_ABI,
        functionName: 'withdrawStake',
      });
    },
    [stakeRegistryAddress, address, writeContract]
  );

  return {
    // Contract address
    stakeRegistryAddress,
    isConfigured: !!stakeRegistryAddress,

    // Stake data
    minStake: minStake ? formatEther(minStake) : '0',
    availableStake: availableStake ? formatEther(availableStake) : '0',
    isEligible: isEligible ?? false,
    
    // Full stake info
    stakeInfo: stakeInfo
      ? {
          availableStake: formatEther(stakeInfo[0]),
          totalStake: formatEther(stakeInfo[1]),
          pendingWithdrawal: formatEther(stakeInfo[2]),
          unlockTime: Number(stakeInfo[3]),
        }
      : null,

    // Actions
    depositStake,
    requestWithdrawal,
    withdrawStake,

    // Transaction state
    depositHash: hash,
    isDepositing: isPending,
    isDepositConfirming: isConfirming,
    isDepositConfirmed: isConfirmed,
    depositError: error || receiptError,

    // Refetch functions
    refetchStake,
    refetchEligibility,
    refetchStakeInfo,
    refetchMinStake,
  };
}
