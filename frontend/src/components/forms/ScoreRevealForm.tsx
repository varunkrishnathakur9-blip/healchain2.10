/**
 * HealChain Frontend - ScoreRevealForm Component
creveal * Form for M7b: Miner reveals contribution score
 */

'use client';

import { useState, FormEvent } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { useContract } from '@/hooks/useContract';
import { keccak256, encodePacked } from 'viem';
import { parseError, ERROR_CODES } from '@/lib/errors';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';

interface ScoreRevealFormProps {
  taskID: string;
  scoreCommit: string; // From M3 submission
  onSuccess?: () => void;
}

function normalizeBytes32Hex(value: string): `0x${string}` | null {
  let v = (value || '').trim();

  // Handle frequent typo from some keyboard layouts: "Øx..." instead of "0x..."
  v = v.replace(/^[ØOo][xX]/, '0x');

  const trimmed = v.replace(/^0x/i, '');
  if (!/^[0-9a-fA-F]{64}$/.test(trimmed)) return null;
  return `0x${trimmed}` as `0x${string}`;
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
  const verifyCommit = (score: bigint, nonceHex: `0x${string}`, commitHex: `0x${string}`): boolean => {
    if (!address) return false;
    const expectedCommit = keccak256(
      encodePacked(['uint256', 'bytes32', 'string', 'address'], [score, nonceHex, taskID, address as `0x${string}`])
    );
    return expectedCommit.toLowerCase() === commitHex.toLowerCase();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isConnected || !address) {
      setError('Please connect your wallet');
      return;
    }

    try {
      // Validate inputs
      const rawScore = parseFloat(formData.score);
      if (!formData.score || !Number.isFinite(rawScore) || rawScore <= 0) {
        setError('Score must be greater than 0');
        return;
      }

      const nonceHex = normalizeBytes32Hex(formData.nonce);
      if (!nonceHex) {
        setError('Nonce must be 32-byte hex (64 hex chars, with or without 0x).');
        return;
      }

      const normalizedScoreCommit = normalizeBytes32Hex(scoreCommit);
      if (!normalizedScoreCommit) {
        setError('Stored score commit is missing or invalid (requires bytes32 hex).');
        return;
      }

      const score = BigInt(Math.floor(rawScore * 1e6));

      // Verify commit
      if (!verifyCommit(score, nonceHex, normalizedScoreCommit)) {
        setError(parseError(new Error(ERROR_CODES.COMMIT_MISMATCH)).message);
        return;
      }

      // Reveal score on-chain
      setShowModal(true);
      await revealScore(
        taskID,
        score,
        nonceHex,
        normalizedScoreCommit
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

