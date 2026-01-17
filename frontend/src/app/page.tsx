'use client';

import { useTaskList } from '@/hooks/useTask';
import { useAccount } from 'wagmi';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import Link from 'next/link';
import ProtocolStatisticsPanel from '@/components/ProtocolStatisticsPanel';
import { formatDate } from '@/lib/dateUtils';

export default function Dashboard() {
  const { address, isConnected } = useAccount();
  const { tasks, loading, refresh } = useTaskList();

  const recentTasks = tasks?.slice(0, 5) || [];

  const isPublisher = isConnected && address;
  const isMiner = isConnected && address;
  const isObserver = !isConnected;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <div className="mt-2 flex items-center gap-2">
            {isPublisher && <Badge variant="info">Publisher</Badge>}
            {isMiner && <Badge variant="info">Miner</Badge>}
            {isObserver && <Badge variant="neutral">Observer</Badge>}
          </div>
        </div>
      </div>

      <ProtocolStatisticsPanel tasks={tasks || []} loading={loading} />

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Recent Tasks</h2>
          <Link href="/tasks">
            <Button variant="outline" size="sm">
              View All Tasks
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading tasks...</p>
          </div>
        ) : recentTasks.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-600 dark:text-gray-400">No tasks found</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTasks.map((task) => (
              <Link
                key={task.taskID}
                href={`/tasks/${task.taskID}`}
                className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium text-gray-900 dark:text-white">{task.taskID}</h3>
                      <TaskStatusBadge status={task.status} />
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Publisher: <span className="font-mono">{task.publisher}</span>
                    </p>
                    {task.rewardAmount && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Reward: {task.rewardAmount} ETH
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    {task.deadline && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Deadline: {formatDate(task.deadline)}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {isPublisher && (
          <Card hover>
            <Link href="/publish" className="block">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Publish New Task
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Create a new federated learning task
              </p>
            </Link>
          </Card>
        )}

        {isMiner && (
          <Card hover>
            <Link href="/mining" className="block">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Browse Available Tasks
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Register as a miner and participate
              </p>
            </Link>
          </Card>
        )}

        {isObserver && (
          <Card hover>
            <Link href="/tasks" className="block">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                View All Tasks
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Browse all federated learning tasks
              </p>
            </Link>
          </Card>
        )}
      </div>
    </div>
  );
}
