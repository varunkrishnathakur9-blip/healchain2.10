/**
 * HealChain Frontend - Publish Page
 * M1: Publish a new FL task
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAccount } from 'wagmi';
import PublishTaskForm from '@/components/forms/PublishTaskForm';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Link from 'next/link';

export default function PublishPage() {
  const { isConnected } = useAccount();
  const router = useRouter();
  const [success, setSuccess] = useState(false);

  const handleSuccess = () => {
    setSuccess(true);
    setTimeout(() => {
      router.push('/tasks');
    }, 2000);
  };

  if (!isConnected) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Connect Your Wallet
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Please connect your wallet to publish a new task
            </p>
            <Link href="/">
              <Button variant="primary">Go to Dashboard</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  if (success) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900 mb-4">
              <svg
                className="w-8 h-8 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Task Published Successfully!
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Redirecting to tasks page...
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Publish Task</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Create a new federated learning task and deposit rewards into escrow
        </p>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Protocol Information</h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>Module:</strong> M1 - Task Publishing</p>
          <p><strong>Steps:</strong></p>
          <ol className="list-decimal list-inside ml-4 space-y-1">
            <li>Fill task details</li>
            <li>Generate commit hash (accuracy + nonce)</li>
            <li>Create task in backend</li>
            <li>Submit transaction to escrow (smart contract)</li>
          </ol>
          <p className="mt-2"><strong>Note:</strong> Miners can register after escrow is locked</p>
        </div>
      </Card>

      <PublishTaskForm onSuccess={handleSuccess} />
    </div>
  );
}

