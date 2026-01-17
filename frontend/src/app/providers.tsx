/**
 * HealChain Frontend - Providers Component
 * Wraps app with wagmi and RainbowKit providers
 */

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider, getDefaultConfig } from '@rainbow-me/rainbowkit';
import { SUPPORTED_CHAINS } from '@/lib/web3';
import '@rainbow-me/rainbowkit/styles.css';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Create wagmi config
// Note: WalletConnect project ID is optional for local development
// If not provided, WalletConnect features will be limited but local wallet connections (MetaMask, etc.) will still work
const walletConnectProjectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;

if (!walletConnectProjectId && typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  console.info(
    'ℹ️  HealChain: WalletConnect project ID not configured.\n' +
    '   Local wallet connections (MetaMask, etc.) will work normally.\n' +
    '   To enable WalletConnect features, set NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID in .env.local\n' +
    '   Get your project ID from: https://cloud.walletconnect.com'
  );
}

const wagmiConfig = getDefaultConfig({
  appName: 'HealChain',
  // Use a valid placeholder that won't cause 403 errors
  // Always use the same value on server and client to avoid hydration mismatches
  projectId: walletConnectProjectId || '00000000000000000000000000000000',
  chains: SUPPORTED_CHAINS,
  ssr: true,
});

// Create query client with better error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Disable automatic refetching to reduce WebSocket subscriptions
      refetchOnMount: false,
      refetchOnReconnect: false,
      // Use polling instead of WebSocket subscriptions where possible
      refetchInterval: false,
      retry: (failureCount, error: any) => {
        // Don't retry on connection/subscription errors
        const errorMessage = error?.message || error?.toString() || '';
        if (
          errorMessage.includes('Connection interrupted') || 
          errorMessage.includes('subscribe') ||
          error?.code === 'ECONNREFUSED' ||
          errorMessage.includes('WebSocket') ||
          errorMessage.includes('EventEmitter')
        ) {
          return false;
        }
        // Retry other errors up to 2 times
        return failureCount < 2;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Suppress connection errors in console
      onError: (error: any) => {
        const errorMessage = error?.message || error?.toString() || '';
        // Only log non-connection errors
        if (
          !errorMessage.includes('Connection interrupted') &&
          !errorMessage.includes('subscribe') &&
          !errorMessage.includes('WebSocket') &&
          !errorMessage.includes('EventEmitter')
        ) {
          console.error('Query error:', error);
        }
      },
    },
    mutations: {
      retry: false, // Don't retry mutations
    },
  },
});

// Comprehensive error handler for unhandled promise rejections (WebSocket errors)
if (typeof window !== 'undefined') {
  // Suppress WebSocket/subscription errors and WalletConnect config errors in console
  const originalError = window.console.error;
  window.console.error = (...args: any[]) => {
    // Serialize error objects to avoid circular reference issues
    const serializedArgs = args.map(arg => {
      if (arg && typeof arg === 'object') {
        try {
          // Try to extract serializable properties
          if (arg instanceof Error) {
            const errorObj: any = {
              name: arg.name,
              message: arg.message,
              stack: arg.stack?.substring(0, 500), // Limit stack trace
            };
            // Preserve custom properties that might contain error details
            if ((arg as any).responseData) {
              errorObj.responseData = (arg as any).responseData;
            }
            if ((arg as any).response) {
              errorObj.response = {
                status: (arg as any).response?.status,
                data: (arg as any).response?.data,
              };
            }
            return errorObj;
          }
          // For plain objects, try JSON.stringify with a replacer to handle circular refs
          const seen = new WeakSet();
          return JSON.parse(JSON.stringify(arg, (key, value) => {
            if (typeof value === 'object' && value !== null) {
              if (seen.has(value)) {
                return '[Circular]';
              }
              seen.add(value);
            }
            // Convert BigInt to string
            if (typeof value === 'bigint') {
              return value.toString();
            }
            return value;
          }));
        } catch {
          // If serialization fails, try to extract at least the message
          if (arg instanceof Error) {
            return { message: arg.message, name: arg.name };
          }
          // For objects, try to get string representation
          return String(arg);
        }
      }
      return arg;
    });
    
    const errorString = serializedArgs.join(' ');
    if (
      errorString.includes('Connection interrupted') ||
      errorString.includes('subscribe') ||
      errorString.includes('WebSocket') ||
      errorString.includes('EventEmitter') ||
      errorString.includes('onClose') ||
      errorString.includes('Reown Config') ||
      errorString.includes('Failed to fetch remote project configuration') ||
      errorString.includes('HTTP status code: 403') ||
      errorString.includes('api.web3modal.org') ||
      errorString.includes('Contract verification issue') ||
      errorString.includes('returned no data') ||
      errorString.includes('not a contract') ||
      errorString.includes('does not have the function')
    ) {
      // Suppress these errors silently (they're non-critical or expected)
      return;
    }
    originalError.apply(console, serializedArgs);
  };

  // Suppress unhandled promise rejections (WebSocket errors)
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason;
    const errorMessage = error?.message || error?.toString() || '';
    
    // Suppress connection/subscription errors and WalletConnect config errors
    if (
      errorMessage.includes('Connection interrupted') ||
      errorMessage.includes('subscribe') ||
      errorMessage.includes('WebSocket') ||
      errorMessage.includes('EventEmitter') ||
      errorMessage.includes('onClose') ||
      errorMessage.includes('Reown Config') ||
      errorMessage.includes('Failed to fetch remote project configuration') ||
      errorMessage.includes('HTTP status code: 403') ||
      errorMessage.includes('api.web3modal.org') ||
      error?.code === 'ECONNREFUSED'
    ) {
      event.preventDefault(); // Prevent error from showing
      return;
    }
  }, true); // Use capture phase to catch early

  // Catch errors from React error boundaries and global errors
  window.addEventListener('error', (event) => {
    const errorMessage = event.message || event.error?.message || '';
    if (
      errorMessage.includes('Connection interrupted') ||
      errorMessage.includes('subscribe') ||
      errorMessage.includes('WebSocket') ||
      errorMessage.includes('EventEmitter') ||
      errorMessage.includes('onClose')
    ) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true); // Use capture phase
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <WagmiProvider config={wagmiConfig}>
        <QueryClientProvider client={queryClient}>
          <RainbowKitProvider>{children}</RainbowKitProvider>
        </QueryClientProvider>
      </WagmiProvider>
    </ErrorBoundary>
  );
}

