'use client';

import { useState, useEffect } from 'react';
import { useAccount } from 'wagmi';
import { useReadContract } from 'wagmi';
import { useTaskList } from '@/hooks/useTask';
import { useContract } from '@/hooks/useContract';
import { REWARD_DISTRIBUTION_ABI, BLOCK_PUBLISHER_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { formatEther } from 'viem';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import ScoreRevealForm from '@/components/forms/ScoreRevealForm';
import Link from 'next/link';

export default function RewardsPage() {
  const { address, isConnected, chainId } = useAccount();
  const { tasks, loading, refresh } = useTaskList();
  const chainConfig = chainId ? getChainConfig(chainId) : null;

  const rewardTasks = tasks?.filter(
    (t) => t.status === 'REVEAL_OPEN' || t.status === 'REVEAL_CLOSED' || t.status === 'VERIFIED'
  ) || [];

  const publisherTasks = rewardTasks.filter(
    (t) => t.publisher?.toLowerCase() === address?.toLowerCase()
  );

  const minerTasks = rewardTasks.filter((t) => {
    return (t as any).miners?.some((m: any) => m.address?.toLowerCase() === address?.toLowerCase());
  });

  const isPublisher = publisherTasks.length > 0;
  const isMiner = minerTasks.length > 0;

  if (!isConnected) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Connect Your Wallet
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Please connect your wallet to view and claim rewards
            </p>
            <Link href="/">
              <Button variant="primary">Go to Dashboard</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Rewards & Reveals</h1>
        <div className="mt-2 flex items-center gap-2">
          {isPublisher && <Badge variant="info">Publisher</Badge>}
          {isMiner && <Badge variant="info">Miner</Badge>}
          {!isPublisher && !isMiner && <Badge variant="neutral">Observer</Badge>}
        </div>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Protocol Information</h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>Module:</strong> M7 - Commit-Reveal & Rewards</p>
          <p><strong>Steps:</strong></p>
          <ol className="list-decimal list-inside ml-4 space-y-1">
            <li>Publisher reveals accuracy (M7a)</li>
            <li>Miners reveal scores (M7b)</li>
            <li>Publisher distributes rewards (M7c)</li>
          </ol>
          <p className="mt-2"><strong>Note:</strong> All reveals must match commits from M1/M3</p>
        </div>
      </Card>

      {isPublisher && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">My Tasks - Publisher View</h2>
          {publisherTasks.length === 0 ? (
            <p className="text-sm text-gray-600 dark:text-gray-400">No tasks awaiting reveal</p>
          ) : (
            <div className="space-y-4">
              {publisherTasks.map((task) => (
                <PublisherTaskCard key={task.taskID} task={task} />
              ))}
            </div>
          )}
        </Card>
      )}

      {isMiner && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">My Participations - Miner View</h2>
          {minerTasks.length === 0 ? (
            <p className="text-sm text-gray-600 dark:text-gray-400">No tasks where you participated</p>
          ) : (
            <div className="space-y-4">
              {minerTasks.map((task) => (
                <MinerTaskCard key={task.taskID} task={task} address={address!} />
              ))}
            </div>
          )}
        </Card>
      )}

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Reward Distribution Status</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-600 dark:text-gray-400">Total Distributed:</dt>
            <dd className="text-gray-900 dark:text-white font-medium">0 ETH</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600 dark:text-gray-400">Pending Distribution:</dt>
            <dd className="text-gray-900 dark:text-white font-medium">
              {rewardTasks.reduce((sum, t) => sum + (parseFloat(t.escrowBalance || '0') || 0), 0).toFixed(4)} ETH
            </dd>
          </div>
          {address && (
            <div className="flex justify-between">
              <dt className="text-gray-600 dark:text-gray-400">My Total Rewards:</dt>
              <dd className="text-gray-900 dark:text-white font-medium">0 ETH</dd>
            </div>
          )}
        </dl>
      </Card>
    </div>
  );
}

// Component to check a single miner's reveal status
function MinerRevealStatus({ taskID, minerAddress, chainConfig, onRevealed }: { 
  taskID: string; 
  minerAddress: string; 
  chainConfig: any;
  onRevealed: (revealed: boolean) => void;
}) {
  const { data: minerReveal } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'minerReveals',
    args: [taskID, minerAddress],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution && !!minerAddress },
  });

  useEffect(() => {
    if (minerReveal) {
      onRevealed((minerReveal as any).revealed === true);
    }
  }, [minerReveal, onRevealed]);

  return null; // This component doesn't render anything
}

