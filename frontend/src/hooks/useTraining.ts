/**
 * HealChain Frontend - useTraining Hook
 * Hook for triggering and monitoring FL client training
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { minerAPI } from '@/lib/api';
import { useWallet } from './useWallet';

export interface TrainingStatus {
  taskID: string;
  minerAddress: string;
  status: 'IDLE' | 'TRAINING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  message?: string;
  error?: string;
  submittedAt?: string;
  submitted?: boolean;
  submissionStatus?: string;
  submissionError?: string;
}

export function useTraining(taskID: string | null) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const { address, signMessage, createAuthMessage, isConnected } = useWallet();

  // Start training for a task
  const startTraining = useCallback(
    async () => {
      if (!isConnected || !address || !taskID) {
        throw new Error('Wallet not connected or task ID missing');
      }

      setLoading(true);
      setError(null);

      try {
        // Create authentication message
        const message = createAuthMessage(address);
        const signature = await signMessage(message);

        // Trigger training (API expects: address, taskID, message, signature)
        try {
          const result = await minerAPI.startTraining(address, taskID, message, signature);

          // If we get here, the request succeeded (200 status)
          if (result.success) {
            // Refresh status
            await fetchStatus();
          } else {
            // Backend returned success: false with a message (shouldn't happen with 200, but handle it)
            const errorMessage = result.message || 'Failed to start training';
            const error = new Error(errorMessage);
            setError(error);
            throw error;
          }
        } catch (apiError: any) {
          // Handle API errors (400, 500, etc.)
          // The axios interceptor converts errors to Error objects with the message
          // But we also need to check the original response data for success: false cases
          let errorMessage = 'Failed to start training';

          // Check if it's an axios error with response data
          // The interceptor preserves responseData on the error object
          if (apiError?.responseData) {
            const responseData = apiError.responseData;
            // Backend returns { success: false, message: "..." } for 400 errors
            if (responseData.success === false && responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.error) {
              errorMessage = responseData.error;
            }
          } else if (apiError?.response?.data) {
            // Fallback: check response.data directly
            const responseData = apiError.response.data;
            if (responseData.success === false && responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.error) {
              errorMessage = responseData.error;
            }
          } else if (apiError?.message) {
            // Error object message (from axios interceptor)
            errorMessage = apiError.message;
          }

          const error = new Error(errorMessage);
          setError(error);
          throw error;
        }
      } catch (err: any) {
        // Final catch for any other errors (wallet errors, etc.)
        const errorMessage = err?.message || 'Failed to start training';
        const error = new Error(errorMessage);
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [address, isConnected, taskID, signMessage, createAuthMessage]
  );

  // Fetch training status
  const fetchStatus = useCallback(async () => {
    if (!address || !taskID) {
      return;
    }

    try {
      const trainingStatus = await minerAPI.getTrainingStatus(address, taskID);
      setStatus(trainingStatus);
    } catch (err) {
      console.error('Failed to fetch training status:', err);
      // Don't set error, just log it
    }
  }, [address, taskID]);

  // Auto-refresh status every 5 seconds if training is in progress
  useEffect(() => {
    if (!taskID || !address) return;

    // Initial fetch
    fetchStatus();

    // Set up polling if training is in progress
    const interval = setInterval(() => {
      if (status?.status === 'TRAINING') {
        fetchStatus();
      }
    }, 10000); // Poll every 10 seconds (increased from 5s to prevent backend overload)

    return () => clearInterval(interval);
  }, [taskID, address, status?.status, fetchStatus]);

  // Submit gradient to aggregator (M3)
  const submitGradient = useCallback(
    async () => {
      if (!isConnected || !address || !taskID) {
        throw new Error('Wallet not connected or task ID missing');
      }

      setLoading(true);
      setError(null);

      try {
        // Create authentication message
        const message = createAuthMessage(address);
        const signature = await signMessage(message);

        // Submit gradient (API expects: address, taskID, message, signature)
        try {
          const result = await minerAPI.submitGradient(address, taskID, message, signature);

          if (result.success) {
            // Refresh status to get updated submission info
            await fetchStatus();
          } else {
            const errorMessage = result.message || 'Failed to submit gradient';
            const error = new Error(errorMessage);
            setError(error);
            throw error;
          }
        } catch (apiError: any) {
          let errorMessage = 'Failed to submit gradient';

          if (apiError?.responseData) {
            const responseData = apiError.responseData;
            if (responseData.success === false && responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.error) {
              errorMessage = responseData.error;
            }
          } else if (apiError?.response?.data) {
            const responseData = apiError.response.data;
            if (responseData.success === false && responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.message) {
              errorMessage = responseData.message;
            } else if (responseData.error) {
              errorMessage = responseData.error;
            }
          } else if (apiError?.message) {
            errorMessage = apiError.message;
          }

          const error = new Error(errorMessage);
          setError(error);
          throw error;
        }
      } catch (err: any) {
        const errorMessage = err?.message || 'Failed to submit gradient';
        const error = new Error(errorMessage);
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [address, isConnected, taskID, signMessage, createAuthMessage, fetchStatus]
  );

  return {
    startTraining,
    submitGradient,
    fetchStatus,
    status,
    loading,
    error,
  };
}

