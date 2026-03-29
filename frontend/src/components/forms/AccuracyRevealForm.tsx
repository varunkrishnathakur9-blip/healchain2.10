/**
 * HealChain Frontend - AccuracyRevealForm Component
 * Form for M7a: Publisher reveals committed accuracy
 */

'use client';

import { FormEvent, useMemo, useState } from 'react';
import { encodePacked, keccak256 } from 'viem';
import { useContract } from '@/hooks/useContract';
import { useWallet } from '@/hooks/useWallet';
import { parseError } from '@/lib/errors';
import Button from '../Button';
import Card from '../Card';
import TransactionModal from '../modals/TransactionModal';

interface AccuracyRevealFormProps {
  taskID: string;
  commitHash: string;
  onSuccess?: () => void;
}

function normalizeBytes32Hex(value: string): `0x${string}` | null {
  const trimmed = (value || '').trim().replace(/^0x/i, '');
  if (!/^[0-9a-fA-F]{64}$/.test(trimmed)) return null;
  return `0x${trimmed}` as `0x${string}`;
}

export default function AccuracyRevealForm({ taskID, commitHash, onSuccess }: AccuracyRevealFormProps) {
  const { isConnected } = useWallet();
  const { revealAccuracy, hash, isPending, isConfirming, isConfirmed } = useContract();
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    accuracy: '',
    nonce: '',
  });
  const [error, setError] = useState<string | null>(null);

  const normalizedCommitHash = useMemo(() => normalizeBytes32Hex(commitHash), [commitHash]);

  const verifyCommit = (accuracyScaled: bigint, nonceHex: `0x${string}`): boolean => {
    if (!normalizedCommitHash) return false;
    const expected = keccak256(encodePacked(['uint256', 'bytes32'], [accuracyScaled, nonceHex]));
    return expected.toLowerCase() === normalizedCommitHash.toLowerCase();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isConnected) {
      setError('Please connect your wallet');
      return;
    }

    if (!normalizedCommitHash) {
      setError('Task commit hash is missing or invalid (requires bytes32 hex).');
      return;
    }

    const rawAccuracy = parseFloat(formData.accuracy);
    if (!Number.isFinite(rawAccuracy) || rawAccuracy < 0 || rawAccuracy > 100) {
      setError('Accuracy must be a number between 0 and 100 (same value used at publish time).');
      return;
    }

    const nonceHex = normalizeBytes32Hex(formData.nonce);
    if (!nonceHex) {
      setError('Nonce must be 32-byte hex (64 hex chars, with or without 0x).');
      return;
    }

    try {
      const accuracyScaled = BigInt(Math.floor(rawAccuracy * 1e6));
      if (!verifyCommit(accuracyScaled, nonceHex)) {
        setError('Accuracy + nonce do not match the stored commit hash.');
        return;
      }

      setShowModal(true);
      await revealAccuracy(taskID, accuracyScaled, nonceHex, normalizedCommitHash);
      if (onSuccess) onSuccess();
    } catch (err) {
      const parsed = parseError(err);
      setError(parsed.message);
      setShowModal(false);
    }
  };

  return (
    <>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Reveal Accuracy (M7a)</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Enter the exact committed accuracy value and nonce from task publishing.
            </p>
          </div>

          <div>
            <label htmlFor="accuracy" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Accuracy (0-100)
            </label>
            <input
              id="accuracy"
              type="number"
              required
              min="0"
              max="100"
              step="0.000001"
              value={formData.accuracy}
              onChange={(e) => setFormData((prev) => ({ ...prev, accuracy: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              placeholder="e.g. 80.000000"
            />
          </div>

          <div>
            <label htmlFor="nonce" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Nonce (bytes32 hex)
            </label>
            <input
              id="nonce"
              type="text"
              required
              value={formData.nonce}
              onChange={(e) => setFormData((prev) => ({ ...prev, nonce: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm"
              placeholder="64 hex chars (with or without 0x)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Stored Commit</label>
            <div className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-xs font-mono break-all text-gray-700 dark:text-gray-300">
              {normalizedCommitHash || 'Unavailable'}
            </div>
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
            disabled={!isConnected || !normalizedCommitHash}
            className="w-full"
          >
            {isPending || isConfirming ? 'Revealing...' : 'Submit Accuracy Reveal'}
          </Button>
        </form>
      </Card>

      <TransactionModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        status={isConfirmed ? 'success' : isConfirming ? 'confirming' : 'pending'}
        hash={hash}
        message={
          isConfirmed
            ? 'Accuracy revealed successfully!'
            : isConfirming
              ? 'Waiting for blockchain confirmation...'
              : 'Submitting accuracy reveal transaction...'
        }
      />
    </>
  );
}

