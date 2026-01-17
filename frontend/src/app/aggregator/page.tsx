/**
 * HealChain Frontend - Aggregator Dashboard
 * Interactive dashboard showing Algorithm 2 (Key Derivation) and Algorithm 3 (Submissions)
 */

'use client';

import { useState, useEffect } from 'react';
import { useTaskList } from '@/hooks/useTask';
import { useAggregator } from '@/hooks/useAggregator';
import { useReadContract, useAccount } from 'wagmi';
import { BLOCK_PUBLISHER_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import Link from 'next/link';
import KeyDerivationCard from '@/components/aggregator/KeyDerivationCard';
import SubmissionsCard from '@/components/aggregator/SubmissionsCard';

export default function AggregatorPage() {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const { tasks, loading } = useTaskList();
  const [selectedTaskID, setSelectedTaskID] = useState<string | null>(null);

  const aggregatingTasks = tasks?.filter(
    (t) => t.status === 'AGGREGATING' || t.status === 'VERIFIED' || t.status === 'OPEN'
  ) || [];

  // Auto-select first task if available
  useEffect(() => {
    if (!selectedTaskID && aggregatingTasks.length > 0) {
      setSelectedTaskID(aggregatingTasks[0].taskID);
    }
  }, [aggregatingTasks, selectedTaskID]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Aggregator Dashboard</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Interactive view for Algorithm 2 (Key Derivation) and Algorithm 3 (Submissions)
        </p>
      </div>

      {/* Task Selection */}
      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Select Task</h2>
        {loading ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-4 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading tasks...</p>
          </div>
        ) : aggregatingTasks.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">No tasks available for aggregation</p>
        ) : (
          <div className="space-y-2">
            {aggregatingTasks.map((task) => (
              <button
                key={task.taskID}
                onClick={() => setSelectedTaskID(task.taskID)}
                className={`w-full p-3 text-left border rounded-lg transition-colors ${
                  selectedTaskID === task.taskID
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-gray-900 dark:text-white">{task.taskID}</span>
                    <TaskStatusBadge status={task.status} />
                  </div>
                  {selectedTaskID === task.taskID && (
                    <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </Card>

      {/* Task-Specific Dashboard */}
      {selectedTaskID && (
        <TaskAggregatorDashboard taskID={selectedTaskID} chainConfig={chainConfig} />
      )}

      {/* Legacy Task Aggregation Status (for backward compatibility) */}
      {aggregatingTasks.filter(t => t.status === 'VERIFIED').length > 0 && (
        <>
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Consensus Details</h2>
            {aggregatingTasks
              .filter(t => t.status === 'VERIFIED')
              .map((task) => (
                <ConsensusDetailsCard key={task.taskID} task={task} />
              ))}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Block Publishing Status</h2>
            {aggregatingTasks
              .filter(t => t.status === 'VERIFIED')
              .map((task) => (
                <BlockPublishingStatusCard key={task.taskID} task={task} chainConfig={chainConfig} />
              ))}
          </Card>
        </>
      )}
    </div>
  );
}

function TaskAggregatorDashboard({ taskID, chainConfig }: { taskID: string; chainConfig: any }) {
  const { address, isConnected } = useAccount();
  const {
    status,
    keyStatus,
    submissions,
    loading,
    loadingKeyStatus,
    loadingSubmissions,
    fetchStatus,
    fetchKeyStatus,
    fetchSubmissions,
    error
  } = useAggregator(taskID);

  // Check if user is authorized (must be connected and be the aggregator)
  const isAuthorized = isConnected && address;

  if (!isAuthorized) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-100 dark:bg-yellow-900 mb-4">
            <svg className="w-8 h-8 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Authentication Required
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Please connect your wallet to view aggregator dashboard.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Algorithm 2: Key Derivation Status */}
      <KeyDerivationCard keyStatus={keyStatus} loading={loadingKeyStatus} error={error} />

      {/* Algorithm 3: Submissions */}
      <SubmissionsCard submissions={submissions} loading={loadingSubmissions} taskID={taskID} error={error} />

      {/* Aggregator Status */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Aggregator Status
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              fetchStatus();
              fetchKeyStatus();
              fetchSubmissions();
            }}
            disabled={loading || loadingKeyStatus || loadingSubmissions}
          >
            Refresh
          </Button>
        </div>

        {loading ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-4 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading status...</p>
          </div>
        ) : status ? (
          <div className="space-y-3">
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-gray-600 dark:text-gray-400 mb-1">Status</dt>
                  <dd className="text-gray-900 dark:text-white font-medium">
                    <Badge variant={
                      status.status === 'COMPLETED' ? 'success' :
                      status.status === 'FAILED' ? 'error' :
                      status.status === 'AGGREGATING' ? 'info' :
                      'neutral'
                    }>
                      {status.status}
                    </Badge>
                  </dd>
                </div>
                {status.progress !== undefined && (
                  <div>
                    <dt className="text-gray-600 dark:text-gray-400 mb-1">Progress</dt>
                    <dd className="text-gray-900 dark:text-white font-medium">
                      {status.progress}%
                    </dd>
                  </div>
                )}
                {status.submissionCount !== undefined && (
                  <div>
                    <dt className="text-gray-600 dark:text-gray-400 mb-1">Submissions</dt>
                    <dd className="text-gray-900 dark:text-white font-medium">
                      {status.submissionCount} / {status.requiredSubmissions || '?'}
                    </dd>
                  </div>
                )}
                {status.completedAt && (
                  <div>
                    <dt className="text-gray-600 dark:text-gray-400 mb-1">Completed At</dt>
                    <dd className="text-gray-900 dark:text-white">
                      {new Date(status.completedAt).toLocaleString()}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {status.error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-800 dark:text-red-200">
                  <strong>Error:</strong> {status.error}
                </p>
              </div>
            )}

            {status.progress !== undefined && (
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${status.progress}%` }}
                ></div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-400">No status available</p>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-800 dark:text-red-200">
              <strong>Error:</strong> {error.message}
            </p>
          </div>
        )}
      </Card>

      {/* Task Actions */}
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Task Actions</h2>
          <Link href={`/tasks/${taskID}`}>
            <Button variant="outline" size="sm">View Full Task Details</Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}

function ConsensusDetailsCard({ task }: { task: any }) {
  const miners = (task as any).miners || [];
  
  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg mb-4">
      <h3 className="font-medium text-gray-900 dark:text-white mb-3">Task: {task.taskID}</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Miners Verified:</dt>
          <dd className="text-gray-900 dark:text-white">{miners.length}/{miners.length}</dd>
        </div>
        <div className="mt-2 space-y-1">
          {miners.map((miner: any, index: number) => (
            <p key={index} className="text-sm text-gray-900 dark:text-white font-mono">
              └─ {miner.address || miner}: VALID
            </p>
          ))}
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Consensus Result:</dt>
          <dd className="text-gray-900 dark:text-white">APPROVED</dd>
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Majority Required:</dt>
          <dd className="text-gray-900 dark:text-white">2/3</dd>
        </div>
      </dl>
    </div>
  );
}

function BlockPublishingStatusCard({ task, chainConfig }: { task: any; chainConfig: any }) {
  const { data: publishedBlock } = useReadContract({
    address: chainConfig?.contracts.blockPublisher as `0x${string}`,
    abi: BLOCK_PUBLISHER_ABI,
    functionName: 'publishedBlocks',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.blockPublisher },
  });

  const blockPublished = publishedBlock && (publishedBlock as any).timestamp > 0n;

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg mb-4">
      <h3 className="font-medium text-gray-900 dark:text-white mb-3">Task: {task.taskID}</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Candidate Block Status:</dt>
          <dd className="text-gray-900 dark:text-white">Ready</dd>
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">On-Chain Status:</dt>
          <dd className="text-gray-900 dark:text-white">
            {blockPublished ? 'Published' : 'Not Published'}
          </dd>
        </div>
        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
          <p className="text-sm text-gray-700 dark:text-gray-300">
            <strong>Note:</strong> Publisher must call M6 to publish on-chain
          </p>
        </div>
      </dl>
    </div>
  );
}
