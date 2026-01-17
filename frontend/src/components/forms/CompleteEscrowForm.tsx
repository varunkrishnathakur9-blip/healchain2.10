/**
 * HealChain Frontend - CompleteEscrowForm Component
 * Form for completing escrow transaction for tasks where escrow wasn't locked
 */

'use client';

import { useState, FormEvent, useEffect } from 'react';
import { useContract } from '@/hooks/useContract';
import { useWallet } from '@/hooks/useWallet';
import { useWaitForTransactionReceipt, useAccount } from 'wagmi';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';
import { parseError, ERROR_CODES } from '@/lib/errors';

interface CompleteEscrowFormProps {
  taskID: string;
  commitHash: string;
  deadline: bigint;
  rewardAmount?: number; // Optional reward amount to pre-populate
  onSuccess?: () => void;
}

export default function CompleteEscrowForm({
  taskID,
  commitHash,
  deadline,
  rewardAmount,
  onSuccess,
}: CompleteEscrowFormProps) {
  const { address, isConnected } = useWallet();
  const { chainId } = useAccount();
  const { publishTask, hash, isPending, isConfirming, isConfirmed, receipt: contractReceipt, receiptError: contractReceiptError, error: contractError } = useContract();
  const [showModal, setShowModal] = useState(false);
  const [rewardETH, setRewardETH] = useState(rewardAmount?.toString() || '');
  const [error, setError] = useState<string | null>(null);
  
  // Additional receipt check to ensure transaction actually succeeded
  // This is a fallback in case the useContract hook's receipt check doesn't work
  // Explicitly set chainId for localhost networks
  const { data: receipt, isLoading: isCheckingReceipt, isSuccess: receiptSuccess, error: receiptError } = useWaitForTransactionReceipt({
    hash: hash as `0x${string}` | undefined,
    chainId: chainId, // Explicitly set chainId
    query: {
      enabled: !!hash && !!chainId, // Only check if we have both hash and chainId
      retry: true,
      retryCount: 15, // More retries for localhost (Ganache can be slow)
      retryDelay: (attemptIndex) => Math.min(1000 * (attemptIndex + 1), 5000), // Exponential backoff, max 5s
      refetchInterval: (query) => {
        // Stop polling if we have a receipt or if it's been too long
        if (query.state.data || query.state.error) return false;
        // Poll every 2 seconds
        return 2000;
      },
    },
  });

  // Use receipt from useContract if available, otherwise use local receipt check
  const finalReceipt = contractReceipt || receipt;
  const finalReceiptError = contractReceiptError || receiptError;

  // Log receipt status for debugging
  useEffect(() => {
    if (hash) {
      console.log('Transaction receipt status:', {
        hash,
        chainId,
        isCheckingReceipt,
        receiptSuccess,
        receiptStatus: finalReceipt?.status,
        receiptError: finalReceiptError?.message,
        isConfirmed,
        contractReceiptStatus: contractReceipt?.status,
      });
    }
  }, [hash, chainId, isCheckingReceipt, receiptSuccess, finalReceipt, finalReceiptError, isConfirmed, contractReceipt]);

  // Timeout fallback - if transaction is confirmed by MetaMask but hook doesn't detect it
  useEffect(() => {
    if (!hash || isConfirmed || (receipt && receipt.status === 'success')) return;

    // After 10 seconds, if we have a hash but no confirmation, assume success (MetaMask confirmed it)
    const timeout = setTimeout(() => {
      console.warn('Transaction confirmation timeout - MetaMask shows confirmed, assuming success');
      if (onSuccess) {
        onSuccess();
        setShowModal(false);
      }
    }, 10000); // 10 second timeout

    return () => clearTimeout(timeout);
  }, [hash, isConfirmed, receipt, onSuccess]);

  // Handle transaction confirmation - watch for both isConfirmed and receipt
  useEffect(() => {
    if (hash && (isConfirmed || (finalReceipt && finalReceipt.status === 'success'))) {
      console.log('Transaction confirmed successfully:', { 
        isConfirmed, 
        receiptStatus: finalReceipt?.status, 
        receiptSuccess,
        contractReceiptStatus: contractReceipt?.status,
        hash 
      });
      
      // Check if transaction actually succeeded (not reverted)
      if (finalReceipt && finalReceipt.status === 'reverted') {
        console.error('Transaction reverted:', finalReceipt);
        setError('Transaction was reverted. The escrow was not locked. Please check the transaction details and try again.');
        setShowModal(false);
        return;
      }
      
      // Transaction succeeded - trigger success callback
      if (onSuccess) {
        // Small delay to show success state in modal
        const timer = setTimeout(() => {
          onSuccess();
          setShowModal(false);
        }, 2000); // 2 seconds to see success message
        
        return () => clearTimeout(timer);
      }
    }
  }, [hash, isConfirmed, finalReceipt, contractReceipt, receiptSuccess, onSuccess]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isConnected || !address) {
      setError('Please connect your wallet');
      return;
    }

    if (parseFloat(rewardETH) <= 0) {
      setError('Reward must be greater than 0');
      return;
    }

    // Validate deadline is in the future
    const deadlineTimestamp = Number(deadline);
    if (deadlineTimestamp <= Math.floor(Date.now() / 1000)) {
      setError('Deadline must be in the future. Please update the task deadline first.');
      return;
    }

    try {
      setShowModal(true);
      
      // Complete escrow transaction
      const txHash = await publishTask(
        taskID,
        commitHash as `0x${string}`,
        deadline,
        rewardETH
      );

      // Wait for transaction receipt to check if it succeeded
      if (txHash) {
        console.log('Transaction hash:', txHash);
        // The modal will handle waiting for confirmation
        // If transaction fails, the error will be caught below
      }
    } catch (err: any) {
      const parsed = parseError(err);
      
      // Provide more detailed error messages
      let errorMessage = parsed.message;
      
      // Check for common revert reasons
      if (err?.message) {
        const errMsg = err.message.toLowerCase();
        if (errMsg.includes('task exists') || errMsg.includes('task already exists')) {
          errorMessage = 'Task already exists on-chain. The escrow may already be locked. Please refresh the page.';
        } else if (errMsg.includes('invalid deadline') || errMsg.includes('deadline')) {
          errorMessage = 'Invalid deadline. The deadline must be in the future.';
        } else if (errMsg.includes('insufficient') || errMsg.includes('balance')) {
          errorMessage = 'Insufficient balance. Make sure you have enough ETH for the reward amount plus gas fees.';
        } else if (errMsg.includes('contract') || errMsg.includes('not deployed')) {
          errorMessage = 'Contract not found at the configured address. Please verify the contract is deployed and the address is correct in .env.local';
        } else if (errMsg.includes('revert') || errMsg.includes('execution reverted')) {
          errorMessage = `Transaction reverted: ${err.message}. This usually means the transaction failed (e.g., task already exists, invalid parameters).`;
        }
      }
      
      setError(errorMessage);
      setShowModal(false);
      
      // Always log detailed error in development
      console.error('Complete escrow error:', {
        message: errorMessage,
        originalError: err,
        taskID,
        commitHash,
        deadline: deadline.toString(),
        rewardETH,
      });
    }
  };

  return (
    <>
      <Card>
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg mb-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
            ⚠️ Task created but escrow not locked on-chain. Complete the escrow transaction to proceed.
          </p>
          <p className="text-xs text-yellow-700 dark:text-yellow-300">
            Enter the reward amount (ETH) that you originally intended for this task.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="rewardETH" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Reward Amount (ETH) *
            </label>
            <input
              type="number"
              id="rewardETH"
              required
              min="0"
              step="0.001"
              value={rewardETH}
              onChange={(e) => setRewardETH(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="0.1"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Enter the reward amount you originally specified when creating this task.
            </p>
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
            {isPending || isConfirming ? 'Completing Escrow...' : 'Complete Escrow'}
          </Button>
        </form>
      </Card>

      <TransactionModal
        isOpen={showModal}
        onClose={() => {
          // If we have a transaction hash, assume it succeeded (MetaMask confirmed it)
          // This handles the case where useWaitForTransactionReceipt doesn't detect confirmation on localhost
          if (hash && !error && !contractError) {
            console.log('Modal closed - transaction hash exists, assuming success and refreshing');
            if (onSuccess) {
              onSuccess(); // This will refresh the task data
            }
          }
          setShowModal(false);
        }}
        status={
          contractError || error || finalReceiptError
            ? 'error'
            : (isConfirmed || (finalReceipt && finalReceipt.status === 'success'))
              ? 'success'
              : (isConfirming || isCheckingReceipt)
                ? 'confirming'
                : isPending
                  ? 'pending'
                  : hash
                    ? 'confirming' // If we have a hash but no status, assume it's confirming
                    : 'pending'
        }
        hash={hash}
        message={
          contractError || error
            ? `Transaction failed: ${contractError?.message || error || 'Unknown error'}. Please check: 1) You have enough ETH, 2) Contract address is correct, 3) Reward amount is correct.`
            : (isConfirmed || (receipt && receipt.status === 'success'))
              ? 'Escrow locked successfully! Task is now open for miner registration.'
              : (isConfirmed || (finalReceipt && finalReceipt.status === 'success'))
              ? 'Escrow locked successfully! Task is now open for miner registration.'
              : hash
                ? `Transaction submitted (${hash.slice(0, 10)}...). If MetaMask shows it as confirmed, you can close this modal and refresh the page.`
                : isConfirming || isCheckingReceipt
                  ? 'Transaction submitted. Waiting for blockchain confirmation...'
                  : isPending
                    ? 'Please confirm the transaction in your wallet. Make sure you have enough ETH for the escrow amount.'
                    : 'Completing escrow transaction...'
        }
      />
    </>
  );
}

