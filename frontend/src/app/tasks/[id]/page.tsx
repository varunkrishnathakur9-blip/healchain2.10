'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAccount } from 'wagmi';
import { useTask } from '@/hooks/useTask';
import { useContract } from '@/hooks/useContract';
import { minerAPI } from '@/lib/api';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import TaskTimeline from '@/components/TaskTimeline';
import BlockchainStatePanel from '@/components/BlockchainStatePanel';
import ParticipantsPanel from '@/components/ParticipantsPanel';
import MinerRegistrationForm from '@/components/forms/MinerRegistrationForm';
import CompleteEscrowForm from '@/components/forms/CompleteEscrowForm';
import Link from 'next/link';
import { formatEther } from 'viem';
import { useReadContract } from 'wagmi';
import { ESCROW_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { formatDateLong } from '@/lib/dateUtils';

export default function TaskDetailPage() {
  const params = useParams();
  const taskID = params.id as string;
  const { address, isConnected, chainId } = useAccount();
  const { task, loading, error, refresh } = useTask(taskID);
  const { publishTask, revealAccuracy, revealScore, distributeRewards, refundEscrow } = useContract();
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [showCompleteEscrow, setShowCompleteEscrow] = useState(false);
  const [isRegisteredMiner, setIsRegisteredMiner] = useState<boolean | null>(null);

  const chainConfig = chainId ? getChainConfig(chainId) : null;

  // Use task's escrow contract address if available, otherwise fall back to env variable
  // This ensures we read from the correct contract even after redeployments
  const escrowAddress = (task?.escrowContractAddress || chainConfig?.contracts.escrow) as `0x${string}` | undefined;

  // Check escrow balance on-chain
  // Note: If the contract doesn't exist or doesn't have this function, this will error
  const { data: escrowBalance, error: escrowBalanceError, isLoading: isLoadingEscrow } = useReadContract({
    address: escrowAddress,
    abi: ESCROW_ABI,
    functionName: 'escrowBalance',
    args: [taskID],
    query: { 
      enabled: !!escrowAddress && !!task,
      refetchInterval: 5000, // Refetch every 5 seconds to catch updates
      retry: false, // Don't retry if it fails - likely means contract doesn't exist
    },
  });

  // Also check if task exists on-chain
  const { data: contractTask, error: contractTaskError } = useReadContract({
    address: escrowAddress,
    abi: ESCROW_ABI,
    functionName: 'tasks',
    args: [taskID],
    query: { 
      enabled: !!escrowAddress && !!task,
      refetchInterval: 5000,
    },
  });

  // Debug logging
  useEffect(() => {
    if (taskID && escrowAddress) {
      const errorMsg = escrowBalanceError?.message || '';
      const isContractError = errorMsg.includes('returned no data') || 
                             errorMsg.includes('not a contract') ||
                             errorMsg.includes('does not have the function');
      
      console.log('Escrow balance check:', {
        taskID,
        escrowAddress: escrowAddress,
        taskEscrowAddress: task?.escrowContractAddress,
        envEscrowAddress: chainConfig?.contracts.escrow,
        escrowBalance: escrowBalance?.toString(),
        escrowBalanceError: escrowBalanceError?.message,
        isLoadingEscrow,
        isContractError,
        contractTask: contractTask ? {
          publisher: contractTask[1],
          reward: contractTask[2]?.toString(),
          status: contractTask[5],
        } : null,
        contractTaskError: contractTaskError?.message,
      });

      // If we get a "returned no data" error, it likely means:
      // 1. Contract doesn't exist at that address
      // 2. Contract doesn't have the escrowBalance function
      // 3. Contract was deployed with different code
      if (isContractError && errorMsg) {
        // Only log if we have a meaningful error message
        // Use console.warn instead of console.error to avoid triggering error overlays
        console.warn('⚠️ Contract verification issue:', {
          address: escrowAddress,
          error: errorMsg,
          suggestion: 'Please verify the contract is deployed at this address and has the escrowBalance function',
        });
      }
    }
  }, [taskID, escrowAddress, task?.escrowContractAddress, chainConfig?.contracts.escrow, escrowBalance, escrowBalanceError, isLoadingEscrow, contractTask, contractTaskError]);

  const isPublisher = address && task?.publisher?.toLowerCase() === address.toLowerCase();
  const isMiner = address && !isPublisher;
  const isObserver = !isConnected;

  // Check if current user is a registered miner for this task
  useEffect(() => {
    const checkMinerRegistration = async () => {
      if (!address || !isConnected || !taskID || isPublisher) {
        setIsRegisteredMiner(false);
        return;
      }

      try {
        const response = await minerAPI.getMyTasks(address);
        const registeredTaskIDs = response.registeredTaskIDs || [];
        setIsRegisteredMiner(registeredTaskIDs.includes(taskID));
      } catch (err) {
        console.error('Failed to check miner registration:', err);
        setIsRegisteredMiner(false);
      }
    };

    checkMinerRegistration();
  }, [address, isConnected, taskID, isPublisher]);

  // Check if escrow needs to be completed
  // With the new flow, tasks are only created if escrow is verified as locked (status = OPEN)
  // So we only show Complete Escrow for legacy tasks with status CREATED
  const taskExistsOnChain = contractTask && contractTask[1] && contractTask[1] !== '0x0000000000000000000000000000000000000000';
  const isLegacyTask = task?.status === 'CREATED'; // Legacy tasks created before escrow verification
  const needsEscrow = isPublisher && task && isLegacyTask && (!escrowBalance || escrowBalance === 0n) && !taskExistsOnChain;
  
  // If task exists on-chain but balance is 0, there might be an issue
  // This could happen if the transaction reverted or if there's a mismatch
  const hasIssue = taskExistsOnChain && (!escrowBalance || escrowBalance === 0n);
  
  // Debug: Log the actual values
  console.log('Escrow status check:', {
    taskID,
    escrowBalance: escrowBalance?.toString(),
    contractTaskPublisher: contractTask?.[1],
    taskExistsOnChain,
    needsEscrow,
    hasIssue,
  });

  // Check if deadline has passed and task is not completed
  const deadlinePassed = task?.deadline 
    ? Number(task.deadline) * 1000 < Date.now()
    : false;
  
  const canRefund = isPublisher && deadlinePassed && 
    task?.status !== 'REWARDED' && 
    task?.status !== 'COMPLETED' &&
    task?.status !== 'CANCELLED';

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading task...</p>
          </div>
        </Card>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <p className="text-red-600 dark:text-red-400 mb-4">
              {error?.message || 'Task not found'}
            </p>
            <Link href="/tasks">
              <Button variant="primary">Back to Tasks</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const handleRegister = () => {
    setShowRegisterForm(true);
  };

  const handlePublishBlock = async () => {
    // M6: Block publishing - would need aggregator data
    // This should be implemented based on aggregator status
  };

  const handleRevealAccuracy = async () => {
    // M7a: Reveal accuracy - would need accuracy and nonce from M1
    // Navigate to rewards page for full form
  };

  const handleRevealScore = async () => {
    // M7b: Reveal score - would need score and nonce from M3
    // Navigate to rewards page for full form
  };

  const handleDistributeRewards = async () => {
    // M7c: Distribute rewards - would need miner list
    // Navigate to rewards page for full form
  };

  const handleRefundEscrow = async () => {
    if (!task?.taskID) return;
    try {
      await refundEscrow(task.taskID);
      // Refresh task data after refund
      refresh?.();
    } catch (err) {
      console.error('Refund failed:', err);
    }
  };

  const handleCompleteEscrowSuccess = () => {
    setShowCompleteEscrow(false);
    // Refresh task data after escrow is locked
    // Add a small delay to ensure blockchain state is updated
    setTimeout(() => {
      refresh?.();
      // Force a page refresh to ensure all data is updated
      window.location.reload();
    }, 1000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{task.taskID}</h1>
          <div className="mt-2 flex items-center gap-2">
            <TaskStatusBadge status={task.status} />
          </div>
        </div>
        <Link href="/tasks">
          <Button variant="outline">Back to Tasks</Button>
        </Link>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Task Metadata</h2>
        <dl className="space-y-3">
          <div>
            <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Publisher</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{task.publisher}</dd>
          </div>
          {task.rewardAmount && (
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Reward</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">{task.rewardAmount} ETH</dd>
            </div>
          )}
          {task.accuracyRequired && (
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Required Accuracy</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {(task.accuracyRequired / 1e6).toFixed(2)}%
              </dd>
            </div>
          )}
          {task.deadline && (
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Deadline</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {formatDateLong(task.deadline)}
              </dd>
            </div>
          )}
          {task.createdAt && (
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Created</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {formatDateLong(new Date(task.createdAt).getTime() / 1000)}
              </dd>
            </div>
          )}
          {task.dataset && (
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Dataset</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">{task.dataset}</dd>
            </div>
          )}
        </dl>
      </Card>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Protocol Phase Timeline</h2>
        <TaskTimeline
          task={task}
          onRegister={handleRegister}
          onPublishBlock={handlePublishBlock}
          onRevealAccuracy={handleRevealAccuracy}
          onRevealScore={handleRevealScore}
          onDistributeRewards={handleDistributeRewards}
        />
      </Card>

      <BlockchainStatePanel task={task} />

      <ParticipantsPanel task={task} />

      {isConnected && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Actions</h2>
          {isPublisher ? (
            <div className="space-y-3">
              {hasIssue && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-3">
                  <p className="text-sm text-red-800 dark:text-red-200 mb-2">
                    ⚠️ Task exists on-chain but escrow balance is 0. This might indicate the transaction reverted.
                  </p>
                  <p className="text-xs text-red-700 dark:text-red-300 mb-2">
                    Check the transaction receipt to see if it reverted. If it succeeded, try refreshing the page.
                  </p>
                  <div className="flex gap-2">
                    <Button variant="primary" onClick={() => refresh?.()}>
                      Refresh
                    </Button>
                    <Button variant="outline" onClick={() => setShowCompleteEscrow(true)}>
                      Try Again
                    </Button>
                  </div>
                </div>
              )}
              {needsEscrow && !showCompleteEscrow && !hasIssue && (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg mb-3">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                    ⚠️ Escrow not locked on-chain. Complete the escrow transaction to proceed.
                  </p>
                  {escrowBalanceError && (
                    <div className="text-xs text-yellow-700 dark:text-yellow-300 mb-2 space-y-1">
                      <p className="font-semibold">Error reading escrow:</p>
                      <p className="font-mono text-xs break-all">{escrowBalanceError.message}</p>
                      {escrowBalanceError.message.includes('returned no data') && (
                        <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded">
                          <p className="font-semibold text-red-800 dark:text-red-200">⚠️ Possible Issues:</p>
                          <ul className="list-disc list-inside mt-1 space-y-1">
                            <li>Contract not deployed at {escrowAddress || chainConfig?.contracts.escrow}</li>
                            <li>Contract deployed with different code</li>
                            <li>Wrong contract address in .env.local</li>
                          </ul>
                          <p className="mt-2 text-xs">
                            <strong>Solution:</strong> Deploy the contract and update NEXT_PUBLIC_ESCROW_ADDRESS in .env.local
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  <Button variant="primary" onClick={() => setShowCompleteEscrow(true)}>
                    Complete Escrow
                  </Button>
                </div>
              )}
              {needsEscrow && showCompleteEscrow && task.commitHash && task.deadline && (
                <CompleteEscrowForm
                  taskID={task.taskID}
                  commitHash={task.commitHash}
                  deadline={BigInt(task.deadline)}
                  rewardAmount={task.rewardAmount}
                  onSuccess={handleCompleteEscrowSuccess}
                />
              )}
              {canRefund && (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg mb-3">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                    Task deadline has passed. You can refund the escrow if the task was not completed.
                  </p>
                  <Button variant="primary" onClick={handleRefundEscrow}>
                    Refund Escrow
                  </Button>
                </div>
              )}
              {task.status === 'VERIFIED' && (
                <Button variant="primary" onClick={handlePublishBlock}>
                  Publish Block (M6, when M5 consensus passed)
                </Button>
              )}
              {(task.status === 'REVEAL_OPEN' || task.status === 'REVEAL_CLOSED' || task.status === 'VERIFIED') && (
                <Link href="/rewards">
                  <Button variant="primary">
                    Reveal Accuracy (M7a, when M6 published)
                  </Button>
                </Link>
              )}
              {task.status === 'REVEAL_CLOSED' && (
                <Link href="/rewards">
                  <Button variant="primary">
                    Distribute Rewards (M7c, when M7b complete)
                  </Button>
                </Link>
              )}
            </div>
          ) : isMiner ? (
            <div className="space-y-3">
              {showRegisterForm ? (
                <MinerRegistrationForm
                  taskID={task.taskID}
                  onSuccess={() => {
                    setShowRegisterForm(false);
                    refresh?.();
                    // Refresh registration status
                    minerAPI.getMyTasks(address!).then(response => {
                      const registeredTaskIDs = response.registeredTaskIDs || [];
                      setIsRegisteredMiner(registeredTaskIDs.includes(taskID));
                    }).catch(console.error);
                  }}
                />
              ) : (
                <>
                  {!isRegisteredMiner && (task.status === 'OPEN' || task.status === 'CREATED') && (
                    <Button variant="primary" onClick={handleRegister}>
                      Register as Miner (M2)
                    </Button>
                  )}
                  {isRegisteredMiner && (task.status === 'OPEN' || task.status === 'AGGREGATING') && (
                    <Link href={`/training/${task.taskID}`}>
                      <Button variant="primary">
                        Go to Training Dashboard (M3)
                      </Button>
                    </Link>
                  )}
                  {(task.status === 'REVEAL_OPEN' || task.status === 'REVEAL_CLOSED' || task.status === 'VERIFIED') && (
                    <Link href="/rewards">
                      <Button variant="primary">
                        Reveal Score (M7b, when M7a done)
                      </Button>
                    </Link>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              No actions available (read-only)
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
