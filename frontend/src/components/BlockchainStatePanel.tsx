'use client';

import { useReadContract } from 'wagmi';
import { ESCROW_ABI, BLOCK_PUBLISHER_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { formatEther } from 'viem';
import Card from './Card';
import { useAccount } from 'wagmi';
import { type Task } from '@/lib/api';

interface BlockchainStatePanelProps {
  task: Task;
}

export default function BlockchainStatePanel({ task }: BlockchainStatePanelProps) {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;

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

  const taskStatus = contractTask ? ['CREATED', 'LOCKED', 'PUBLISHED', 'AWAITING_REVEAL', 'COMPLETED', 'FAILED'][(contractTask as any).status] : 'Unknown';
  const accuracyCommit = contractTask ? (contractTask as any).accuracyCommit : null;
  const modelHash = publishedBlock ? (publishedBlock as any).modelHash : '0x0000000000000000000000000000000000000000000000000000000000000000';
  const accuracy = publishedBlock ? (publishedBlock as any).accuracy : 0;
  const blockHash = publishedBlock ? (publishedBlock as any).timestamp > 0n ? '0x' + (publishedBlock as any).timestamp.toString(16) : '0x0000000000000000000000000000000000000000000000000000000000000000' : '0x0000000000000000000000000000000000000000000000000000000000000000';

  return (
    <Card>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Blockchain State</h2>
      <dl className="space-y-3">
        <div>
          <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Escrow Balance</dt>
          <dd className="mt-1 text-sm text-gray-900 dark:text-white">
            {escrowBalance ? formatEther(escrowBalance) : '0'} ETH (from contract)
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Task Status</dt>
          <dd className="mt-1 text-sm text-gray-900 dark:text-white">{taskStatus} (from contract)</dd>
        </div>
        {accuracyCommit && (
          <div>
            <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Accuracy Commit</dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono break-all">
              {accuracyCommit} (from contract)
            </dd>
          </div>
        )}
        {publishedBlock && (publishedBlock as any).timestamp > 0n && (
          <>
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Model Hash</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono break-all">
                {modelHash} (from contract, if M6 done)
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Accuracy</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {accuracy} (from contract, if M6 done)
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400">Block Hash</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono break-all">
                {blockHash} (from BlockPublisher, if M6 done)
              </dd>
            </div>
          </>
        )}
      </dl>
    </Card>
  );
}

