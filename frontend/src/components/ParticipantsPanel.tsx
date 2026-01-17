'use client';

import Card from './Card';
import { type Task } from '@/lib/api';

interface ParticipantsPanelProps {
  task: Task;
}

export default function ParticipantsPanel({ task }: ParticipantsPanelProps) {
  const miners = (task as any).miners || [];
  const aggregator = (task as any).aggregator || null;
  const scoreReveals = 0;
  const hasEnoughMiners = miners.length >= 3;

  return (
    <Card>
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Participants</h2>
      <div className="space-y-3">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Registered Miners: {miners.length}</p>
          <div className="mt-2 space-y-1">
            {miners.map((miner: any, index: number) => {
              const isAggregator = aggregator && (miner.address || miner).toLowerCase() === aggregator.toLowerCase();
              return (
                <p key={index} className="text-sm text-gray-900 dark:text-white font-mono">
                  └─ {miner.address || miner} {isAggregator && <span className="text-blue-600 dark:text-blue-400">(Aggregator)</span>}
                </p>
              );
            })}
          </div>
        </div>
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            Aggregator: {aggregator ? (
              <span className="text-gray-900 dark:text-white font-mono">{aggregator}</span>
            ) : hasEnoughMiners ? (
              <span className="text-yellow-600 dark:text-yellow-400">Will be selected automatically via Proof of Stake (PoS)</span>
            ) : (
              <span>Not selected yet (need at least 3 miners)</span>
            )}
          </p>
        </div>
        {(task.status === 'REVEAL_OPEN' || task.status === 'REVEAL_CLOSED' || task.status === 'VERIFIED') && (
          <div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Score Reveals: {scoreReveals}/{miners.length} (if M7 active)</p>
          </div>
        )}
      </div>
    </Card>
  );
}

