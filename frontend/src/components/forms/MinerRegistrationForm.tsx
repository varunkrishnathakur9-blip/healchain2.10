/**
 * HealChain Frontend - MinerRegistrationForm Component
 * Form for M2: Registering as a miner for a task
 */

'use client';

import { useState, FormEvent } from 'react';
import { useWallet } from '@/hooks/useWallet';
import { useMiner } from '@/hooks/useMiner';
import { useStake } from '@/hooks/useStake';
import Button from '../Button';
import Card from '../Card';
import Link from 'next/link';

interface MinerRegistrationFormProps {
  taskID: string;
  onSuccess?: () => void;
}

export default function MinerRegistrationForm({ taskID, onSuccess }: MinerRegistrationFormProps) {
  const { isConnected } = useWallet();
  const { registerMiner, loading, error } = useMiner();
  const {
    minStake,
    availableStake,
    isEligible,
    isConfigured: isStakeConfigured,
  } = useStake();
  const [success, setSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [proof, setProof] = useState('');  // Algorithm 2: Miner proof (IPFS link or system proof)
  const [publicKey, setPublicKey] = useState('');  // Algorithm 2: Miner public key for key derivation (EC point: x_hex,y_hex)
  const [showStakeWarning, setShowStakeWarning] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccess(false);

    if (!isConnected) {
      setErrorMessage('Please connect your wallet');
      return;
    }

    // Algorithm 2: Validate proof is provided
    if (!proof || proof.trim() === '') {
      setErrorMessage('Miner proof is required (Algorithm 2). Please provide IPFS link or system proof.');
      return;
    }

    // Algorithm 2: Warn if public key is not provided (required for key derivation)
    if (!publicKey || publicKey.trim() === '') {
      const proceed = window.confirm(
        'Warning: Public key not provided. Key derivation (Algorithm 2.2) requires all miners\' public keys. ' +
        'You can still register, but key derivation will be delayed until all miners provide their public keys. ' +
        'Continue without public key?'
      );
      if (!proceed) {
        return;
      }
    }

    // Check stake eligibility (Algorithm 2.1 requirement)
    if (isStakeConfigured && !isEligible) {
      setShowStakeWarning(true);
      // Still allow registration, but warn user
    }

    try {
      await registerMiner(taskID, proof, publicKey.trim() || undefined);
      setSuccess(true);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to register as miner';
      setErrorMessage(errorMsg);
    }
  };

  if (success) {
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Successfully Registered!
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            You are now registered as a miner for this task.
          </p>
          {isStakeConfigured && !isEligible && (
            <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <p className="text-sm text-yellow-800 dark:text-yellow-200 font-medium mb-1">
                ⚠️ Stake Eligibility Warning
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-300">
                You have insufficient stake ({availableStake} ETH) for aggregator selection.
                Minimum required: {parseFloat(minStake).toFixed(4)} ETH. You can still participate
                as a miner, but won't be selected as aggregator.
              </p>
            </div>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Register as Miner
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Register to participate in task: <span className="font-mono">{taskID}</span>
          </p>
          
          {/* Stake Eligibility Status */}
          {isStakeConfigured && (
            <div className={`p-3 rounded-lg mb-4 ${
              isEligible
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                : 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
            }`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className={`text-sm font-medium mb-1 ${
                    isEligible
                      ? 'text-green-800 dark:text-green-200'
                      : 'text-yellow-800 dark:text-yellow-200'
                  }`}>
                    {isEligible ? (
                      <>✓ Eligible for Aggregator Selection (Algorithm 2.1)</>
                    ) : (
                      <>⚠️ Insufficient Stake for Aggregator Selection</>
                    )}
                  </p>
                  <p className={`text-xs ${
                    isEligible
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-yellow-700 dark:text-yellow-300'
                  }`}>
                    Current stake: {availableStake} ETH | Minimum required: {parseFloat(minStake).toFixed(4)} ETH
                    {!isEligible && (
                      <> | You can still register but won't be selected as aggregator</>
                    )}
                  </p>
                </div>
              </div>
              {!isEligible && (
                <div className="mt-2">
                  <Link href="/mining?action=stake" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                    → Deposit stake now
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          <label htmlFor="proof" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Miner Proof (Algorithm 2) <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="proof"
            required
            value={proof}
            onChange={(e) => setProof(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            placeholder="ipfs://Qm... or https://ipfs.io/ipfs/Qm... or JSON system proof"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Provide IPFS link to your system proof or system proof JSON. This will be verified against task dataset requirements (Algorithm 2).
          </p>
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Examples: 
            <span className="font-mono ml-1">ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco</span> or
            <span className="font-mono ml-1">{"{\"dataset\":\"chestxray\",\"capabilities\":[...]}"}</span>
          </p>
        </div>

        <div>
          <label htmlFor="publicKey" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Public Key (Algorithm 2) <span className="text-yellow-600">⚠️ Recommended</span>
          </label>
          <input
            type="text"
            id="publicKey"
            value={publicKey}
            onChange={(e) => setPublicKey(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white font-mono text-sm"
            placeholder="0000000000000000000000000000000000000000000000000000000000000001,0000000000000000000000000000000000000000000000000000000000000002"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Your EC point public key for NDD-FE encryption and key derivation (Algorithm 2.2). Format: <span className="font-mono">x_hex,y_hex</span> (64 hex digits each).
          </p>
          <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
            <strong>Important:</strong> Key derivation requires all miners' public keys. You can derive your public key from your <span className="font-mono">MINER_PRIVATE_KEY</span> in your FL client.
          </p>
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            How to get: Your FL client should provide this. If using <span className="font-mono">MINER_PRIVATE_KEY</span>, compute <span className="font-mono">{'g^{sk}'}</span> where <span className="font-mono">g</span> is the secp256r1 generator point.
          </p>
        </div>

        {errorMessage && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">{errorMessage}</p>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">{error.message}</p>
          </div>
        )}

        {/* Stake Warning Before Submission */}
        {showStakeWarning && !isEligible && (
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200 font-medium mb-1">
              Warning: Insufficient Stake
            </p>
            <p className="text-xs text-yellow-700 dark:text-yellow-300 mb-2">
              You have {availableStake} ETH staked, but need {parseFloat(minStake).toFixed(4)} ETH 
              minimum to be eligible for aggregator selection (Algorithm 2.1). You can still 
              register as a miner, but you won't be selected as aggregator.
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setShowStakeWarning(false)}
                className="text-xs py-1"
              >
                Continue Anyway
              </Button>
            </div>
          </div>
        )}

        <Button
          type="submit"
          variant="primary"
          isLoading={loading}
          disabled={!isConnected}
          className="w-full"
        >
          {loading ? 'Registering...' : 'Register as Miner'}
        </Button>
      </form>
    </Card>
  );
}