function PublisherTaskCard({ task }: { task: any }) {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const { revealAccuracy, distributeRewards } = useContract();
  const [showRevealForm, setShowRevealForm] = useState(false);
  const [showDistribute, setShowDistribute] = useState(false);
  const [revealedMiners, setRevealedMiners] = useState<Set<string>>(new Set());

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
  const totalMiners = miners.length;
  const revealedMinersCount = revealedMiners.size;

  const handleMinerRevealed = (minerAddress: string) => (revealed: boolean) => {
    setRevealedMiners((prev) => {
      const next = new Set(prev);
      if (revealed) {
        next.add(minerAddress);
      } else {
        next.delete(minerAddress);
      }
      return next;
    });
  };

  const m6Complete = publishedBlock && (publishedBlock as any).timestamp > 0n;
  const m7aDone = accuracyRevealed === true;
  
  // Get accuracy from published block (if available) or use placeholder
  const revealedAccuracy = publishedBlock && (publishedBlock as any).accuracy 
    ? ((publishedBlock as any).accuracy / 1e6).toFixed(2) + '%'
    : 'N/A';

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-medium text-gray-900 dark:text-white">Task: {task.taskID}</h3>
        <TaskStatusBadge status={task.status} />
      </div>
      <dl className="space-y-2 text-sm mb-4">
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Escrow:</dt>
          <dd className="text-gray-900 dark:text-white font-mono">
            {task.escrowBalance ? formatEther(BigInt(task.escrowBalance)) : '0'} ETH
          </dd>
        </div>
        {task.commitHash && (
          <div>
            <dt className="text-gray-600 dark:text-gray-400">Accuracy Commit:</dt>
            <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
              {task.commitHash}
            </dd>
          </div>
        )}
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Block Published:</dt>
          <dd className="text-gray-900 dark:text-white">
            {m6Complete ? '✅ (M6 complete)' : '❌ (M6 pending)'}
          </dd>
        </div>
      </dl>

      {!m7aDone && m6Complete && (
        <div className="space-y-2">
          <Button variant="primary" size="sm" onClick={() => setShowRevealForm(true)}>
            Reveal Accuracy (M7a)
          </Button>
          {showRevealForm && (
            <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                Opens form: Accuracy value, Nonce
              </p>
              <Link href={`/tasks/${task.taskID}`}>
                <Button variant="outline" size="sm">Go to Task Detail</Button>
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Render miner reveal status checkers (hidden) */}
      {miners.map((miner: any) => {
        const minerAddress = miner.address || miner;
        return minerAddress ? (
          <MinerRevealStatus
            key={minerAddress}
            taskID={task.taskID}
            minerAddress={minerAddress}
            chainConfig={chainConfig}
            onRevealed={handleMinerRevealed(minerAddress)}
          />
        ) : null;
      })}

      {m7aDone && (
        <div className="space-y-2">
          <dl className="text-sm space-y-1">
            <div>
              <dt className="text-gray-600 dark:text-gray-400">Accuracy Revealed:</dt>
              <dd className="text-gray-900 dark:text-white">
                {revealedAccuracy !== 'N/A' ? revealedAccuracy : 'N/A'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-600 dark:text-gray-400">Miners Revealed:</dt>
              <dd className="text-gray-900 dark:text-white">
                {totalMiners > 0 ? `${revealedMinersCount}/${totalMiners}` : '0/0'}
              </dd>
            </div>
          </dl>
          <Button variant="primary" size="sm" onClick={() => setShowDistribute(true)}>
            Distribute Rewards (M7c)
          </Button>
          {showDistribute && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
              Triggers: RewardDistribution.distribute()
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function MinerTaskCard({ task, address }: { task: any; address: string }) {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const [showRevealForm, setShowRevealForm] = useState(false);

  const { data: accuracyRevealed } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'accuracyRevealed',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });

  const { data: minerReveal } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'minerReveals',
    args: [task.taskID, address],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution && !!address },
  });

  const { data: publishedBlock } = useReadContract({
    address: chainConfig?.contracts.blockPublisher as `0x${string}`,
    abi: BLOCK_PUBLISHER_ABI,
    functionName: 'publishedBlocks',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.blockPublisher },
  });

  const m7aDone = accuracyRevealed === true;
  const myScoreRevealed = minerReveal && (minerReveal as any).revealed === true;
  
  // Get score commit from published block or task data
  const scoreCommits = publishedBlock && (publishedBlock as any).scoreCommits 
    ? (publishedBlock as any).scoreCommits 
    : [];
  const myScoreCommit = scoreCommits.length > 0 
    ? `${scoreCommits[0]?.slice(0, 10)}...${scoreCommits[0]?.slice(-6)}` 
    : task.scoreCommit || '0x000...000';
  
  // Get revealed score from contract if available
  const myRevealedScore = minerReveal && (minerReveal as any).score 
    ? ((minerReveal as any).score / 1e6).toFixed(2)
    : null;
  
  // Get accuracy from published block
  const publisherAccuracy = publishedBlock && (publishedBlock as any).accuracy 
    ? ((publishedBlock as any).accuracy / 1e6).toFixed(2) + '%'
    : null;

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-medium text-gray-900 dark:text-white">Task: {task.taskID}</h3>
        <TaskStatusBadge status={task.status} />
      </div>
      <dl className="space-y-2 text-sm mb-4">
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Publisher Revealed:</dt>
          <dd className="text-gray-900 dark:text-white">
            {m7aDone ? (publisherAccuracy ? `✅ (Accuracy: ${publisherAccuracy})` : '✅ (Accuracy: N/A)') : '❌ Not yet'}
          </dd>
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">My Score Commit:</dt>
          <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">{myScoreCommit}</dd>
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">My Score Revealed:</dt>
          <dd className="text-gray-900 dark:text-white">
            {myScoreRevealed ? (myRevealedScore ? `✅ (Score: ${myRevealedScore})` : '✅ (Score: Revealed)') : '❌ Not yet'}
          </dd>
        </div>
      </dl>

      {m7aDone && !myScoreRevealed && (
        <div className="space-y-2">
          <Button variant="primary" size="sm" onClick={() => setShowRevealForm(true)}>
            Reveal Score (M7b)
          </Button>
          {showRevealForm && (
            <div className="mt-2">
              <ScoreRevealForm
                taskID={task.taskID}
                scoreCommit={myScoreCommit}
                onSuccess={() => {
                  setShowRevealForm(false);
                }}
              />
            </div>
          )}
        </div>
      )}

      {myScoreRevealed && (
        <div className="text-sm">
          <p className="text-gray-600 dark:text-gray-400">My Reward Share:</p>
          <p className="text-gray-900 dark:text-white font-medium">0.5 ETH (pending distribution)</p>
        </div>
      )}
    </div>
  );
}
