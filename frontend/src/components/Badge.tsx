/**
 * HealChain Frontend - Badge Component
 * Status badge component for task states
 */

'use client';

import { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
}: BadgeProps) {
  const variants = {
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    neutral: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  );
}

// Task status badge helper - matches backend TaskStatus enum
export function TaskStatusBadge({ status }: { status: string }) {
  const statusMap: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    // Backend TaskStatus enum values
    CREATED: { variant: 'info', label: 'Created' },
    OPEN: { variant: 'info', label: 'Open' },
    COMMIT_CLOSED: { variant: 'warning', label: 'Commit Closed' },
    REVEAL_OPEN: { variant: 'warning', label: 'Reveal Open' },
    REVEAL_CLOSED: { variant: 'warning', label: 'Reveal Closed' },
    AGGREGATING: { variant: 'info', label: 'Aggregating' },
    VERIFIED: { variant: 'success', label: 'Verified' },
    REWARDED: { variant: 'success', label: 'Rewarded' },
    CANCELLED: { variant: 'error', label: 'Cancelled' },
    // Legacy/alternative status names (for compatibility)
    ESCROW_LOCKED: { variant: 'info', label: 'Locked' },
    TRAINING: { variant: 'warning', label: 'Training' },
    AGGREGATED: { variant: 'info', label: 'Aggregated' },
    ONCHAIN_PUBLISHED: { variant: 'success', label: 'Published' },
    AWAITING_REVEAL: { variant: 'warning', label: 'Awaiting Reveal' },
    COMPLETED: { variant: 'success', label: 'Completed' },
    FAILED: { variant: 'error', label: 'Failed' },
  };

  const config = statusMap[status] || { variant: 'neutral' as const, label: status };

  return <Badge variant={config.variant}>{config.label}</Badge>;
}

