'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useAccount } from 'wagmi';
import { useReadContract } from 'wagmi';
import { useTaskList } from '@/hooks/useTask';
import { useContract } from '@/hooks/useContract';
import { REWARD_DISTRIBUTION_ABI, BLOCK_PUBLISHER_ABI, ESCROW_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { verificationAPI } from '@/lib/api';
import { formatEther } from 'viem';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import ScoreRevealForm from '@/components/forms/ScoreRevealForm';
import AccuracyRevealForm from '@/components/forms/AccuracyRevealForm';
import Link from 'next/link';

function formatAccuracyPercent(value: unknown): string | null {
  if (value === null || value === undefined) return null;

  let numeric: number;
  if (typeof value === 'bigint') {
    numeric = Number(value);
  } else if (typeof value === 'number') {
    numeric = value;
  } else if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    numeric = Number(trimmed);
  } else {
    return null;
  }

  if (!Number.isFinite(numeric)) return null;

  let pct = numeric;
  if (numeric > 1000) {
    // Stored as scaled integer (x 1e6)
    pct = numeric / 1e6;
  } else if (numeric >= 0 && numeric <= 1) {
    // Stored as ratio (0..1)
    pct = numeric * 100;
  }

  return `${pct.toFixed(2)}%`;
}

function normalizeCommitHash(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim().replace(/^0x/i, '');
  if (!/^[0-9a-fA-F]{64}$/.test(trimmed)) return null;
  if (/^0{64}$/.test(trimmed)) return null;
  return `0x${trimmed}`;
}

