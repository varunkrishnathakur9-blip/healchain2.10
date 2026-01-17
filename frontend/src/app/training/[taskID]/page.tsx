/**
 * HealChain Frontend - Training Page
 * M3: Dedicated page for miner training with real-time status
 * Only accessible by registered miners for the specific task
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAccount } from 'wagmi';
import { useTask } from '@/hooks/useTask';
import { useTraining, type TrainingStatus } from '@/hooks/useTraining';
import { minerAPI } from '@/lib/api';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import Link from 'next/link';
import { formatDateLong } from '@/lib/dateUtils';

export default function TrainingPage() {
  const params = useParams();
  const router = useRouter();
  const taskID = params.taskID as string;
  const { address, isConnected } = useAccount();
  
  const { task, loading: taskLoading, error: taskError } = useTask(taskID);
  const { startTraining, submitGradient, status, loading: trainingLoading, error: trainingError, fetchStatus } = useTraining(taskID);
  
  // Authorization state
  const [isRegistered, setIsRegistered] = useState<boolean | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  
  // Local error state
  const [localError, setLocalError] = useState<string | null>(null);
  const [startSuccess, setStartSuccess] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Check if miner is registered for this task
  useEffect(() => {
    const checkRegistration = async () => {
      if (!address || !isConnected || !taskID) {
        setIsRegistered(false);
        setIsCheckingAuth(false);
        return;
      }

      setIsCheckingAuth(true);
      setAuthError(null);

      try {
        const response = await minerAPI.getMyTasks(address);
        const registeredTaskIDs = response.registeredTaskIDs || [];
        const registered = registeredTaskIDs.includes(taskID);
        setIsRegistered(registered);
        
        if (!registered) {
          setAuthError(`You are not registered as a miner for task ${taskID}. Please register first.`);
        }
      } catch (err: any) {
        console.error('Failed to check registration:', err);
        setIsRegistered(false);
        setAuthError('Failed to verify miner registration. Please try again.');
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkRegistration();
  }, [address, isConnected, taskID]);

  // Auto-refresh status when training is active
  useEffect(() => {
    if (!taskID || !address || !isRegistered) return;

    // Initial fetch
    fetchStatus();

    // Set up polling if training is in progress
    const interval = setInterval(() => {
      if (status?.status === 'TRAINING') {
        fetchStatus();
      }
    }, 3000); // Poll every 3 seconds for real-time updates

    return () => clearInterval(interval);
  }, [taskID, address, isRegistered, status?.status, fetchStatus]);

  const handleStartTraining = async () => {
    setLocalError(null);
    setStartSuccess(false);
    
    try {
      await startTraining();
      setStartSuccess(true);
      // Status will be updated via polling
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to start training';
      setLocalError(errorMessage);
    }
  };

  const handleSubmitGradient = async () => {
    setLocalError(null);
    setSubmitSuccess(false);
    setSubmitting(true);
    
    try {
      await submitGradient();
      setSubmitSuccess(true);
      // Refresh status to get updated submission info
      await fetchStatus();
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to submit gradient';
      setLocalError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (!isConnected) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Wallet Not Connected
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Please connect your wallet to access the training page.
            </p>
            <Link href="/mining">
              <Button variant="primary">Go to Mining Dashboard</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // Authorization check loading
  if (isCheckingAuth || taskLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              {isCheckingAuth ? 'Verifying authorization...' : 'Loading task details...'}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  // Authorization error
  if (isRegistered === false || authError) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900 mb-4">
              <svg
                className="w-8 h-8 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Access Denied
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {authError || `You are not registered as a miner for task ${taskID}.`}
            </p>
            <div className="flex gap-3 justify-center">
              <Link href="/mining">
                <Button variant="primary">Go to Mining Dashboard</Button>
              </Link>
              {taskID && (
                <Link href={`/tasks/${taskID}`}>
                  <Button variant="outline">View Task Details</Button>
                </Link>
              )}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Task error
  if (taskError && !task) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Task Not Found
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {taskError.message || `Task ${taskID} could not be loaded.`}
            </p>
            <Link href="/mining">
              <Button variant="primary">Go to Mining Dashboard</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // Main training interface
  const getStatusBadge = (status: TrainingStatus['status']) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success">Training Complete</Badge>;
      case 'TRAINING':
        return <Badge variant="info">Training in Progress</Badge>;
      case 'FAILED':
        return <Badge variant="error">Training Failed</Badge>;
      default:
        return <Badge variant="outline">Idle</Badge>;
    }
  };

  const canStartTraining = !status || status.status === 'IDLE' || status.status === 'FAILED';
  const isTraining = status?.status === 'TRAINING';
  const isCompleted = status?.status === 'COMPLETED';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Training Dashboard
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Task: <span className="font-mono font-medium">{taskID}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/mining">
            <Button variant="outline" size="sm">Back to Mining</Button>
          </Link>
          {taskID && (
            <Link href={`/tasks/${taskID}`}>
              <Button variant="outline" size="sm">View Task</Button>
            </Link>
          )}
        </div>
      </div>

      {/* Success Messages */}
      {startSuccess && !localError && (
        <Card>
          <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Training started successfully! Status will update automatically.
              </p>
            </div>
          </div>
        </Card>
      )}

      {submitSuccess && !localError && (
        <Card>
          <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Gradient submitted to aggregator successfully! (Algorithm 3 - M3)
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Task Information */}
      {task && (
        <Card>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Task Information
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Task ID</span>
              <span className="text-sm font-mono text-gray-900 dark:text-white">{task.taskID}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
              <TaskStatusBadge status={task.status} />
            </div>
            {task.publisher && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Publisher</span>
                <span className="text-sm font-mono text-gray-900 dark:text-white">{task.publisher}</span>
              </div>
            )}
            {task.rewardAmount && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Reward</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{task.rewardAmount} ETH</span>
              </div>
            )}
            {task.deadline && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Deadline</span>
                <span className="text-sm text-gray-900 dark:text-white">{formatDateLong(task.deadline)}</span>
              </div>
            )}
            {task.dataset && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Dataset</span>
                <span className="text-sm text-gray-900 dark:text-white">{task.dataset}</span>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Training Status */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Training Status (M3)
          </h2>
          {status && getStatusBadge(status.status)}
        </div>

        <div className="space-y-4">
          {/* Training Status Details */}
          {status ? (
            <div className="space-y-3">
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Training Status</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {status.status}
                    </p>
                  </div>
                  {status.progress !== undefined && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Progress</p>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {status.progress}%
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Submission Status</p>
                    {status.submitted ? (
                      <Badge variant="success">Submitted</Badge>
                    ) : status.submissionStatus === 'FAILED' ? (
                      <Badge variant="error">Submission Failed</Badge>
                    ) : (
                      <Badge variant="outline">Not Submitted</Badge>
                    )}
                  </div>
                  {(status.submittedAt || status.submitted) && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Submitted At</p>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {status.submittedAt ? formatDateLong(status.submittedAt) : 'Pending...'}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {status.progress !== undefined && (
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${status.progress}%` }}
                  ></div>
                </div>
              )}

              {/* Submission Error Message */}
              {status.submissionError && !status.submitted && (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    <span className="font-medium">Submission Error:</span> {status.submissionError}
                  </p>
                  <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                    You can manually submit using the button below.
                  </p>
                </div>
              )}

              {/* Training Error Message */}
              {status.error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-800 dark:text-red-200">
                    <span className="font-medium">Error:</span> {status.error}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-sm text-gray-500 dark:text-gray-500">
                No training status available. Start training to begin.
              </p>
            </div>
          )}

          {/* Training Controls */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700 flex-wrap">
            {canStartTraining && (
              <Button
                variant="primary"
                onClick={handleStartTraining}
                disabled={trainingLoading}
                isLoading={trainingLoading}
              >
                {status?.status === 'FAILED' ? 'Retry Training' : 'Start Training'}
              </Button>
            )}
            
            {isTraining && (
              <Button
                variant="outline"
                onClick={() => fetchStatus()}
                disabled={trainingLoading}
              >
                Refresh Status
              </Button>
            )}

            {/* Submit Gradient Button (M3) - Show when training completed but not submitted */}
            {isCompleted && !status?.submitted && (
              <Button
                variant="primary"
                onClick={handleSubmitGradient}
                disabled={submitting || trainingLoading}
                isLoading={submitting}
              >
                Submit Gradient to Aggregator (M3)
              </Button>
            )}

            {/* Resubmit if submission failed */}
            {isCompleted && status?.submissionStatus === 'FAILED' && (
              <Button
                variant="primary"
                onClick={handleSubmitGradient}
                disabled={submitting || trainingLoading}
                isLoading={submitting}
              >
                Retry Submission
              </Button>
            )}

            {isCompleted && status?.submitted && (
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Gradient submitted to aggregator!</span>
              </div>
            )}
          </div>

          {/* Error Display */}
          {(trainingError || localError) && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">
                <span className="font-medium">Error:</span> {localError || trainingError?.message || 'An unknown error occurred'}
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Training Information */}
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Training Information
        </h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p>
            • Training runs locally on your machine via the FL Client Service
          </p>
          <p>
            • The FL Client Service must be running for training to work
          </p>
          <p>
            • Training status updates automatically every 3 seconds
          </p>
          <p>
            • You can refresh the status manually at any time
          </p>
          <p>
            • After training completes, gradient is automatically submitted to aggregator (Algorithm 3 - M3)
          </p>
          <p>
            • If automatic submission fails, use the "Submit Gradient" button to retry
          </p>
          {status?.status === 'TRAINING' && (
            <p className="pt-2 text-blue-600 dark:text-blue-400 font-medium">
              ⚠️ Keep this page open while training is in progress
            </p>
          )}
        </div>
      </Card>

      {/* Miner Information */}
      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Miner Information
        </h2>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Wallet Address</span>
            <span className="text-sm font-mono text-gray-900 dark:text-white">{address}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Registration Status</span>
            <Badge variant="success">Registered</Badge>
          </div>
        </div>
      </Card>
    </div>
  );
}
