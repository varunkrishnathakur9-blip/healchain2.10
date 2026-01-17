/**
 * HealChain Frontend - Error Boundary Component
 * Catches and suppresses WebSocket connection errors
 */

'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    // Check if it's a connection/subscription error
    const errorMessage = error.message || error.toString();
    const isConnectionError =
      errorMessage.includes('Connection interrupted') ||
      errorMessage.includes('subscribe') ||
      errorMessage.includes('WebSocket') ||
      errorMessage.includes('EventEmitter');

    // Only set error state for non-connection errors
    if (!isConnectionError) {
      return { hasError: true, error };
    }

    // Suppress connection errors
    return { hasError: false, error: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const errorMessage = error.message || error.toString();
    const isConnectionError =
      errorMessage.includes('Connection interrupted') ||
      errorMessage.includes('subscribe') ||
      errorMessage.includes('WebSocket') ||
      errorMessage.includes('EventEmitter') ||
      errorMessage.includes('onClose');

    // Only log non-connection errors
    if (!isConnectionError) {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    } else {
      // For connection errors, try to recover silently
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError && this.state.error) {
      // Only show error UI for non-connection errors
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
              Something went wrong
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {this.state.error.message}
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