export default function RewardsPage() {
  const { address, isConnected } = useAccount();
  const { tasks, refresh } = useTaskList();

  const rewardTasks = useMemo(
    () =>
      tasks?.filter((t: any) => {
        const verificationOpen =
          t?.verificationOpen === true ||
          (t?.status === 'AGGREGATING' && !!t?.block?.candidateHash);
        return (
          verificationOpen ||
          t.status === 'REVEAL_OPEN' ||
          t.status === 'REVEAL_CLOSED' ||
          t.status === 'VERIFIED' ||
          t.status === 'REWARDED'
        );
      }) || [],
    [tasks]
  );

  const publisherTasks = rewardTasks.filter(
    (t) => t.publisher?.toLowerCase() === address?.toLowerCase()
  );

  const minerTasks = rewardTasks.filter((t) => {
    return (t as any).miners?.some((m: any) => m.address?.toLowerCase() === address?.toLowerCase());
  });

  const isPublisher = publisherTasks.length > 0;
  const isMiner = minerTasks.length > 0;

  const { totalDistributedEth, pendingDistributionEth, myTotalRewardsEth } = useMemo(() => {
    return rewardTasks.reduce(
      (acc, t: any) => {
        const taskRewards = Array.isArray(t?.rewards) ? t.rewards : [];
        const distributedRows = taskRewards.filter(
          (r: any) => String(r?.status || '').toUpperCase() === 'DISTRIBUTED'
        );
        const distributedForTask = distributedRows.reduce(
          (sum: number, r: any) => sum + (parseFloat(String(r?.amountETH ?? '0')) || 0),
          0
        );

        acc.totalDistributedEth += distributedForTask;

        const hasAnyDistributed = distributedRows.length > 0;
        if (!hasAnyDistributed && (
          t?.status === 'VERIFIED' ||
          t?.status === 'REVEAL_OPEN' ||
          t?.status === 'REVEAL_CLOSED'
        )) {
          const escrow = parseFloat(t?.escrowBalance || '0') || 0;
          acc.pendingDistributionEth += escrow;
        }

        if (address) {
          const myRows = distributedRows.filter(
            (r: any) => String(r?.minerAddress || '').toLowerCase() === address.toLowerCase()
          );
          acc.myTotalRewardsEth += myRows.reduce(
            (sum: number, r: any) => sum + (parseFloat(String(r?.amountETH ?? '0')) || 0),
            0
          );
        }

        return acc;
      },
      { totalDistributedEth: 0, pendingDistributionEth: 0, myTotalRewardsEth: 0 }
    );
  }, [rewardTasks, address]);

  useEffect(() => {
    if (!isConnected) return;
    refresh();
    const intervalId = setInterval(() => {
      refresh();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [isConnected, refresh]);

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
            <p className="text-sm text-gray-600 dark:text-gray-400">No tasks in verification/reveal phase</p>
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
            <dd className="text-gray-900 dark:text-white font-medium">
              {totalDistributedEth.toFixed(4)} ETH
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600 dark:text-gray-400">Pending Distribution:</dt>
            <dd className="text-gray-900 dark:text-white font-medium">
              {pendingDistributionEth.toFixed(4)} ETH
            </dd>
          </div>
          {address && (
            <div className="flex justify-between">
              <dt className="text-gray-600 dark:text-gray-400">My Total Rewards:</dt>
              <dd className="text-gray-900 dark:text-white font-medium">
                {myTotalRewardsEth.toFixed(4)} ETH
              </dd>
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

  const lastReportedRef = useRef<boolean | null>(null);

  useEffect(() => {
    if (minerReveal) {
      const revealed = (minerReveal as any).revealed === true;
      // Avoid parent-state update loops when effect reruns with equivalent value.
      if (lastReportedRef.current === revealed) return;
      lastReportedRef.current = revealed;
      onRevealed(revealed);
    }
  }, [minerReveal, onRevealed]);

  return null; // This component doesn't render anything
}

function PublisherTaskCard({ task }: { task: any }) {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const [showRevealForm, setShowRevealForm] = useState(false);
  const [showDistribute, setShowDistribute] = useState(false);
  const [distributeError, setDistributeError] = useState<string | null>(null);
  const [distributeInfo, setDistributeInfo] = useState<string | null>(null);
  const [distributeSubmitted, setDistributeSubmitted] = useState(false);
  const [revealedMiners, setRevealedMiners] = useState<Set<string>>(new Set());
  const {
    distributeRewards,
    hash: distributeTxHash,
    isPending: distributePending,
    isConfirming: distributeConfirming,
    isConfirmed: distributeConfirmed,
  } = useContract();
  const escrowAddress = (task.escrowContractAddress || chainConfig?.contracts.escrow) as `0x${string}` | undefined;

  const { data: escrowBalanceOnChain } = useReadContract({
    address: escrowAddress,
    abi: ESCROW_ABI,
    functionName: 'escrowBalance',
    args: [task.taskID],
    query: { enabled: !!escrowAddress },
  });
  const { data: escrowTask } = useReadContract({
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
  const { data: revealedAccuracyOnChain } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'revealedAccuracy',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });
  const { data: rewardsDistributedOnChain } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'rewardsDistributed',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });

  const miners = (task as any).miners || [];
  const totalMiners = miners.length;
  const revealedMinersCount = revealedMiners.size;
  const verificationOpen =
    task?.verificationOpen === true ||
    (task?.status === 'AGGREGATING' && !!task?.block?.candidateHash);

  const handleMinerRevealed = (minerAddress: string) => (revealed: boolean) => {
    setRevealedMiners((prev) => {
      const alreadyHas = prev.has(minerAddress);
      if ((revealed && alreadyHas) || (!revealed && !alreadyHas)) {
        return prev;
      }
      const next = new Set(prev);
      if (revealed) {
        next.add(minerAddress);
      } else {
        next.delete(minerAddress);
      }
      return next;
    });
  };

  const m6PublishedOnChain = !!publishedBlock && (publishedBlock as any).timestamp > 0n;
  const m6Complete =
    m6PublishedOnChain ||
    task.status === 'REVEAL_OPEN' ||
    task.status === 'REVEAL_CLOSED' ||
    task.status === 'REWARDED';
  const m7DistributedOnChain = rewardsDistributedOnChain === true;
  const escrowBalance = (() => {
    if (typeof escrowBalanceOnChain === 'bigint') return escrowBalanceOnChain;
    try {
      return task.escrowBalance ? BigInt(task.escrowBalance) : 0n;
    } catch {
      return 0n;
    }
  })();
  const m7aDone = accuracyRevealed === true || m7DistributedOnChain || task.status === 'REWARDED';
  const rewardRows = Array.isArray((task as any)?.rewards) ? (task as any).rewards : [];
  const distributedRewardRows = rewardRows.filter(
    (r: any) => String(r?.status || '').toUpperCase() === 'DISTRIBUTED'
  );
  const distributedAmountEth = distributedRewardRows.reduce(
    (sum: number, r: any) => sum + (parseFloat(String(r?.amountETH ?? '0')) || 0),
    0
  );
  const distributedMinerCount = new Set(
    distributedRewardRows.map((r: any) => String(r?.minerAddress || '').toLowerCase())
  ).size;
  
  // Prefer explicit M7a revealed accuracy; fallback to block/task values for compatibility.
  const revealedAccuracy =
    formatAccuracyPercent(revealedAccuracyOnChain) ||
    formatAccuracyPercent((publishedBlock as any)?.accuracy) ||
    formatAccuracyPercent((task as any)?.block?.accuracy);
  const commitHashForReveal =
    normalizeCommitHash(task.commitHash) ||
    normalizeCommitHash((escrowTask as any)?.accuracyCommit) ||
    normalizeCommitHash((escrowTask as any)?.[3]);

  const handleDistributeRewards = async () => {
    setShowDistribute(true);
    setDistributeError(null);
    setDistributeInfo(null);
    setDistributeSubmitted(false);

    if (!chainConfig?.contracts.rewardDistribution) {
      setDistributeError('RewardDistribution contract not configured for this network.');
      return;
    }

    if (!m7aDone) {
      setDistributeError('Publisher accuracy reveal (M7a) is required before M7c.');
      return;
    }

    if (!m6Complete) {
      setDistributeError('Block publishing (M6) must be complete before M7c.');
      return;
    }
    if (m7DistributedOnChain) {
      setDistributeInfo('Rewards are already distributed on-chain for this task.');
      return;
    }

    // Contract ignores miners in the backward-compatible overload, but pass validated addresses.
    const minersForTx = (miners || [])
      .map((m: any) => (m?.address || m || '').toString())
      .filter((addr: string) => /^0x[a-fA-F0-9]{40}$/.test(addr)) as `0x${string}`[];

    try {
      await distributeRewards(task.taskID, minersForTx);
      setDistributeSubmitted(true);
    } catch (err: any) {
      const rawMsg =
        err?.shortMessage ||
        err?.details ||
        err?.message ||
        'Failed to trigger reward distribution';
      const normalized = String(rawMsg).toLowerCase();
      if (normalized.includes('no scores')) {
        setDistributeError(
          'Current on-chain RewardDistribution requires at least one miner score reveal (M7b) before M7c. ' +
          'Reveal one valid miner score for this task, then retry distribution.'
        );
      } else if (normalized.includes('rewards already distributed')) {
        setDistributeError(null);
        setDistributeInfo('Rewards are already distributed on-chain for this task.');
      } else {
        setDistributeError(String(rawMsg));
      }
    }
  };

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-medium text-gray-900 dark:text-white">Task: {task.taskID}</h3>
        <TaskStatusBadge status={task.status} />
        {verificationOpen && <Badge variant="warning">Verification Open</Badge>}
        {m7DistributedOnChain && <Badge variant="success">Rewards Distributed</Badge>}
      </div>
      <dl className="space-y-2 text-sm mb-4">
        <div>
          <dt className="text-gray-600 dark:text-gray-400">Escrow:</dt>
          <dd className="text-gray-900 dark:text-white font-mono">
            {formatEther(escrowBalance)} ETH
          </dd>
        </div>
        {commitHashForReveal && (
          <div>
            <dt className="text-gray-600 dark:text-gray-400">Accuracy Commit:</dt>
            <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
              {commitHashForReveal}
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

      {verificationOpen && (
        <div className="mb-4 p-2 rounded bg-amber-50 dark:bg-amber-900/20 text-xs text-amber-700 dark:text-amber-300">
          M5 is active for this task. Participants can submit verification feedback while status is AGGREGATING.
        </div>
      )}

      {!m7aDone && m6Complete && (
        <div className="space-y-2">
          <Button variant="primary" size="sm" onClick={() => setShowRevealForm((prev) => !prev)}>
            {showRevealForm ? 'Hide Reveal Form (M7a)' : 'Reveal Accuracy (M7a)'}
          </Button>
          {showRevealForm && (
            <div className="mt-2">
              <AccuracyRevealForm
                taskID={task.taskID}
                commitHash={commitHashForReveal || ''}
                onSuccess={() => setShowRevealForm(false)}
              />
            </div>
          )}
          {!commitHashForReveal && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Commit hash is unavailable from backend and escrow. Refresh after chain sync.
            </p>
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
                {revealedAccuracy || 'N/A'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-600 dark:text-gray-400">Miners Revealed:</dt>
              <dd className="text-gray-900 dark:text-white">
                {totalMiners > 0 ? `${revealedMinersCount}/${totalMiners}` : '0/0'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-600 dark:text-gray-400">Rewards Recorded (DB):</dt>
              <dd className="text-gray-900 dark:text-white">
                {distributedMinerCount}/{totalMiners}
                {distributedRewardRows.length > 0 ? `, ${distributedAmountEth.toFixed(4)} ETH` : ''}
              </dd>
            </div>
          </dl>
          <Button
            variant="primary"
            size="sm"
            onClick={handleDistributeRewards}
            disabled={m7DistributedOnChain || distributePending || distributeConfirming}
          >
            {m7DistributedOnChain
              ? 'Rewards Already Distributed'
              : distributePending || distributeConfirming
                ? 'Distributing...'
                : 'Distribute Rewards (M7c)'}
          </Button>
          {showDistribute && (
            <div className="mt-2 space-y-1">
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Triggers: RewardDistribution.distribute()
              </p>
              {distributeSubmitted && !distributeTxHash && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Distribution transaction requested in wallet.
                </p>
              )}
              {distributeTxHash && (
                <p className="text-xs text-gray-700 dark:text-gray-300 break-all">
                  Tx: <span className="font-mono">{distributeTxHash}</span>
                </p>
              )}
              {distributeConfirmed && (
                <p className="text-xs text-green-600 dark:text-green-400">
                  Distribution transaction confirmed on-chain.
                </p>
              )}
              {distributeInfo && (
                <p className="text-xs text-green-600 dark:text-green-400 break-all">
                  {distributeInfo}
                </p>
              )}
              {distributeError && (
                <p className="text-xs text-red-600 dark:text-red-400 break-all">
                  {distributeError}
                </p>
              )}
            </div>
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
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [myVerification, setMyVerification] = useState<any | null>(null);
  const [consensus, setConsensus] = useState<any | null>(null);

  const { data: accuracyRevealed } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'accuracyRevealed',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });
  const { data: revealedAccuracyOnChain } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'revealedAccuracy',
    args: [task.taskID],
    query: { enabled: !!chainConfig?.contracts.rewardDistribution },
  });
  const { data: rewardsDistributedOnChain } = useReadContract({
    address: chainConfig?.contracts.rewardDistribution as `0x${string}`,
    abi: REWARD_DISTRIBUTION_ABI,
    functionName: 'rewardsDistributed',
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

  const m7DistributedOnChain = rewardsDistributedOnChain === true;
  const m7aDone = accuracyRevealed === true || m7DistributedOnChain || task.status === 'REWARDED';
  const myScoreRevealed = minerReveal && (minerReveal as any).revealed === true;
  const rewardRows = Array.isArray((task as any)?.rewards) ? (task as any).rewards : [];
  const myRewardRow = rewardRows.find(
    (r: any) => String(r?.minerAddress || '').toLowerCase() === address.toLowerCase()
  );
  const myRewardDistributed =
    !!myRewardRow && String(myRewardRow?.status || '').toUpperCase() === 'DISTRIBUTED';
  const myRewardAmountEth = parseFloat(String(myRewardRow?.amountETH ?? '0')) || 0;
  const verificationOpen =
    task?.verificationOpen === true ||
    (task?.status === 'AGGREGATING' && !!task?.block?.candidateHash);
  const candidateHash = task?.block?.candidateHash || '';
  const myMinerRecord = ((task as any).miners || []).find((m: any) => m?.address?.toLowerCase() === address.toLowerCase());
  const myMinerPublicKey = myMinerRecord?.publicKey || '';

  const loadVerificationState = useCallback(async () => {
    if (!verificationOpen || !candidateHash) {
      setMyVerification(null);
      setConsensus(null);
      return;
    }
    try {
      const [verifications, consensusResult] = await Promise.all([
        verificationAPI.getByTask(task.taskID),
        verificationAPI.getConsensus(task.taskID),
      ]);
      const mine =
        (verifications || []).find(
          (v: any) =>
            v?.minerAddress?.toLowerCase() === address.toLowerCase() &&
            v?.candidateHash === candidateHash
        ) || null;
      setMyVerification(mine);
      setConsensus(consensusResult || null);
    } catch {
      // Keep UI resilient if backend polling fails transiently.
    }
  }, [address, candidateHash, task.taskID, verificationOpen]);

  useEffect(() => {
    if (!verificationOpen || !candidateHash) return;
    loadVerificationState();
    const id = setInterval(loadVerificationState, 5000);
    return () => clearInterval(id);
  }, [verificationOpen, candidateHash, loadVerificationState]);

  const handleSubmitVerification = async () => {
    if (!verificationOpen) {
      setSubmitError('Verification phase is not open for this task.');
      return;
    }
    if (!candidateHash) {
      setSubmitError('Missing candidate hash. Wait for candidate sync.');
      return;
    }
    setSubmitLoading(true);
    setSubmitError(null);
    setSubmitSuccess(null);
    try {
      await verificationAPI.triggerViaFlClient(task.taskID, address);
      setSubmitSuccess('Verification submitted via FL client successfully.');
      await loadVerificationState();
    } catch (err: any) {
      const msg =
        err?.response?.data?.error ||
        err?.responseData?.error ||
        err?.message ||
        'Failed to submit verification';
      setSubmitError(String(msg));
    } finally {
      setSubmitLoading(false);
    }
  };

  // Prefer backend-recorded commit keyed by miner address.
  const taskScoreCommitsByMiner = ((task as any).scoreCommitsByMiner || {}) as Record<string, string>;
  const myRawScoreCommitFromTask = taskScoreCommitsByMiner[address.toLowerCase()];

  // Fallback to on-chain score commit list only when there is exactly one commit.
  // With multiple commits, index-to-miner mapping is not guaranteed in this view.
  const scoreCommits = publishedBlock && (publishedBlock as any).scoreCommits 
    ? (publishedBlock as any).scoreCommits 
    : [];
  const myRawScoreCommit = myRawScoreCommitFromTask || (scoreCommits.length === 1 ? scoreCommits[0] : '');
  const normalizedScoreCommit = (myRawScoreCommit || '').startsWith('0x')
    ? (myRawScoreCommit || '')
    : (myRawScoreCommit ? `0x${myRawScoreCommit}` : '');
  const hasValidScoreCommit = /^0x[a-fA-F0-9]{64}$/.test(normalizedScoreCommit);
  const myScoreCommit = hasValidScoreCommit
    ? `${normalizedScoreCommit.slice(0, 10)}...${normalizedScoreCommit.slice(-6)}`
    : 'Unavailable';
  
  // Get revealed score from contract if available
  const myRevealedScore = minerReveal && (minerReveal as any).score 
    ? ((minerReveal as any).score / 1e6).toFixed(2)
    : null;
  
  // Prefer explicit M7a revealed accuracy; fallback to block/task values for compatibility.
  const publisherAccuracy =
    formatAccuracyPercent(revealedAccuracyOnChain) ||
    formatAccuracyPercent((publishedBlock as any)?.accuracy) ||
    formatAccuracyPercent((task as any)?.block?.accuracy);

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-medium text-gray-900 dark:text-white">Task: {task.taskID}</h3>
        <TaskStatusBadge status={task.status} />
        {verificationOpen && <Badge variant="warning">Verification Open</Badge>}
        {m7DistributedOnChain && <Badge variant="success">Rewards Distributed</Badge>}
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
          <dd className="text-gray-900 dark:text-white font-mono text-xs break-all">
            {myScoreCommit}
          </dd>
        </div>
        <div>
          <dt className="text-gray-600 dark:text-gray-400">My Score Revealed:</dt>
          <dd className="text-gray-900 dark:text-white">
            {myScoreRevealed ? (myRevealedScore ? `✅ (Score: ${myRevealedScore})` : '✅ (Score: Revealed)') : '❌ Not yet'}
          </dd>
        </div>
      </dl>

      {verificationOpen && (
        <div className="mb-4 p-2 rounded bg-amber-50 dark:bg-amber-900/20 text-xs text-amber-700 dark:text-amber-300">
          M5 verification is active. Keep this page open; task state is polled every 5 seconds from the frontend.
        </div>
      )}

      {verificationOpen && (
        <div className="mb-4 p-3 border border-amber-300/50 dark:border-amber-700/50 rounded bg-amber-50/60 dark:bg-amber-900/20">
          <div className="text-xs text-gray-700 dark:text-gray-300 mb-2">
            <div>Candidate Hash: <span className="font-mono break-all">{candidateHash || 'N/A'}</span></div>
            <div>Consensus: {consensus ? `${consensus.validVotes}/${consensus.totalMiners} VALID (need ${consensus.majorityRequired})` : 'Loading...'}</div>
          </div>

          {myVerification ? (
            <div className="text-sm">
              <div className="font-medium text-green-700 dark:text-green-400">You already submitted M5 feedback.</div>
              <div className="text-xs text-gray-700 dark:text-gray-300 mt-1">
                Verdict: <span className="font-mono">{myVerification.verdict}</span>
                {myVerification.reason ? ` | Reason: ${myVerification.reason}` : ''}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmitVerification}
                disabled={submitLoading || !candidateHash}
              >
                {submitLoading ? 'Submitting...' : 'Submit Verification (M5 via FL Client)'}
              </Button>
              {!myMinerPublicKey && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  Your miner public key is missing. Re-sync task/registration metadata.
                </p>
              )}
              <p className="text-xs text-gray-600 dark:text-gray-400">
                This calls your local FL client verifier (`/api/verify`) which auto-computes VALID/INVALID,
                signs with miner FL key, and submits strict Algorithm-5 feedback.
              </p>
            </div>
          )}

          {submitError && <p className="text-xs text-red-600 dark:text-red-400 mt-2">{submitError}</p>}
          {submitSuccess && <p className="text-xs text-green-600 dark:text-green-400 mt-2">{submitSuccess}</p>}
        </div>
      )}

      {m7aDone && !m7DistributedOnChain && !myScoreRevealed && hasValidScoreCommit && (
        <div className="space-y-2">
          <Button variant="primary" size="sm" onClick={() => setShowRevealForm(true)}>
            Reveal Score (M7b)
          </Button>
          {showRevealForm && (
            <div className="mt-2">
              <ScoreRevealForm
                taskID={task.taskID}
                scoreCommit={myRawScoreCommit}
                onSuccess={() => {
                  setShowRevealForm(false);
                }}
              />
            </div>
          )}
        </div>
      )}

      {m7aDone && !m7DistributedOnChain && !myScoreRevealed && !hasValidScoreCommit && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Score commit not available yet for this miner. Wait for backend sync before revealing.
        </p>
      )}

      {m7DistributedOnChain && (
        <p className="text-xs text-green-600 dark:text-green-400">
          Rewards have already been distributed on-chain for this task.
        </p>
      )}

      {(myScoreRevealed || myRewardDistributed) && (
        <div className="text-sm">
          <p className="text-gray-600 dark:text-gray-400">My Reward Share:</p>
          <p className="text-gray-900 dark:text-white font-medium">
            {myRewardDistributed
              ? `${myRewardAmountEth.toFixed(4)} ETH (distributed)`
              : 'Pending distribution'}
          </p>
        </div>
      )}
    </div>
  );
}
