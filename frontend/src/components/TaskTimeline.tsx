'use client';

import { useAccount } from 'wagmi';
import { useReadContract } from 'wagmi';
import { ESCROW_ABI, BLOCK_PUBLISHER_ABI, REWARD_DISTRIBUTION_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { formatEther } from 'viem';
import Badge from './Badge';
import Button from './Button';
import { type Task } from '@/lib/api';

interface TaskTimelineProps {
  task: Task;
  onRegister?: () => void;
  onPublishBlock?: () => void;
  onRevealAccuracy?: () => void;
  onRevealScore?: () => void;
  onDistributeRewards?: () => void;
}

export default function TaskTimeline({
  task,
  onRegister,
  onPublishBlock,
  onRevealAccuracy,
  onRevealScore,
  onDistributeRewards,
}: TaskTimelineProps) {
  const { address, chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;

  const isPublisher = address && task.publisher?.toLowerCase() === address.toLowerCase();
  const isMiner = address && !isPublisher;

  // Use task's escrow contract address if available, otherwise fall back to env variable
  const escrowAddress = (task.escrowContractAddress || chainConfig?.contracts.escrow) as `0x${string}` | undefined;

  const { data: escrowBalance } = useReadContract({
    address: escrowAddress,
    abi: ESCROW_ABI,
    functionName: 'escrowBalance',
    args: [task.taskID],
    query: { enabled: !!escrowAddress },
  });

  const { data: contractTask } = useReadContract({
    address: escrowAddress,
    abi: ESCROW_ABI,
    functionName: 'tasks',
    args: [task.taskID],
    query: { enabled: !!escrowAddress },
  });

  const { data: publishedBlock } = useReadContract({
    address: chainConfig?.contracts.blockPublisher as `0x${string}`,
    abi: BLOCK_PUBLISHER_ABI,
    functionName: 'publishedBlocks',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.blockPublisher },
  });

  const { data: accuracyRevealed } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'accuracyRevealed',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });

  const miners = (task as any).miners || [];
  const minerCount = miners.length;
  const requiredMiners = task.maxMiners || 5; // Use task-specific maxMiners
  const minRequired = task.minMiners || 3; // Use task-specific minMiners
  
  // M1: Completed if escrow > 0 on-chain, or if task exists in backend (fallback)
  // If escrow is 0 but task exists, it means escrow transaction wasn't completed
  const m1Completed = escrowBalance && escrowBalance > 0n;
  const m1InProgress = !m1Completed && task.status !== 'CANCELLED' && task.status !== 'FAILED';
  
  // M2: Complete when we have at least minMiners miners
  const m2InProgress = (task.status === 'CREATED' || task.status === 'OPEN') && minerCount > 0 && minerCount < minRequired;
  const m2Complete = minerCount >= minRequired; // M2 complete when we have at least minMiners
  const m6Published = publishedBlock && (publishedBlock as any).timestamp > 0n;
  const m7aDone = accuracyRevealed === true;

  return (
    <div className="space-y-4">
      <div className="border-l-2 border-gray-300 dark:border-gray-600 pl-4 space-y-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M1] Task Published</span>
            {m1Completed ? (
              <Badge variant="success">✅ Completed</Badge>
            ) : m1InProgress ? (
              <Badge variant="warning">⚠️ Escrow Pending</Badge>
            ) : (
              <Badge variant="neutral">⏳ Pending</Badge>
            )}
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {m1Completed ? (
              <>
                <p>└─ Escrow: {escrowBalance ? formatEther(escrowBalance) : '0'} ETH (Locked)</p>
                {contractTask && (
                  <p className="font-mono text-xs">
                    └─ Commit Hash: {(contractTask as any).accuracyCommit?.slice(0, 20)}...
                  </p>
                )}
              </>
            ) : m1InProgress ? (
              <p className="text-yellow-600 dark:text-yellow-400">
                └─ ⚠️ Task created but escrow not locked on-chain. Publisher must complete escrow transaction.
              </p>
            ) : (
              <p>└─ Waiting for task creation</p>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M2] Miner Registration</span>
            {m2Complete ? (
              <Badge variant="success">✅ Completed</Badge>
            ) : m2InProgress ? (
              <Badge variant="warning">🔄 In Progress</Badge>
            ) : (
              <Badge variant="neutral">⏳ Pending</Badge>
            )}
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Registered: {minerCount}/{requiredMiners} miners (minimum {minRequired} required)</p>
            {m2Complete && (task as any).aggregator && (
              <p className="text-green-600 dark:text-green-400">
                └─ ✅ Aggregator selected: {(task as any).aggregator.slice(0, 10)}...
              </p>
            )}
            {isMiner && task.status === 'OPEN' && !m2Complete && (
              <Button variant="primary" size="sm" onClick={onRegister} className="mt-2">
                Register as Miner
              </Button>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M3] Training Phase</span>
            <Badge variant="neutral">⏳ Pending</Badge>
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Status: Waiting for miners</p>
            <p className="text-xs italic">└─ Note: Training happens off-chain (FL-client)</p>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M4] Aggregation</span>
            <Badge variant="neutral">⏳ Pending</Badge>
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Status: Waiting for training completion</p>
            <p className="text-xs italic">└─ Note: Aggregation happens off-chain (aggregator)</p>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M5] Verification</span>
            <Badge variant="neutral">⏳ Pending</Badge>
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Status: Waiting for aggregation</p>
            <p className="text-xs italic">└─ Note: Consensus happens off-chain (aggregator)</p>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M6] Block Publishing</span>
            {m6Published ? (
              <Badge variant="success">✅ Published</Badge>
            ) : (
              <Badge variant="neutral">⏳ Pending</Badge>
            )}
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Status: {m6Published ? 'Published' : 'Waiting for verification'}</p>
            {isPublisher && !m6Published && task.status === 'VERIFIED' && (
              <Button variant="primary" size="sm" onClick={onPublishBlock} className="mt-2">
                Publish Block
              </Button>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-gray-900 dark:text-white">[M7] Reveal & Rewards</span>
            {m7aDone ? (
              <Badge variant="warning">🔄 In Progress</Badge>
            ) : (
              <Badge variant="neutral">⏳ Pending</Badge>
            )}
          </div>
          <div className="ml-6 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p>└─ Status: {m7aDone ? 'Reveal phase active' : 'Waiting for block publishing'}</p>
            {isPublisher && m6Published && !m7aDone && (
              <Button variant="primary" size="sm" onClick={onRevealAccuracy} className="mt-2">
                Reveal Accuracy
              </Button>
            )}
            {isMiner && m7aDone && (
              <Button variant="primary" size="sm" onClick={onRevealScore} className="mt-2">
                Reveal Score
              </Button>
            )}
            {isPublisher && m7aDone && (
              <Button variant="primary" size="sm" onClick={onDistributeRewards} className="mt-2">
                Distribute Rewards
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

