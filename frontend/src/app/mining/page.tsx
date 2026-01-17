/**
 * HealChain Frontend - Mining Page
 * M2-M3: Miner dashboard for task participation
 */

'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAccount } from 'wagmi';
import { useTaskList } from '@/hooks/useTask';
import { useMiner } from '@/hooks/useMiner';
import { useTraining } from '@/hooks/useTraining';
import { useAggregator } from '@/hooks/useAggregator';
import { useStake } from '@/hooks/useStake';
import { minerAPI, taskAPI } from '@/lib/api';
import Card from '@/components/Card';
import Badge, { TaskStatusBadge } from '@/components/Badge';
import Button from '@/components/Button';
import MinerRegistrationForm from '@/components/forms/MinerRegistrationForm';
import StakeDepositForm from '@/components/forms/StakeDepositForm';
import Link from 'next/link';
import { formatDate } from '@/lib/dateUtils';

export default function MiningPage() {
  const { address, isConnected } = useAccount();
  const router = useRouter();
  const searchParams = useSearchParams();
  const action = searchParams?.get('action'); // For ?action=stake URL parameter
  const { tasks, loading, refresh } = useTaskList(); // Get ALL tasks, not just OPEN
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [showStakeForm, setShowStakeForm] = useState(action === 'stake');
  const [registeredTasks, setRegisteredTasks] = useState<Set<string>>(new Set());
  const [loadingRegistered, setLoadingRegistered] = useState(false);
  
  // Stake management
  const {
    minStake,
    availableStake,
    isEligible,
    isConfigured: isStakeConfigured,
    stakeInfo,
  } = useStake();

  // Filter open tasks for registration
  const openTasks = tasks?.filter(
    (t) => t.status === 'OPEN' || t.status === 'CREATED'
  ) || [];

  // Get all registered tasks (not just open ones)
  const allRegisteredTasks = tasks?.filter(
    (t) => registeredTasks.has(t.taskID)
  ) || [];

  // Fetch registered tasks on mount and when address changes
  useEffect(() => {
    const fetchRegisteredTasks = async () => {
      if (!address || !isConnected) {
        setRegisteredTasks(new Set());
        return;
      }

      setLoadingRegistered(true);
      try {
        const response = await minerAPI.getMyTasks(address);
        const taskIDs = response.registeredTaskIDs || [];
        console.log('Fetched registered tasks:', taskIDs); // Debug log
        setRegisteredTasks(new Set(taskIDs));
      } catch (err) {
        console.error('Failed to fetch registered tasks:', err);
        // Don't show error to user, just log it
      } finally {
        setLoadingRegistered(false);
      }
    };

    // Only fetch if we have an address
    if (address && isConnected) {
      fetchRegisteredTasks();
    }
  }, [address, isConnected]);

  const handleRegisterSuccess = async (taskID: string) => {
    // Update local state immediately
    setRegisteredTasks(new Set([...registeredTasks, taskID]));
    setSelectedTask(null);
    
    // Refresh tasks list
    refresh?.();
    
    // Also refresh registered tasks from backend to ensure consistency
    if (address) {
      try {
        const response = await minerAPI.getMyTasks(address);
        const taskIDs = response.registeredTaskIDs || [];
        setRegisteredTasks(new Set(taskIDs));
      } catch (err) {
        console.error('Failed to refresh registered tasks:', err);
      }
    }
  };

  if (!isConnected) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Connect Your Wallet
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Please connect your wallet to participate in mining tasks
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
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Mining Dashboard</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Wallet Address: {address}
        </p>
      </div>

      {/* Stake Status Card */}
      {isStakeConfigured && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              PoS Stake Status (Algorithm 2.1)
            </h2>
            <Button
              variant={isEligible ? 'outline' : 'primary'}
              size="sm"
              onClick={() => setShowStakeForm(!showStakeForm)}
            >
              {showStakeForm ? 'Hide' : isEligible ? 'Manage Stake' : 'Deposit Stake'}
            </Button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Available Stake</p>
              <p className="text-lg font-mono font-semibold text-gray-900 dark:text-white">
                {availableStake} ETH
              </p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Minimum Required</p>
              <p className="text-lg font-mono font-semibold text-gray-900 dark:text-white">
                {parseFloat(minStake).toFixed(4)} ETH
              </p>
            </div>
            <div className={`p-4 rounded-lg ${
              isEligible
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                : 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
            }`}>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Eligibility</p>
              <p className={`text-lg font-semibold ${
                isEligible
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-yellow-700 dark:text-yellow-400'
              }`}>
                {isEligible ? '✓ Eligible' : '⚠️ Not Eligible'}
              </p>
            </div>
          </div>

          {!isEligible && (
            <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-1 font-medium">
                ⚠️ Insufficient Stake for Aggregator Selection
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-300">
                You need at least {parseFloat(minStake).toFixed(4)} ETH staked to be eligible for 
                aggregator selection (Algorithm 2.1). You can still register as a miner and 
                participate in training, but won't be selected as aggregator.
              </p>
            </div>
          )}

          {stakeInfo && stakeInfo.pendingWithdrawal !== '0.0' && (
            <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-xs text-blue-700 dark:text-blue-300">
                ℹ️ You have {stakeInfo.pendingWithdrawal} ETH pending withdrawal. 
                Unlock time: {stakeInfo.unlockTime > 0 
                  ? new Date(stakeInfo.unlockTime * 1000).toLocaleString()
                  : 'N/A'}
              </p>
            </div>
          )}

          {/* Stake Deposit Form */}
          {showStakeForm && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <StakeDepositForm
                onSuccess={() => {
                  setShowStakeForm(false);
                }}
                onCancel={() => setShowStakeForm(false)}
              />
            </div>
          )}
        </Card>
      )}

      <Card>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          My Participations
        </h2>
        {loadingRegistered ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-blue-500 border-t-transparent"></div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading registrations...</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Tasks I'm Registered For: {allRegisteredTasks.length} / {registeredTasks.size} total
            </p>
            {allRegisteredTasks.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-500 italic py-2">
                No registered tasks found. Register for a task below to get started.
              </p>
            ) : (
              <div className="space-y-2">
                {allRegisteredTasks.map((task) => (
                  <div key={task.taskID} className="flex items-center justify-between p-2 border border-gray-200 dark:border-gray-700 rounded">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-900 dark:text-white font-medium">{task.taskID}</span>
                      <TaskStatusBadge status={task.status} />
                    </div>
                    <Link href={`/tasks/${task.taskID}`}>
                      <Button variant="outline" size="sm">View Details</Button>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-4 mb-2">
          Tasks I Can Register For: {openTasks.filter(t => !registeredTasks.has(t.taskID)).length}
        </p>
        <div className="space-y-2">
          {openTasks.filter(t => !registeredTasks.has(t.taskID)).map((task) => (
            <div key={task.taskID} className="flex items-center justify-between p-2 border border-gray-200 dark:border-gray-700 rounded">
              <span className="text-sm text-gray-900 dark:text-white">{task.taskID}</span>
              <Button variant="primary" size="sm" onClick={() => setSelectedTask(task.taskID)}>
                Register
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {selectedTask ? (
        <div className="max-w-2xl mx-auto">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Register for Task
              </h2>
              <Button variant="ghost" size="sm" onClick={() => setSelectedTask(null)}>
                Cancel
              </Button>
            </div>
            <MinerRegistrationForm taskID={selectedTask} onSuccess={() => handleRegisterSuccess(selectedTask)} />
          </Card>
        </div>
      ) : (
        <>
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Available Tasks
              </h2>
              <div className="flex gap-2">
                <select className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white min-h-[44px] touch-manipulation">
                  <option value="all">All</option>
                  <option value="open">Open for Registration</option>
                </select>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={async () => {
                    // Refresh both tasks and registered tasks
                    setLoadingRegistered(true);
                    try {
                      // Refresh tasks list
                      await refresh?.();
                      
                      // Refresh registered tasks
                      if (address) {
                        const response = await minerAPI.getMyTasks(address);
                        const taskIDs = response.registeredTaskIDs || [];
                        console.log('Refreshed registered tasks:', taskIDs); // Debug log
                        setRegisteredTasks(new Set(taskIDs));
                      }
                    } catch (err) {
                      console.error('Failed to refresh:', err);
                    } finally {
                      setLoadingRegistered(false);
                    }
                  }}
                  disabled={loading || loadingRegistered}
                >
                  {loading || loadingRegistered ? 'Refreshing...' : 'Refresh'}
                </Button>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading tasks...</p>
              </div>
            ) : openTasks.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-600 dark:text-gray-400">No open tasks available</p>
              </div>
            ) : (
              <div className="space-y-3">
                {openTasks.map((task) => {
                  const isRegistered = registeredTasks.has(task.taskID);
                  return (
                    <div
                      key={task.taskID}
                      className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Link
                              href={`/tasks/${task.taskID}`}
                              className="font-medium text-gray-900 dark:text-white hover:text-blue-600"
                            >
                              {task.taskID}
                            </Link>
                            <TaskStatusBadge status={task.status} />
                            {isRegistered && <Badge variant="success">Registered</Badge>}
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
                        </div>
                        <div className="ml-4">
                          {isRegistered ? (
                            <Link href={`/tasks/${task.taskID}`}>
                              <Button variant="outline" size="sm">
                                View Task
                              </Button>
                            </Link>
                          ) : (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => setSelectedTask(task.taskID)}
                            >
                              Register
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Training Status for Registered Tasks */}
          {allRegisteredTasks.length > 0 && (
            <Card>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Training Status (M3)
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Start FL client training for your registered tasks. Training runs locally on your machine.
              </p>
              <div className="space-y-3">
                {allRegisteredTasks
                  .filter(task => task.status === 'OPEN' || task.status === 'AGGREGATING')
                  .map((task) => {
                    const TrainingCard = () => {
                      const { startTraining, status, loading, error } = useTraining(task.taskID);
                      const [localError, setLocalError] = useState<string | null>(null);

                      const handleStartTraining = async () => {
                        setLocalError(null);
                        try {
                          await startTraining();
                          // Redirect to training page after successful start
                          router.push(`/training/${task.taskID}`);
                        } catch (err: any) {
                          setLocalError(err.message || 'Failed to start training');
                        }
                      };

                      return (
                        <div key={task.taskID} className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <span className="font-medium text-gray-900 dark:text-white">{task.taskID}</span>
                              <TaskStatusBadge status={task.status} />
                            </div>
                            {status?.status === 'COMPLETED' ? (
                              <Badge variant="success">Training Complete</Badge>
                            ) : status?.status === 'TRAINING' ? (
                              <Badge variant="info">Training...</Badge>
                            ) : status?.status === 'FAILED' ? (
                              <Badge variant="error">Failed</Badge>
                            ) : (
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={handleStartTraining}
                                disabled={loading}
                                isLoading={loading}
                              >
                                Start Training
                              </Button>
                            )}
                          </div>
                          {status && (
                            <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                              Status: <span className="font-medium">{status.status}</span>
                              {status.progress !== undefined && (
                                <span className="ml-2">({status.progress}%)</span>
                              )}
                            </div>
                          )}
                          {(error || localError) && (
                            <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                              {error?.message || localError}
                            </div>
                          )}
                          {/* Link to training page */}
                          <div className="mt-2">
                            <Link href={`/training/${task.taskID}`}>
                              <Button variant="ghost" size="sm">
                                View Training Dashboard →
                              </Button>
                            </Link>
                          </div>
                        </div>
                      );
                    };
                    return <TrainingCard key={task.taskID} />;
                  })}
                {allRegisteredTasks.filter(task => task.status === 'OPEN' || task.status === 'AGGREGATING').length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-500 italic">
                    No tasks available for training. Tasks must be in OPEN or AGGREGATING status.
                  </p>
                )}
              </div>
            </Card>
          )}

          {/* Aggregation Status (for Aggregator) */}
          {allRegisteredTasks.length > 0 && (
            <Card>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Aggregation Status (M4-M6)
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Start aggregator for tasks where you are the selected aggregator. Aggregation runs locally on your machine.
              </p>
              <div className="space-y-3">
                {allRegisteredTasks
                  .filter(task => task.status === 'OPEN' || task.status === 'AGGREGATING')
                  .map((task) => {
                    const AggregationCard = () => {
                      const [localError, setLocalError] = useState<string | null>(null);
                      const [isAggregator, setIsAggregator] = useState<boolean | null>(null);
                      const [taskDetails, setTaskDetails] = useState<any>(null);

                      // Check if current address is the aggregator FIRST (before using useAggregator)
                      useEffect(() => {
                        const checkAggregator = async () => {
                          try {
                            // Fetch task details to check aggregator using proper API client
                            const details = await taskAPI.getById(task.taskID);
                            setTaskDetails(details);
                            if (details && address) {
                              // Check if aggregator is selected (either in DB or computed as first miner)
                              let aggregatorAddress = details.aggregatorAddress;
                              if (!aggregatorAddress && details.miners && details.miners.length >= 3) {
                                // Use computed aggregator (first miner) if database field is not set
                                aggregatorAddress = details.miners[0]?.address;
                              }
                              setIsAggregator(
                                aggregatorAddress?.toLowerCase() === address.toLowerCase()
                              );
                            } else {
                              setIsAggregator(false);
                            }
                          } catch (err) {
                            // If task not found or error, assume not aggregator
                            console.error('Failed to check aggregator status:', err);
                            setIsAggregator(false);
                          }
                        };
                        if (address && task.taskID) checkAggregator();
                      }, [task.taskID, address]);

                      // Only use useAggregator hook if user is confirmed to be the aggregator
                      // This prevents unnecessary API calls and 403 errors
                      const { startAggregation, status, loading, error } = useAggregator(
                        isAggregator === true ? task.taskID : null
                      );

                      const handleStartAggregation = async () => {
                        setLocalError(null);
                        try {
                          await startAggregation();
                        } catch (err: any) {
                          // Extract detailed error message from backend response
                          let errorMessage = 'Failed to start aggregation';
                          
                          // Try multiple paths to extract error message
                          const responseData = err?.responseData || err?.response?.data;
                          
                          if (responseData?.error) {
                            errorMessage = responseData.error;
                          } else if (responseData?.message) {
                            errorMessage = responseData.message;
                          } else if (err?.message) {
                            errorMessage = err.message;
                          }
                          
                          // Log detailed error information for debugging
                          // Use console.error with separate arguments to avoid serialization issues
                          console.error('[Start Aggregation Error]');
                          console.error('Message:', errorMessage);
                          if (err?.response?.status) {
                            console.error('Status:', err.response.status);
                          }
                          if (responseData) {
                            console.error('Response Data:', {
                              error: responseData.error,
                              message: responseData.message,
                              success: responseData.success,
                            });
                          }
                          if (err?.config?.url) {
                            console.error('URL:', err.config.url);
                          }
                          
                          setLocalError(errorMessage);
                        }
                      };

                      if (isAggregator === false) {
                        return null; // Don't show if not aggregator
                      }

                      return (
                        <div key={task.taskID} className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <span className="font-medium text-gray-900 dark:text-white">{task.taskID}</span>
                              <TaskStatusBadge status={task.status} />
                              {isAggregator && <Badge variant="info" className="ml-2">You are Aggregator</Badge>}
                            </div>
                            {status?.status === 'COMPLETED' ? (
                              <Badge variant="success">Aggregation Complete</Badge>
                            ) : status?.status === 'AGGREGATING' || status?.status === 'VERIFYING' || status?.status === 'PUBLISHING' ? (
                              <Badge variant="info">In Progress...</Badge>
                            ) : (
                              isAggregator && (
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={handleStartAggregation}
                                  disabled={loading}
                                  isLoading={loading}
                                >
                                  Start Aggregation
                                </Button>
                              )
                            )}
                          </div>
                          {status && (
                            <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                              <div>Status: <span className="font-medium">{status.status}</span></div>
                              {status.submissionCount !== undefined && status.requiredSubmissions !== undefined && (
                                <div className="mt-1">
                                  Submissions: {status.submissionCount} / {status.requiredSubmissions}
                                </div>
                              )}
                              {status.progress !== undefined && (
                                <div className="mt-1">Progress: {status.progress}%</div>
                              )}
                            </div>
                          )}
                          {(error || localError) && (
                            <div className="mt-2 text-sm text-red-600 dark:text-red-400">
                              {error?.message || localError}
                            </div>
                          )}
                        </div>
                      );
                    };
                    return <AggregationCard key={task.taskID} />;
                  })}
                {allRegisteredTasks.filter(task => task.status === 'OPEN' || task.status === 'AGGREGATING').length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-500 italic">
                    No tasks available for aggregation. Tasks must be in OPEN or AGGREGATING status.
                  </p>
                )}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

