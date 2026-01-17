/**
 * HealChain Frontend - useTask Hook
 * Hook for task management and status tracking
 */

'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { taskAPI, type Task } from '@/lib/api';
import { useContract } from './useContract';
import { useReadContract } from 'wagmi';
import { ESCROW_ABI } from '@/lib/contracts';
import { getChainConfig } from '@/lib/web3';
import { useAccount } from 'wagmi';

export function useTask(taskID?: string) {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;

  // Fetch task from backend
  const fetchTask = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await taskAPI.getById(id);
      setTask(data);
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch task');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch task from blockchain
  const fetchTaskFromChain = useCallback(async (id: string) => {
    if (!chainConfig) return null;
    try {
      // This would use useReadContract hook, but we need to handle it differently
      // For now, return null and let the component handle it
      return null;
    } catch (err) {
      console.error('Failed to fetch task from chain:', err);
      return null;
    }
  }, [chainConfig]);

  // Fetch all tasks
  const fetchAllTasks = useCallback(async (filters?: {
    status?: string;
    publisher?: string;
    limit?: number;
    offset?: number;
  }) => {
    setLoading(true);
    setError(null);
    try {
      const tasks = await taskAPI.getAll(filters);
      return tasks;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch tasks');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch open tasks
  const fetchOpenTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tasks = await taskAPI.getOpen();
      return tasks;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch open tasks');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-fetch if taskID provided
  useEffect(() => {
    if (taskID) {
      fetchTask(taskID);
    }
  }, [taskID, fetchTask]);

  // Poll task status (for real-time updates)
  const startPolling = useCallback(
    (id: string, interval: number = 5000) => {
      const poll = async () => {
        try {
          await fetchTask(id);
        } catch (err) {
          console.error('Polling error:', err);
        }
      };

      poll(); // Initial fetch
      const intervalId = setInterval(poll, interval);

      return () => clearInterval(intervalId);
    },
    [fetchTask]
  );

  return {
    task,
    loading,
    error,
    fetchTask,
    fetchAllTasks,
    fetchOpenTasks,
    fetchTaskFromChain,
    startPolling,
    refresh: taskID ? () => fetchTask(taskID) : undefined,
  };
}

// Hook for task list
export function useTaskList(filters?: {
  status?: string;
  publisher?: string;
  limit?: number;
  offset?: number;
}) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Memoize filters to prevent infinite loops
  const memoizedFilters = useMemo(() => filters, [
    filters?.status,
    filters?.publisher,
    filters?.limit,
    filters?.offset,
  ]);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await taskAPI.getAll(memoizedFilters);
      setTasks(data);
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch tasks');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [memoizedFilters]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  return {
    tasks,
    loading,
    error,
    refresh: fetchTasks,
  };
}

