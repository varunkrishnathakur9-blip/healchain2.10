/**
 * HealChain Frontend - ScoreRevealForm Component
 * Form for M7b: Miner reveals contribution score
 */

'use client';

import { useState, FormEvent } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { useContract } from '@/hooks/useContract';
import { keccak256, toBytes, encodePacked } from 'viem';
import { parseError, ERROR_CODES } from '@/lib/errors';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';

interface ScoreRevealFormProps {
  taskID: string;
  scoreCommit: string; // From M3 submission
  onSuccess?: () => void;
}

export default function ScoreRevealForm({ taskID, scoreCommit, onSuccess }: ScoreRevealFormProps) {
  const { address, isConnected } = useWallet();
  const { revealScore, hash, isPending, isConfirming, isConfirmed } = useContract();
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    score: '',
    nonce: '',
  });
  const [error, setError] = useState<string | null>(null);

  // Verify commit matches
  const verifyCommit = (score: bigint, nonce: string): boolean => {
    if (!address) return false;
    const nonceBytes = toBytes(nonce);
    const expectedCommit = keccak256(
      encodePacked(['uint256', 'bytes32', 'string', 'address'], [score, nonceBytes, taskID, address as `0x${string}`])
    );
    return expectedCommit.toLowerCase() === scoreCommit.toLowerCase();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isConnected || !address) {
      setError('Please connect your wallet');
      return;
    }

    try {
      const score = BigInt(Math.floor(parseFloat(formData.score) * 1e6));
      const nonceBytes = toBytes(formData.nonce);

      // Validate inputs
      if (!formData.score || parseFloat(formData.score) <= 0) {
        setError('Score must be greater than 0');
        return;
      }

      if (!formData.nonce.trim()) {
        setError('Nonce is required');
        return;
      }

      // Verify commit
      if (!verifyCommit(score, formData.nonce)) {
        setError(parseError(new Error(ERROR_CODES.COMMIT_MISMATCH)).message);
        return;
      }

      // Reveal score on-chain
      setShowModal(true);
      await revealScore(
        taskID,
        score,
        nonceBytes as `0x${string}`,
        scoreCommit as `0x${string}`
      );

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      const parsed = parseError(err);
      setError(parsed.message);
      setShowModal(false);
      
      // Log original error for debugging
      if (process.env.NEXT_PUBLIC_DEBUG === 'true') {
        console.error('Reveal score error:', parsed.originalError || err);
      }
    }
  };

  return (
    <>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Reveal Contribution Score
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Reveal your score for task: <span className="font-mono">{taskID}</span>
            </p>
          </div>

          <div>
            <label htmlFor="score" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Score
            </label>
            <input
              type="number"
              id="score"
              required
              min="0"
              step="0.000001"
              value={formData.score}
              onChange={(e) => setFormData({ ...formData, score: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="0.000000"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Enter the exact score value you committed during training
            </p>
          </div>

          <div>
            <label htmlFor="nonce" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Nonce
            </label>
            <input
              type="text"
              id="nonce"
              required
              value={formData.nonce}
              onChange={(e) => setFormData({ ...formData, nonce: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm"
              placeholder="Your commit nonce"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Enter the nonce you used when creating the score commit
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
            {isPending || isConfirming ? 'Revealing...' : 'Reveal Score'}
          </Button>
        </form>
      </Card>

      <TransactionModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        status={
          isConfirmed ? 'success' : isConfirming ? 'confirming' : isPending ? 'pending' : 'pending'
        }
        hash={hash}
        message={
          isConfirmed
            ? 'Score revealed successfully!'
            : isConfirming
              ? 'Waiting for blockchain confirmation...'
              : 'Revealing score on blockchain...'
        }
      />
    </>
  );
}

