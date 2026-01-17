/**
 * HealChain Frontend - Submissions Card Component
 * Algorithm 3: Displays miner submissions with ciphertext status
 */

'use client';

import { useState } from 'react';
import Card from '@/components/Card';
import Badge from '@/components/Badge';
import { type Submission } from '@/hooks/useAggregator';

interface SubmissionsCardProps {
  submissions: Submission[];
  loading: boolean;
  taskID: string;
  error?: Error | null;
}

export default function SubmissionsCard({ submissions, loading, taskID, error }: SubmissionsCardProps) {
  const [expandedSubmission, setExpandedSubmission] = useState<string | null>(null);

  if (error) {
    return (
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Algorithm 3: Miner Submissions
        </h2>
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-200 font-medium mb-1">
            Access Denied
          </p>
          <p className="text-xs text-red-700 dark:text-red-300">
            {error.message || 'Only the selected aggregator can view submissions with ciphertext.'}
          </p>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Algorithm 3: Miner Submissions
        </h2>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading submissions...</p>
        </div>
      </Card>
    );
  }

  const submissionsWithCiphertext = submissions.filter(s => s.ciphertext && s.ciphertext.length > 0);
  const submissionsWithoutCiphertext = submissions.filter(s => !s.ciphertext || s.ciphertext.length === 0);

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Algorithm 3: Miner Submissions
        </h2>
        <div className="flex items-center gap-2">
          <Badge variant={submissions.length > 0 ? "success" : "neutral"}>
            {submissions.length} Submission{submissions.length !== 1 ? 's' : ''}
          </Badge>
          {submissionsWithCiphertext.length > 0 && (
            <Badge variant="info">
              {submissionsWithCiphertext.length} with Ciphertext
            </Badge>
          )}
        </div>
      </div>

      {submissions.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No submissions received yet. Waiting for miners to submit gradients...
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Summary */}
          <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Total Submissions</dt>
                <dd className="text-gray-900 dark:text-white font-medium text-lg">
                  {submissions.length}
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">With Ciphertext</dt>
                <dd className="text-gray-900 dark:text-white font-medium text-lg text-green-600 dark:text-green-400">
                  {submissionsWithCiphertext.length}
                </dd>
              </div>
              <div>
                <dt className="text-gray-600 dark:text-gray-400 mb-1">Missing Ciphertext</dt>
                <dd className="text-gray-900 dark:text-white font-medium text-lg text-yellow-600 dark:text-yellow-400">
                  {submissionsWithoutCiphertext.length}
                </dd>
              </div>
            </dl>
          </div>

          {/* Submissions List */}
          <div className="space-y-2">
            {submissions.map((submission, index) => {
              const hasCiphertext = submission.ciphertext && submission.ciphertext.length > 0;
              const isExpanded = expandedSubmission === submission.minerAddress;

              return (
                <div
                  key={submission.minerAddress}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          Miner #{index + 1}
                        </span>
                        {hasCiphertext ? (
                          <Badge variant="success" size="sm">Ciphertext Available</Badge>
                        ) : (
                          <Badge variant="error" size="sm">Missing Ciphertext</Badge>
                        )}
                        {submission.signature && (
                          <Badge variant="info" size="sm">Signed</Badge>
                        )}
                      </div>
                      <dl className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400">Address</dt>
                          <dd className="text-gray-900 dark:text-white font-mono break-all">
                            {submission.minerAddress}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400">Submitted At</dt>
                          <dd className="text-gray-900 dark:text-white">
                            {new Date(submission.submittedAt).toLocaleString()}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400">Score Commit</dt>
                          <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
                            {submission.scoreCommit.slice(0, 20)}...
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400">Encrypted Hash</dt>
                          <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
                            {submission.encryptedHash.slice(0, 20)}...
                          </dd>
                        </div>
                      </dl>
                    </div>
                    <button
                      onClick={() => setExpandedSubmission(isExpanded ? null : submission.minerAddress)}
                      className="ml-4 p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                      aria-label={isExpanded ? "Collapse" : "Expand"}
                    >
                      <svg
                        className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                      {/* Ciphertext Preview */}
                      {hasCiphertext ? (
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <dt className="text-xs font-medium text-gray-900 dark:text-white">
                              Ciphertext (EC Points)
                            </dt>
                            <Badge variant="success" size="sm">
                              {submission.ciphertext!.length} points
                            </Badge>
                          </div>
                          <dd className="text-xs font-mono text-gray-700 dark:text-gray-300 max-h-32 overflow-y-auto space-y-1">
                            {submission.ciphertext!.slice(0, 5).map((point, idx) => (
                              <div key={idx} className="break-all">
                                {idx + 1}. {point}
                              </div>
                            ))}
                            {submission.ciphertext!.length > 5 && (
                              <div className="text-gray-500 dark:text-gray-500 italic">
                                ... and {submission.ciphertext!.length - 5} more points
                              </div>
                            )}
                          </dd>
                        </div>
                      ) : (
                        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                          <p className="text-xs text-yellow-800 dark:text-yellow-200">
                            ⚠️ Ciphertext not available. This submission was made before ciphertext storage was implemented.
                            The aggregator cannot decrypt this submission without the ciphertext.
                          </p>
                        </div>
                      )}

                      {/* Full Details */}
                      <div className="grid grid-cols-1 gap-2 text-xs">
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400 mb-1">Public Key</dt>
                          <dd className="text-gray-900 dark:text-white font-mono break-all">
                            {submission.publicKey || 'Not available'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400 mb-1">Score Commit (Full)</dt>
                          <dd className="text-gray-900 dark:text-white font-mono break-all">
                            {submission.scoreCommit}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400 mb-1">Encrypted Hash (Full)</dt>
                          <dd className="text-gray-900 dark:text-white font-mono break-all">
                            {submission.encryptedHash}
                          </dd>
                        </div>
                        {submission.signature && (
                          <div>
                            <dt className="text-gray-600 dark:text-gray-400 mb-1">Miner Signature</dt>
                            <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
                              {submission.signature.slice(0, 50)}...
                            </dd>
                          </div>
                        )}
                        <div>
                          <dt className="text-gray-600 dark:text-gray-400 mb-1">Status</dt>
                          <dd className="text-gray-900 dark:text-white">
                            <Badge variant={submission.status === 'COMMITTED' ? 'success' : 'neutral'} size="sm">
                              {submission.status}
                            </Badge>
                          </dd>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Warning for Missing Ciphertext */}
          {submissionsWithoutCiphertext.length > 0 && (
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
              <p className="text-sm text-yellow-800 dark:text-yellow-200">
                <strong>Warning:</strong> {submissionsWithoutCiphertext.length} submission{submissionsWithoutCiphertext.length !== 1 ? 's' : ''} 
                {' '}missing ciphertext. These submissions cannot be decrypted by the aggregator.
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
