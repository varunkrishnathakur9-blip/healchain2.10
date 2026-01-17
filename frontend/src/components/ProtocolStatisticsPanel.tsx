'use client';

import { useEffect, useState } from 'react';
import { useAccount } from 'wagmi';
import { useReadContract } from 'wagmi';
import { taskAPI, type Task } from '@/lib/api';
import { ESCROW_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { formatEther } from 'viem';
import Metric from './Metric';
import Card from './Card';

interface ProtocolStatisticsPanelProps {
  tasks: Task[];
  loading?: boolean;
}

export default function ProtocolStatisticsPanel({ tasks, loading }: ProtocolStatisticsPanelProps) {
  const { address, chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;
  const [totalEscrow, setTotalEscrow] = useState<bigint>(0n);

  const activeTasks = tasks?.filter((t) => t.status === 'OPEN' || t.status === 'CREATED') || [];
  const completedTasks = tasks?.filter((t) => t.status === 'REWARDED' || t.status === 'COMPLETED') || [];
  const myTasks = address ? tasks?.filter((t) => t.publisher?.toLowerCase() === address.toLowerCase()) || [] : [];
  const myParticipations = address ? tasks?.filter((t) => {
    return (t as any).miners?.some((m: any) => m.address?.toLowerCase() === address.toLowerCase());
  }) || [] : [];

  useEffect(() => {
    if (!tasks || tasks.length === 0) {
      setTotalEscrow(0n);
      return;
    }

    let total = 0n;
    for (const task of tasks) {
      if (task.escrowBalance) {
        total += BigInt(task.escrowBalance);
      }
    }
    setTotalEscrow(total);
  }, [tasks]);

  if (loading) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Protocol Statistics</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Total Tasks" value={tasks?.length || 0} />
        <Metric label="Active Tasks" value={activeTasks.length} />
        <Metric label="Completed Tasks" value={completedTasks.length} />
        <Metric label="Total Escrow Locked" value={`${formatEther(totalEscrow)} ETH`} />
        {address && <Metric label="My Tasks" value={myTasks.length} />}
        {address && <Metric label="My Participations" value={myParticipations.length} />}
      </div>
    </Card>
  );
}

