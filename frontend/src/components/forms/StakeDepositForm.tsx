/**
 * HealChain Frontend - StakeDepositForm Component
 * Form for depositing stakes to StakeRegistry contract
 * Required for PoS aggregator selection (Algorithm 2.1)
 */

'use client';

import { useState, FormEvent } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { useStake } from '@/hooks/useStake';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';

interface StakeDepositFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export default function StakeDepositForm({ onSuccess, onCancel }: StakeDepositFormProps) {
  const { isConnected, address } = useWallet();
  const {
    minStake,
    availableStake,
    isEligible,
    depositStake,
    depositHash,
    isDepositing,
    isDepositConfirming,
    isDepositConfirmed,
    depositError,
    stakeInfo,
    refetchStake,
  } = useStake();

  const [amount, setAmount] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showTransactionModal, setShowTransactionModal] = useState(false);

  // Refetch stake after successful deposit
  if (isDepositConfirmed) {
    refetchStake();
    if (onSuccess) {
      setTimeout(() => {
        onSuccess();
      }, 1000);
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!isConnected) {
      setErrorMessage('Please connect your wallet');
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setErrorMessage('Please enter a valid deposit amount');
      return;
    }

    const minStakeFloat = parseFloat(minStake);
    const amountFloat = parseFloat(amount);

    if (amountFloat < minStakeFloat) {
      setErrorMessage(
        `Minimum stake required: ${minStakeFloat} ETH. You are depositing ${amountFloat} ETH.`
      );
      return;
    }

    try {
      await depositStake(amount);
      setShowTransactionModal(true);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to deposit stake';
      setErrorMessage(errorMsg);
    }
  };

  if (!isConnected) {
    return (
      <Card>
        <div className="text-center py-6">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Please connect your wallet to deposit stake
          </p>
        </div>
      </Card>
    );
  }

  if (isDepositConfirmed) {
    return (
      <Card>
        <div className="text-center py-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900 mb-4">
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Stake Deposited Successfully!
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {amount} ETH has been deposited to your stake.
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Your available stake: {availableStake} ETH
          </p>
          {isEligible && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <p className="text-sm text-green-700 dark:text-green-400 font-medium">
                ✓ You are now eligible for aggregator selection!
              </p>
            </div>
          )}
        </div>
      </Card>
    );
  }

  const minStakeFloat = parseFloat(minStake);
  const currentStakeFloat = parseFloat(availableStake);
  const remainingNeeded = Math.max(0, minStakeFloat - currentStakeFloat);

  return (
    <>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Deposit Stake for PoS Selection
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Deposit ETH to participate in Proof of Stake aggregator selection (Algorithm 2.1).
              You must have at least {minStakeFloat} ETH staked to be eligible for selection.
            </p>
          </div>

          {/* Current Stake Status */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Current Available Stake:
              </span>
              <span className="text-sm font-mono text-gray-900 dark:text-white">
                {availableStake} ETH
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Minimum Required:
              </span>
              <span className="text-sm font-mono text-gray-900 dark:text-white">
                {minStakeFloat} ETH
              </span>
            </div>
            {currentStakeFloat < minStakeFloat && (
              <div className="flex justify-between items-center pt-2 border-t border-gray-200 dark:border-gray-700">
                <span className="text-sm font-medium text-orange-700 dark:text-orange-400">
                  Additional Stake Needed:
                </span>
                <span className="text-sm font-mono font-semibold text-orange-700 dark:text-orange-400">
                  {remainingNeeded.toFixed(4)} ETH
                </span>
              </div>
            )}
            {isEligible && (
              <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-green-700 dark:text-green-400 font-medium">
                  ✓ You are eligible for aggregator selection
                </p>
              </div>
            )}
            {stakeInfo && stakeInfo.pendingWithdrawal !== '0.0' && (
              <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
                <p className="text-xs text-yellow-700 dark:text-yellow-400">
                  ⚠️ You have {stakeInfo.pendingWithdrawal} ETH pending withdrawal
                </p>
              </div>
            )}
          </div>

          {/* Amount Input */}
          <div>
            <label
              htmlFor="amount"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Deposit Amount (ETH) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="amount"
              required
              min={minStakeFloat}
              step="0.0001"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder={`Minimum: ${minStakeFloat} ETH`}
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Enter the amount of ETH you want to deposit. Minimum stake: {minStakeFloat} ETH
            </p>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-700 dark:text-red-400">{errorMessage}</p>
            </div>
          )}

          {/* Deposit Error */}
          {depositError && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-700 dark:text-red-400">
                Deposit failed: {depositError instanceof Error ? depositError.message : String(depositError)}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              type="submit"
              variant="primary"
              disabled={isDepositing || isDepositConfirming || !amount}
              loading={isDepositing || isDepositConfirming}
              className="flex-1"
            >
              {isDepositing || isDepositConfirming ? 'Processing...' : 'Deposit Stake'}
            </Button>
            {onCancel && (
              <Button type="button" variant="secondary" onClick={onCancel} className="flex-1">
                Cancel
              </Button>
            )}
          </div>

          {/* Info */}
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <p className="text-xs text-blue-700 dark:text-blue-400">
              <strong>Note:</strong> Stakes are locked on-chain and used for PoS aggregator selection.
              You can request withdrawal after depositing, but there is an unlock delay. Higher stakes
              increase your probability of being selected as aggregator.
            </p>
          </div>
        </form>
      </Card>

      {/* Transaction Modal */}
      {showTransactionModal && depositHash && (
        <TransactionModal
          hash={depositHash}
          isOpen={showTransactionModal}
          onClose={() => {
            if (isDepositConfirmed) {
              setShowTransactionModal(false);
            }
          }}
          status={
            isDepositConfirmed
              ? 'confirmed'
              : isDepositConfirming
              ? 'confirming'
              : isDepositing
              ? 'pending'
              : 'pending'
          }
        />
      )}
    </>
  );
}
