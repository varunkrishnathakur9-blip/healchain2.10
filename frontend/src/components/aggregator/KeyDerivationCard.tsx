/**
 * HealChain Frontend - Key Derivation Card Component
 * Algorithm 2: Displays skFE key derivation status and metadata
 */

'use client';

import Card from '@/components/Card';
import Badge from '@/components/Badge';
import { type KeyStatus } from '@/hooks/useAggregator';

interface KeyDerivationCardProps {
  keyStatus: KeyStatus | null;
  loading: boolean;
  error?: Error | null;
}

export default function KeyDerivationCard({ keyStatus, loading, error }: KeyDerivationCardProps) {
  if (loading) {
    return (
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Algorithm 2: Key Derivation Status
        </h2>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading key status...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Algorithm 2: Key Derivation Status
        </h2>
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-200 font-medium mb-1">
            Access Denied
          </p>
          <p className="text-xs text-red-700 dark:text-red-300">
            {error.message || 'Only the selected aggregator can view key derivation metadata.'}
          </p>
        </div>
      </Card>
    );
  }

  if (!keyStatus) {
    return (
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Algorithm 2: Key Derivation Status
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">No key status available</p>
      </Card>
    );
  }

  const isReady = keyStatus.keyDerived && keyStatus.aggregatorSelected;
  const canDerive = keyStatus.canDerive ?? false;

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Algorithm 2: Key Derivation Status
        </h2>
        {isReady ? (
          <Badge variant="success">Key Derived</Badge>
        ) : keyStatus.aggregatorSelected ? (
          <Badge variant="info">Aggregator Selected</Badge>
        ) : (
          <Badge variant="neutral">Pending</Badge>
        )}
      </div>

      <div className="space-y-4">
        {/* Status Overview */}
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-600 dark:text-gray-400 mb-1">Key Derived</dt>
              <dd className="text-gray-900 dark:text-white font-medium">
                {keyStatus.keyDerived ? 'Yes' : 'No'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-600 dark:text-gray-400 mb-1">Aggregator Selected</dt>
              <dd className="text-gray-900 dark:text-white font-medium">
                {keyStatus.aggregatorSelected ? 'Yes' : 'No'}
              </dd>
            </div>
            {keyStatus.aggregatorAddress && (
              <div className="col-span-2">
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Aggregator Address</dt>
                <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
                  {keyStatus.aggregatorAddress}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Derivation Metadata */}
        {keyStatus.derivationMetadata && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Derivation Metadata (Algorithm 2.2)
            </h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Publisher</dt>
                <dd className="text-gray-900 dark:text-white font-mono text-xs">
                  {keyStatus.derivationMetadata.publisher}
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Miner Public Keys</dt>
                <dd className="text-gray-900 dark:text-white">
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {keyStatus.derivationMetadata.minerPublicKeys.map((pk, idx) => (
                      <div key={idx} className="font-mono text-xs break-all">
                        {idx + 1}. {pk}
                      </div>
                    ))}
                  </div>
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Nonce (nonceTP)</dt>
                <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
                  {keyStatus.derivationMetadata.nonceTP}
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Derivation Method</dt>
                <dd className="text-gray-900 dark:text-white text-xs">
                  {keyStatus.derivationMethod || 'Algorithm 2.2: H(publisher || minerPKs || taskID || nonceTP)'}
                </dd>
              </div>
            </dl>
          </div>
        )}

        {/* Miner Count Info */}
        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-600 dark:text-gray-400 mb-1">Total Miners</dt>
              <dd className="text-gray-900 dark:text-white font-medium">
                {keyStatus.minerCount || 0}
              </dd>
            </div>
            <div>
              <dt className="text-gray-600 dark:text-gray-400 mb-1">Miners with Public Keys</dt>
              <dd className="text-gray-900 dark:text-white font-medium">
                {keyStatus.minersWithPublicKeys || 0}
              </dd>
            </div>
            {keyStatus.requiredMiners && (
              <div className="col-span-2">
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Required Miners</dt>
                <dd className="text-gray-900 dark:text-white font-medium">
                  {keyStatus.minerCount || 0} / {keyStatus.requiredMiners}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Key Delivery Status */}
        {keyStatus.keyDelivered && keyStatus.keyDeliveredAt && (
          <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-sm font-medium text-green-800 dark:text-green-200">
                Key Delivered
              </span>
            </div>
            <p className="text-xs text-green-700 dark:text-green-300">
              Delivered at: {new Date(keyStatus.keyDeliveredAt).toLocaleString()}
            </p>
          </div>
        )}

        {/* Warning Messages */}
        {!keyStatus.aggregatorSelected && keyStatus.message && (
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              {keyStatus.message}
            </p>
          </div>
        )}

        {keyStatus.aggregatorSelected && !canDerive && (
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Cannot derive key: Some miners are missing public keys or insufficient miners registered.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
