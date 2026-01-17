/**
 * HealChain Frontend - PublishTaskForm Component
 * Form for M1: Publishing a new FL task
 */

'use client';

import { useState, FormEvent, useEffect, useRef } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { useContract } from '@/hooks/useContract';
import { taskAPI } from '@/lib/api';
import { keccak256, encodePacked, bytesToHex, parseEther } from 'viem';
import { parseError, ERROR_CODES } from '@/lib/errors';
import { usePublicClient, useReadContract } from 'wagmi';
import { ESCROW_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { useAccount } from 'wagmi';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';

interface PublishTaskFormProps {
  onSuccess?: () => void;
}

export default function PublishTaskForm({ onSuccess }: PublishTaskFormProps) {
  const { address, isConnected, signMessage, createAuthMessage } = useWallet();
  const { chainId } = useAccount();
  const { publishTask, hash, isPending, isConfirming, isConfirmed, receipt, receiptError } = useContract();
  const publicClient = usePublicClient();
  const [showModal, setShowModal] = useState(false);
  const [escrowLocked, setEscrowLocked] = useState(false);
  const [isManuallyVerifying, setIsManuallyVerifying] = useState(false);
  const backendCreationAttempted = useRef(false); // Track if we've already attempted backend creation
  const [formData, setFormData] = useState({
    taskID: '',
    requiredAccuracy: '',
    rewardETH: '',
    deadline: '',
    minMiners: '3',  // Minimum miners required for PoS aggregator selection
    maxMiners: '5',  // Maximum miners allowed for PoS aggregator selection
    dataset: 'chestxray',  // D: Dataset requirements (Algorithm 1)
    initialModelLink: '',  // L: Initial model link (Algorithm 1) - optional
    nonceTP: '',           // Nonce for commit hash (Algorithm 1) - provided by publisher
    description: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [autoGenerateNonce, setAutoGenerateNonce] = useState(true);
  
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  
  // Check if task exists on-chain before submitting
  // NOTE: This hook must be declared AFTER formData state to avoid initialization error
  const { data: existingTask, isLoading: isLoadingTask } = useReadContract({
    address: chainConfig?.contracts.escrow as `0x${string}` | undefined,
    abi: ESCROW_ABI,
    functionName: 'tasks',
    args: formData.taskID ? [formData.taskID] : undefined,
    query: {
      enabled: !!chainConfig && !!formData.taskID && formData.taskID.length > 0,
    },
  });

  // Generate 32 random bytes using browser crypto API
  const generateRandomBytes = (length: number = 32): Uint8Array => {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return array;
  };

  // Helper function to generate nonce hex string
  const generateNonceHex = (): string => {
    const generated = generateRandomBytes(32);
    return Array.from(generated)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  };

  // Generate commit hash (M1)
  const generateCommitHash = (accuracy: number, nonce: Uint8Array): `0x${string}` => {
    const accuracyBigInt = BigInt(Math.floor(accuracy * 1e6));
    // Ensure nonce is exactly 32 bytes (bytes32)
    if (nonce.length !== 32) {
      throw new Error('Nonce must be exactly 32 bytes');
    }
    // Convert Uint8Array to hex string for bytes32 encoding
    const nonceHex = bytesToHex(nonce) as `0x${string}`;
    return keccak256(encodePacked(['uint256', 'bytes32'], [accuracyBigInt, nonceHex]));
  };

  // Auto-generate nonce on component mount (Algorithm 1)
  useEffect(() => {
    if (autoGenerateNonce && !formData.nonceTP) {
      setFormData(prev => ({ ...prev, nonceTP: generateNonceHex() }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Step 2: After escrow transaction is confirmed, create task in backend
  // The backend will verify escrow is locked before creating the task
  useEffect(() => {
    console.log('[DEBUG] useEffect triggered:', {
      hash: hash ? hash.substring(0, 10) + '...' : null,
      escrowLocked,
      address: address ? address.substring(0, 10) + '...' : null,
      backendCreationAttempted: backendCreationAttempted.current,
      isConfirmed,
      hasReceipt: !!receipt,
    });
    
    if (!hash || escrowLocked || !address || backendCreationAttempted.current) {
      console.log('[DEBUG] useEffect early return:', {
        noHash: !hash,
        escrowLocked,
        noAddress: !address,
        alreadyAttempted: backendCreationAttempted.current,
      });
      return;
    }
    
    // Debug logging
    console.log('[DEBUG] Escrow transaction status:', {
      hash,
      isPending,
      isConfirming,
      isConfirmed,
      receipt: receipt ? { status: receipt.status, blockNumber: receipt.blockNumber } : null,
      receiptError: receiptError?.message,
    });
    
    // If we have a receipt with success status, proceed even if isConfirmed is false
    // This handles cases where useWaitForTransactionReceipt doesn't update properly
    const hasSuccessfulReceipt = receipt?.status === 'success';
    
    if (!isConfirmed && !hasSuccessfulReceipt) {
      // Still waiting for confirmation
      console.log('[DEBUG] Still waiting for transaction confirmation');
      return;
    }
    
    // Mark that we've attempted backend creation to prevent retries
    backendCreationAttempted.current = true;
    
    // Proceed with backend task creation
    console.log('[DEBUG] useEffect: Calling createTaskInBackend with hash:', hash);
    createTaskInBackend(hash).catch((err) => {
      // Handle any unhandled errors
      console.error('[DEBUG] Unhandled error in createTaskInBackend:', err);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConfirmed, hash, receipt, receiptError, address, escrowLocked, isPending, isConfirming]);

  // Manual verification function - directly check transaction receipt
  const manuallyVerifyTransaction = async () => {
    if (!hash || !publicClient || escrowLocked || !address || backendCreationAttempted.current) return;
    
    try {
      setIsManuallyVerifying(true);
      console.log('Manually verifying transaction:', hash);
      
      // First, try to get the transaction to see if it exists
      let tx;
      try {
        tx = await publicClient.getTransaction({ hash: hash as `0x${string}` });
        console.log('Transaction found:', {
          blockNumber: tx.blockNumber,
          blockHash: tx.blockHash,
          from: tx.from,
          to: tx.to,
        });
      } catch (txErr: any) {
        console.warn('Could not get transaction:', txErr.message);
        // Transaction might not exist yet - check if it's pending
        throw new Error('Transaction not found. It may still be pending. Please wait a moment and try again, or check MetaMask for the transaction status.');
      }
      
      // If transaction exists but no blockNumber, it's still pending
      if (!tx.blockNumber) {
        throw new Error('Transaction is still pending and has not been mined yet. Please wait for it to be confirmed.');
      }
      
      // Now try to get the receipt
      let txReceipt;
      try {
        txReceipt = await publicClient.getTransactionReceipt({ hash: hash as `0x${string}` });
      } catch (receiptErr: any) {
        // Receipt might not be available yet even if transaction is in a block
        // This can happen if the block was just mined
        console.warn('Receipt not available yet:', receiptErr.message);
        throw new Error('Transaction receipt not available yet. The transaction may have just been mined. Please wait a few seconds and try again.');
      }
      
      console.log('Transaction receipt received:', {
        status: txReceipt.status,
        blockNumber: txReceipt.blockNumber,
        blockHash: txReceipt.blockHash,
      });
      
      if (txReceipt.status === 'success') {
        // Transaction is confirmed - proceed with backend task creation
        console.log('Transaction confirmed manually - proceeding with task creation');
        backendCreationAttempted.current = true; // Mark as attempted before calling
        await createTaskInBackend(hash);
      } else {
        throw new Error('Transaction reverted on-chain');
      }
    } catch (err: any) {
      console.error('Manual verification failed:', err);
      const errorMessage = err.message || 'Failed to verify transaction. Please check the transaction hash manually.';
      setError(errorMessage);
      
      // Don't close modal on error - let user see the error and try again
    } finally {
      setIsManuallyVerifying(false);
    }
  };

  // Helper function to create task in backend (extracted for reuse)
  const createTaskInBackend = async (txHash: string) => {
    // Note: backendCreationAttempted is already checked in useEffect, so we don't check it here
    // Also, escrowLocked might be false initially, but we set it to true here to prevent duplicate calls
    if (!address) {
      console.log('[DEBUG] createTaskInBackend early return: no address');
      return;
    }
    
    // Check if already locked (prevent duplicate calls from multiple sources)
    if (escrowLocked) {
      console.log('[DEBUG] createTaskInBackend early return: already locked');
      return;
    }
    
    try {
      console.log('[DEBUG] Starting backend task creation for hash:', txHash);
      setEscrowLocked(true); // Prevent duplicate calls
      // Note: backendCreationAttempted is already set to true in useEffect before calling this function
      
      // Sign message for backend
      console.log('[DEBUG] Requesting signature for backend authentication...');
      const message = createAuthMessage(address);
      console.log('[DEBUG] Message to sign:', message);
      
      let signature: string;
      try {
        signature = await signMessage(message);
        console.log('[DEBUG] Signature received:', signature.substring(0, 20) + '...');
      } catch (sigError: any) {
        console.error('[DEBUG] Signature error:', sigError);
        throw sigError;
      }
      
      console.log('[DEBUG] Signature received, preparing API call...');

      // Calculate values needed for backend
      const accuracy = parseFloat(formData.requiredAccuracy);
      const deadlineDate = new Date(formData.deadline);
      const deadlineTimestamp = BigInt(Math.floor(deadlineDate.getTime() / 1000));
      
      // Get nonce
      let nonceHex: string;
      if (autoGenerateNonce) {
        nonceHex = formData.nonceTP;
      } else {
        const nonceTrimmed = formData.nonceTP.trim().replace(/^0x/i, '');
        nonceHex = nonceTrimmed;
      }
      
      // Generate commit hash (same as before)
      const nonce = new Uint8Array(
        nonceHex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
      );
      const commitHash = generateCommitHash(accuracy, nonce);

      // Create task in backend with escrow transaction hash
      const requestData = {
        taskID: formData.taskID,
        publisher: address,
        address: address,
        accuracy: Math.floor(accuracy * 1e6).toString(),
        deadline: deadlineTimestamp.toString(),
        commitHash: commitHash,
        nonceTP: nonceHex,
        escrowTxHash: txHash,
        dataset: formData.dataset,
        initialModelLink: formData.initialModelLink || undefined,
        minMiners: parseInt(formData.minMiners),
        maxMiners: parseInt(formData.maxMiners),
        message,
        signature,
      };
      
      console.log('[DEBUG] Calling backend API to create task:', {
        taskID: requestData.taskID,
        escrowTxHash: requestData.escrowTxHash,
        minMiners: requestData.minMiners,
        maxMiners: requestData.maxMiners,
        backendURL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3000',
      });
      
      const result = await taskAPI.create(requestData);
      
      console.log('[DEBUG] Backend task creation successful:', result);

      // Success - close modal and call onSuccess
      setShowModal(false);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      console.error('[DEBUG] Error in createTaskInBackend:', err);
      const parsed = parseError(err);
      setError(parsed.message);
      // Don't reset escrowLocked or backendCreationAttempted on signature rejection
      // Only allow retry if it's a backend API error (not a signature/user rejection)
      const isSignatureRejection = err?.message?.includes('signature') || err?.message?.includes('rejected') || err?.message?.includes('User rejected');
      if (!isSignatureRejection) {
        setEscrowLocked(false); // Allow retry only for non-signature errors
        backendCreationAttempted.current = false;
      }
      setShowModal(false);
      
      // Log error with serializable properties only
      const errorDetails = {
        message: err?.message || parsed.message,
        code: parsed.code,
        name: err?.name,
        response: err?.response?.data ? {
          error: err.response.data.error,
          message: err.response.data.message,
          status: err.response.status,
        } : undefined,
        stack: err?.stack?.substring(0, 500), // Limit stack trace length
      };
      console.error('Backend task creation error:', errorDetails);
    }
  };

  // Timeout fallback: If transaction hash exists but confirmation is taking too long,
  // try to proceed anyway (transaction might be confirmed but hook didn't update)
  useEffect(() => {
    if (!hash || escrowLocked || !address || isConfirmed || receipt?.status === 'success') return;
    
    // Set a timeout of 30 seconds - if still not confirmed, show warning
    const timeout = setTimeout(() => {
      console.warn('Transaction confirmation timeout - transaction might be confirmed but hook not updated');
      console.log('Transaction hash:', hash);
      console.log('Current status:', { isPending, isConfirming, isConfirmed, receipt: receipt?.status });
      console.log('Suggestion: Use "Verify Manually" button if MetaMask shows transaction as confirmed');
    }, 30000); // 30 seconds
    
    return () => clearTimeout(timeout);
  }, [hash, escrowLocked, address, isConfirmed, receipt, isPending, isConfirming]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isConnected || !address) {
      setError(parseError(new Error(ERROR_CODES.WALLET_NOT_CONNECTED)).message);
      return;
    }

    // Validate form data
    if (!formData.taskID.trim()) {
      setError('Task ID is required');
      return;
    }

    if (parseFloat(formData.requiredAccuracy) <= 0 || parseFloat(formData.requiredAccuracy) > 100) {
      setError('Required accuracy must be between 0 and 100');
      return;
    }

    if (parseFloat(formData.rewardETH) <= 0) {
      setError('Reward must be greater than 0');
      return;
    }

    const deadlineDate = new Date(formData.deadline);
    if (deadlineDate <= new Date()) {
      setError('Deadline must be in the future');
      return;
    }

    // Validate min/max miners
    const minMiners = parseInt(formData.minMiners);
    const maxMiners = parseInt(formData.maxMiners);
    if (isNaN(minMiners) || minMiners < 1) {
      setError('Minimum miners must be at least 1');
      return;
    }
    if (isNaN(maxMiners) || maxMiners < minMiners) {
      setError('Maximum miners must be greater than or equal to minimum miners');
      return;
    }
    if (maxMiners > 1000) {
      setError('Maximum miners cannot exceed 1000');
      return;
    }

    try {
      // Get nonce from publisher (Algorithm 1 requirement)
      let nonce: Uint8Array;
      let nonceHex: string;
      
      if (autoGenerateNonce) {
        // Auto-generate nonce for convenience
        nonce = generateRandomBytes(32);
        nonceHex = Array.from(nonce)
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
        // Update form with generated nonce
        setFormData({ ...formData, nonceTP: nonceHex });
      } else {
        // Use publisher-provided nonce (Algorithm 1 compliance)
        if (!formData.nonceTP || formData.nonceTP.trim() === '') {
          setError('Nonce is required (Algorithm 1)');
          return;
        }
        
        // Validate nonce format (64 hex characters = 32 bytes)
        const nonceTrimmed = formData.nonceTP.trim().replace(/^0x/i, '');
        if (!/^[0-9a-fA-F]{64}$/.test(nonceTrimmed)) {
          setError('Nonce must be exactly 64 hex characters (32 bytes). Example: 0x1234...abcd');
          return;
        }
        
        // Convert hex string to Uint8Array
        nonce = new Uint8Array(
          nonceTrimmed.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16))
        );
        nonceHex = nonceTrimmed;
      }
      
      // Generate commit hash (Algorithm 1: keccak256(accuracy || nonce))
      const accuracy = parseFloat(formData.requiredAccuracy);
      const commitHash = generateCommitHash(accuracy, nonce);

      // Calculate deadline timestamp
      const deadlineDate = new Date(formData.deadline);
      const deadlineTimestamp = BigInt(Math.floor(deadlineDate.getTime() / 1000));
      
      // Validate deadline is in the future
      const currentTimestamp = BigInt(Math.floor(Date.now() / 1000));
      if (deadlineTimestamp <= currentTimestamp) {
        setError('Deadline must be in the future. Please select a future date and time.');
        return;
      }
      
      // Validate reward amount
      const rewardAmount = parseFloat(formData.rewardETH);
      if (isNaN(rewardAmount) || rewardAmount <= 0) {
        setError('Reward must be greater than 0. Please enter a valid reward amount.');
        return;
      }
      
      // Check if task already exists on-chain
      if (existingTask && existingTask.publisher && existingTask.publisher !== '0x0000000000000000000000000000000000000000') {
        setError(`Task ID "${formData.taskID}" already exists on-chain. Please use a different task ID.`);
        return;
      }

      // Step 1: Lock escrow on-chain FIRST (atomic operation)
      // This ensures the task can only be created if escrow is successfully locked
      setShowModal(true);
      backendCreationAttempted.current = false; // Reset flag for new task
      
      try {
        await publishTask(
          formData.taskID,
          commitHash as `0x${string}`,
          deadlineTimestamp,
          formData.rewardETH
        );
        // Wait for transaction hash
        // Note: We'll wait for confirmation in useEffect below
      } catch (publishErr: any) {
        // If simulation failed, show the error immediately
        const parsed = parseError(publishErr);
        setError(parsed.message);
        setShowModal(false);
        
        // Log full error details for debugging (extract serializable properties)
        const errorDetails = {
          message: publishErr?.message || parsed.message,
          revertReason: publishErr?.revertReason || parsed.revertReason,
          code: parsed.code,
          name: publishErr?.name,
          stack: publishErr?.stack?.substring(0, 500), // Limit stack trace length
        };
        console.error('Publish task error:', errorDetails);
        throw publishErr; // Re-throw to be caught by outer catch
      }
    } catch (err: any) {
      const parsed = parseError(err);
      setError(parsed.message);
      setShowModal(false);
      
      // Log original error for debugging (extract serializable properties)
      const errorDetails = {
        message: err?.message || parsed.message,
        code: parsed.code,
        name: err?.name,
        stack: err?.stack?.substring(0, 500), // Limit stack trace length
      };
      console.error('Publish task error (outer catch):', errorDetails);
    }
  };

  // Get minimum date (today)
  const minDate = new Date().toISOString().split('T')[0];

  return (
    <>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="taskID" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Task ID
            </label>
            <div className="relative">
              <input
                type="text"
                id="taskID"
                required
                value={formData.taskID}
                onChange={(e) => setFormData({ ...formData, taskID: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white ${
                  existingTask && existingTask.publisher && existingTask.publisher !== '0x0000000000000000000000000000000000000000'
                    ? 'border-red-300 dark:border-red-700'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder="task_001"
              />
              {isLoadingTask && formData.taskID && (
                <div className="absolute right-3 top-2.5 text-xs text-gray-500">Checking...</div>
              )}
              {existingTask && existingTask.publisher && existingTask.publisher !== '0x0000000000000000000000000000000000000000' && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                  ⚠️ This task ID already exists on-chain. Please use a different ID.
                </p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="requiredAccuracy" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Required Accuracy (%)
            </label>
            <input
              type="number"
              id="requiredAccuracy"
              required
              min="0"
              max="100"
              step="0.01"
              value={formData.requiredAccuracy}
              onChange={(e) => setFormData({ ...formData, requiredAccuracy: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="85.5"
            />
          </div>

          <div>
            <label htmlFor="rewardETH" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Reward (ETH)
            </label>
            <input
              type="number"
              id="rewardETH"
              required
              min="0"
              step="0.001"
              value={formData.rewardETH}
              onChange={(e) => setFormData({ ...formData, rewardETH: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="0.1"
            />
          </div>

          <div>
            <label htmlFor="deadline" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Deadline
            </label>
            <input
              type="datetime-local"
              id="deadline"
              required
              min={minDate}
              value={formData.deadline}
              onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="minMiners" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Min Miners <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="minMiners"
                required
                min="1"
                max="1000"
                value={formData.minMiners}
                onChange={(e) => setFormData({ ...formData, minMiners: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                placeholder="3"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Minimum miners required for PoS aggregator selection
              </p>
            </div>
            <div>
              <label htmlFor="maxMiners" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Miners <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="maxMiners"
                required
                min="1"
                max="1000"
                value={formData.maxMiners}
                onChange={(e) => setFormData({ ...formData, maxMiners: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                placeholder="5"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Maximum miners allowed for PoS aggregator selection
              </p>
            </div>
          </div>

          <div>
            <label htmlFor="nonceTP" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Nonce (Algorithm 1) <span className="text-red-500">*</span>
            </label>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="autoGenerateNonce"
                  checked={autoGenerateNonce}
                  onChange={(e) => {
                    setAutoGenerateNonce(e.target.checked);
                    if (e.target.checked) {
                      // Auto-generate when checkbox is checked
                      setFormData({ ...formData, nonceTP: generateNonceHex() });
                    }
                  }}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="autoGenerateNonce" className="text-sm text-gray-600 dark:text-gray-400">
                  Auto-generate nonce (recommended)
                </label>
                {autoGenerateNonce && (
                  <button
                    type="button"
                    onClick={() => {
                      setFormData({ ...formData, nonceTP: generateNonceHex() });
                    }}
                    className="ml-auto text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    Generate New
                  </button>
                )}
              </div>
              <input
                type="text"
                id="nonceTP"
                required
                disabled={autoGenerateNonce}
                value={formData.nonceTP}
                onChange={(e) => setFormData({ ...formData, nonceTP: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800"
                placeholder="0x1234567890abcdef... (64 hex characters)"
                pattern="^(0x)?[0-9a-fA-F]{64}$"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Publisher-provided nonce for commit hash generation (Algorithm 1). Must be 32 bytes (64 hex characters).
                {autoGenerateNonce && ' A secure random nonce will be generated automatically.'}
              </p>
            </div>
          </div>

          <div>
            <label htmlFor="dataset" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Dataset (D) <span className="text-red-500">*</span>
            </label>
            <select
              id="dataset"
              required
              value={formData.dataset}
              onChange={(e) => setFormData({ ...formData, dataset: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            >
              <option value="chestxray">Chest X-Ray</option>
              <option value="mnist">MNIST</option>
              <option value="cifar10">CIFAR-10</option>
              <option value="custom">Custom</option>
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Dataset requirements for the federated learning task (Algorithm 1: D)
            </p>
          </div>

          <div>
            <label htmlFor="initialModelLink" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Initial Model Link (L) <span className="text-gray-400 text-xs">(Optional)</span>
            </label>
            <input
              type="url"
              id="initialModelLink"
              value={formData.initialModelLink}
              onChange={(e) => setFormData({ ...formData, initialModelLink: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="https://ipfs.io/ipfs/... or http://..."
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Link to initial model for miners to start training from (Algorithm 1: L). Can be IPFS link or HTTP URL.
            </p>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description (Optional)
            </label>
            <textarea
              id="description"
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="Describe your federated learning task..."
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            isLoading={isPending || isConfirming}
            disabled={!isConnected}
            className="w-full"
          >
            {isPending || isConfirming ? 'Publishing...' : 'Publish Task'}
          </Button>
        </form>
      </Card>

      <TransactionModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          if (isConfirmed || receipt?.status === 'success') {
            onSuccess?.();
          }
        }}
        onManualVerify={hash && isConfirming && !isConfirmed && !escrowLocked ? manuallyVerifyTransaction : undefined}
        isManuallyVerifying={isManuallyVerifying}
        status={
          error
            ? 'error'
            : isConfirmed
              ? 'success'
              : isConfirming
                ? 'confirming'
                : isPending
                  ? 'pending'
                  : 'pending'
        }
        hash={hash}
        message={
          error
            ? `Transaction failed: ${error}\n\nCommon causes:\n• Task ID already exists (use a different ID)\n• Deadline is in the past (select a future date)\n• Reward is 0 (enter a valid amount)\n• Insufficient ETH balance\n• Contract not deployed (restart backend after deployment)`
            : isConfirmed
              ? 'Task published successfully! Escrow is now locked on-chain.'
              : isConfirming
                ? 'Transaction submitted. Waiting for blockchain confirmation... If MetaMask shows it as confirmed, click "Verify Manually".'
                : isPending
                  ? 'Please confirm the transaction in your wallet. Make sure you have enough ETH for the escrow amount.'
                  : 'Publishing task to blockchain...'
        }
      />
    </>
  );
}

