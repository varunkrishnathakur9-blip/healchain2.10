/**
 * HealChain Frontend - useAggregator Hook
 * Hook for triggering and monitoring aggregator operations
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { aggregatorAPI } from '@/lib/api';
import { useWallet } from './useWallet';

export interface AggregatorStatus {
  taskID: string;
  status: 'IDLE' | 'WAITING_SUBMISSIONS' | 'AGGREGATING' | 'VERIFYING' | 'PUBLISHING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  submissionCount?: number;
  requiredSubmissions?: number;
  error?: string;
  completedAt?: string;
}

export interface KeyStatus {
  taskID: string;
  keyDerived: boolean;
  aggregatorSelected: boolean;
  aggregatorAddress?: string;
  publisher?: string;
  minerCount?: number;
  minersWithPublicKeys?: number;
  canDerive?: boolean;
  derivationMetadata?: {
    publisher: string;
    minerPublicKeys: string[];
    nonceTP: string;
    aggregatorAddress: string;
  };
  keyDelivered?: boolean;
  keyDeliveredAt?: string;
  derivationMethod?: string;
  message?: string;
  requiredMiners?: number;
}

export interface Submission {
  taskID: string;
  minerAddress: string;
  miner_pk: string;
  publicKey: string | null;
  scoreCommit: string;
  encryptedHash: string;
  ciphertext: string[] | null; // Array of EC points ["x_hex,y_hex", ...]
  signature: string | null;
  status: string;
  submittedAt: string;
}

export function useAggregator(taskID: string | null) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [status, setStatus] = useState<AggregatorStatus | null>(null);
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loadingKeyStatus, setLoadingKeyStatus] = useState(false);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const { address, signMessage, createAuthMessage, isConnected } = useWallet();

  // Fetch aggregator status (defined first to avoid initialization order issues)
  const fetchStatus = useCallback(async () => {
    if (!taskID) {
      return;
    }

    try {
      const aggregatorStatus = await aggregatorAPI.getAggregatorStatus(taskID);
      setStatus(aggregatorStatus);
    } catch (err) {
      console.error('Failed to fetch aggregator status:', err);
      // Don't set error, just log it
    }
  }, [taskID]);

  // Start aggregation for a task
  const startAggregation = useCallback(
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

        // Trigger aggregation
        const result = await aggregatorAPI.startAggregation(taskID, address, message, signature);
        
        if (result.success) {
          // Refresh status
          await fetchStatus();
        } else {
          throw new Error(result.message || 'Failed to start aggregation');
        }
      } catch (err: any) {
        // Check if user rejected/cancelled the signature request
        if (err?.message?.includes('rejected') || err?.message?.includes('denied') || err?.message?.includes('User rejected')) {
          // User cancelled - don't set error, just silently fail
          return;
        }
        // Extract error message from backend response
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
        
        // Preserve error details for debugging
        const error = new Error(errorMessage);
        (error as any).originalError = err;
        (error as any).responseData = responseData;
        (error as any).status = err?.response?.status;
        
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [address, isConnected, taskID, signMessage, createAuthMessage, fetchStatus]
  );

  // Fetch key derivation status (Algorithm 2)
  const fetchKeyStatus = useCallback(async () => {
    if (!taskID || !isConnected || !address) {
      return;
    }

    // Prevent multiple simultaneous calls
    if (loadingKeyStatus) {
      return;
    }

    setLoadingKeyStatus(true);
    setError(null); // Clear previous errors
    try {
      // Create authentication message for wallet auth
      const message = createAuthMessage(address);
      const signature = await signMessage(message);
      
      const keyStatusData = await aggregatorAPI.getKeyStatus(taskID, address, message, signature);
      setKeyStatus(keyStatusData);
      setError(null); // Clear error on success
    } catch (err: any) {
      // Check if user rejected/cancelled the signature request
      if (err?.message?.includes('rejected') || err?.message?.includes('denied') || err?.message?.includes('User rejected')) {
        // User cancelled - don't set error, just silently fail
        setKeyStatus(null);
        return;
      }
      
      // Check if it's an authorization error (403) - this is expected for non-aggregators
      if (err?.response?.status === 403 || err?.responseData?.statusCode === 403) {
        // Set error state but don't log as error (this is expected behavior)
        setError(new Error('Unauthorized: Only the selected aggregator can view key derivation metadata'));
        setKeyStatus(null); // Clear key status on unauthorized access
      } else {
        // Only log unexpected errors
        console.error('Failed to fetch key status:', err);
        setError(err instanceof Error ? err : new Error('Failed to fetch key status'));
      }
    } finally {
      setLoadingKeyStatus(false);
    }
  }, [taskID, isConnected, address, signMessage, createAuthMessage, loadingKeyStatus]);

  // Fetch submissions (Algorithm 3)
  const fetchSubmissions = useCallback(async () => {
    if (!taskID || !isConnected || !address) {
      return;
    }

    // Prevent multiple simultaneous calls
    if (loadingSubmissions) {
      return;
    }

    setLoadingSubmissions(true);
    setError(null); // Clear previous errors
    try {
      // Create authentication message for wallet auth
      const message = createAuthMessage(address);
      const signature = await signMessage(message);
      
      const submissionsData = await aggregatorAPI.getSubmissions(taskID, address, message, signature);
      setSubmissions(submissionsData || []);
      setError(null); // Clear error on success
    } catch (err: any) {
      // Check if user rejected/cancelled the signature request
      if (err?.message?.includes('rejected') || err?.message?.includes('denied') || err?.message?.includes('User rejected')) {
        // User cancelled - don't set error, just silently fail
        setSubmissions([]);
        return;
      }
      
      // Check if it's an authorization error (403) - this is expected for non-aggregators
      if (err?.response?.status === 403 || err?.responseData?.statusCode === 403) {
        // Set error state but don't log as error (this is expected behavior)
        setError(new Error('Unauthorized: Only the selected aggregator can view submissions'));
        setSubmissions([]);
      } else {
        // Only log unexpected errors
        console.error('Failed to fetch submissions:', err);
        setError(err instanceof Error ? err : new Error('Failed to fetch submissions'));
        setSubmissions([]);
      }
    } finally {
      setLoadingSubmissions(false);
    }
  }, [taskID, isConnected, address, signMessage, createAuthMessage, loadingSubmissions]);

  // Use refs to store latest function versions to avoid stale closures without causing infinite loops
  const fetchStatusRef = useRef(fetchStatus);
  const fetchKeyStatusRef = useRef(fetchKeyStatus);
  const fetchSubmissionsRef = useRef(fetchSubmissions);

  // Update refs when functions change
  useEffect(() => {
    fetchStatusRef.current = fetchStatus;
    fetchKeyStatusRef.current = fetchKeyStatus;
    fetchSubmissionsRef.current = fetchSubmissions;
  }, [fetchStatus, fetchKeyStatus, fetchSubmissions]);

  // Auto-refresh status every 5 seconds if aggregation is in progress
  useEffect(() => {
    if (!taskID || !isConnected || !address) return;

    let isMounted = true;
    let intervalId: NodeJS.Timeout | null = null;

    // Initial fetch with delay to avoid immediate signature requests on connect
    const initialTimeout = setTimeout(() => {
      if (!isMounted) return;
      
      // Only fetch status initially (no signature required)
      // DO NOT automatically fetch key status or submissions - they require signatures
      // These should only be called when explicitly requested by the user
      fetchStatusRef.current();
    }, 100);

    // Set up polling if aggregation is in progress
    intervalId = setInterval(() => {
      if (!isMounted) return;
      if (status && ['WAITING_SUBMISSIONS', 'AGGREGATING', 'VERIFYING', 'PUBLISHING'].includes(status.status)) {
        // Only fetch status during polling (no signature required)
        // Submissions require signature, so don't poll automatically
        fetchStatusRef.current();
      }
    }, 5000); // Poll every 5 seconds

    return () => {
      isMounted = false;
      clearTimeout(initialTimeout);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [taskID, isConnected, address, status?.status]); // REMOVED callback functions from dependencies

  return {
    startAggregation,
    fetchStatus,
    fetchKeyStatus,
    fetchSubmissions,
    status,
    keyStatus,
    submissions,
    loading,
    loadingKeyStatus,
    loadingSubmissions,
    error,
  };
}

