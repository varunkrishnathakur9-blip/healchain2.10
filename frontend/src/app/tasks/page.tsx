/**
 * HealChain Frontend - Tasks List Page
 * List all tasks with filtering
 */

'use client';

import { useState } from 'react';
import { useTaskList } from '@/hooks/useTask';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import Link from 'next/link';
import { useAccount } from 'wagmi';
import { formatDate } from '@/lib/dateUtils';

export default function TasksPage() {
  const { address } = useAccount();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const { tasks, loading, refresh } = useTaskList({ status: statusFilter });

  const statusOptions = [
    { value: undefined, label: 'All' },
    { value: 'CREATED', label: 'Created' },
    { value: 'OPEN', label: 'Open' },
    { value: 'COMMIT_CLOSED', label: 'Commit Closed' },
    { value: 'REVEAL_OPEN', label: 'Reveal Open' },
    { value: 'REVEAL_CLOSED', label: 'Reveal Closed' },
    { value: 'AGGREGATING', label: 'Aggregating' },
    { value: 'VERIFIED', label: 'Verified' },
    { value: 'REWARDED', label: 'Rewarded' },
    { value: 'CANCELLED', label: 'Cancelled' },
  ];

  const filteredTasks = tasks || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Tasks</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Browse all federated learning tasks
          </p>
        </div>
        <Link href="/publish">
          <Button variant="primary">Publish Task</Button>
        </Link>
      </div>

      <Card>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
              Status Filter:
            </label>
            <select
              value={statusFilter || 'All'}
              onChange={(e) => setStatusFilter(e.target.value === 'All' ? undefined : e.target.value)}
              className="w-full sm:w-auto px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-[44px] touch-manipulation"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value || 'All'} value={opt.value || 'All'}>
                  {opt.label}
                </option>
              ))}
            </select>
            {address && (
              <>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  Publisher Filter:
                </label>
                <select
                  className="w-full sm:w-auto px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-[44px] touch-manipulation"
                >
                  <option value="all">All</option>
                  <option value="my">My Tasks</option>
                </select>
              </>
            )}
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
              Sort:
            </label>
            <select className="w-full sm:w-auto px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-[44px] touch-manipulation">
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="reward-high">Reward (High→Low)</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading tasks...</p>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-600 dark:text-gray-400">No tasks found</p>
            <Link href="/publish" className="mt-4 inline-block">
              <Button variant="primary">Publish Your First Task</Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTasks.map((task) => {
              const isMyTask = address && task.publisher?.toLowerCase() === address.toLowerCase();
              return (
                <Link
                  key={task.taskID}
                  href={`/tasks/${task.taskID}`}
                  className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium text-gray-900 dark:text-white">{task.taskID}</h3>
                        <TaskStatusBadge status={task.status} />
                        {isMyTask && <Badge variant="info">My Task</Badge>}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                        Publisher: <span className="font-mono">{task.publisher}</span>
                      </p>
                      {task.rewardAmount && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                          Reward: {task.rewardAmount} ETH
                        </p>
                      )}
                      {task.deadline && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Deadline: {formatDate(task.deadline)}
                        </p>
                      )}
                      {(task as any)._count && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Miners: {(task as any)._count.miners || 0}
                        </p>
                      )}
                      {task.escrowBalance && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Escrow Balance: {task.escrowBalance} ETH
                        </p>
                      )}
                    </div>
                    <div className="ml-4">
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </Card>

      <Card>
        <div className="flex items-center justify-center gap-2">
          <Button variant="ghost" size="sm" disabled>
            Previous
          </Button>
          <span className="text-sm text-gray-600 dark:text-gray-400">Page 1 of 1</span>
          <Button variant="ghost" size="sm" disabled>
            Next
          </Button>
        </div>
      </Card>
    </div>
  );
}

