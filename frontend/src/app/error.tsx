/**
 * HealChain Frontend - Error Page
 * Catches and suppresses WebSocket connection errors
 */

'use client';

import { useEffect } from 'react';
import Button from '@/components/Button';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Check if it's a connection/subscription error
    const errorMessage = error.message || error.toString();
    const isConnectionError =
      errorMessage.includes('Connection interrupted') ||
      errorMessage.includes('subscribe') ||
      errorMessage.includes('WebSocket') ||
      errorMessage.includes('EventEmitter') ||
      errorMessage.includes('onClose');

    // If it's a connection error, automatically reset without showing error
    if (isConnectionError) {
      // Suppress silently and reset
      setTimeout(() => {
        reset();
      }, 100);
      return;
    }

    // Log other errors
    console.error('Application error:', error);
  }, [error, reset]);

  const errorMessage = error.message || error.toString();
  const isConnectionError =
    errorMessage.includes('Connection interrupted') ||
    errorMessage.includes('subscribe') ||
    errorMessage.includes('WebSocket') ||
    errorMessage.includes('EventEmitter');

  // Don't show error UI for connection errors
  if (isConnectionError) {
    return null; // Return null to suppress the error UI
  }

  // Show error UI for other errors
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Something went wrong
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">{error.message}</p>
        <div className="space-x-4">
          <Button variant="primary" onClick={reset}>
            Try again
          </Button>
          <Link href="/">
            <Button variant="outline">Go home</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

