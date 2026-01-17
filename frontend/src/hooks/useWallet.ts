/**
 * HealChain Frontend - useWallet Hook
 * Hook for wallet connection and account management
 */

'use client';

import { useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi';
import { injected } from 'wagmi/connectors';
import { useCallback } from 'react';
import { parseError, ERROR_CODES } from '@/lib/errors';

export function useWallet() {
  const { address, isConnected, chainId } = useAccount();
  const { connect, connectors, isPending: isConnecting } = useConnect();
  const { disconnect } = useDisconnect();
  const { signMessageAsync, isPending: isSigning } = useSignMessage();

  // Connect wallet
  const connectWallet = async () => {
    try {
      const injectedConnector = connectors.find((c) => c.id === 'injected' || c.id === 'metaMask');
      if (injectedConnector) {
        connect({ connector: injectedConnector });
      } else {
        connect({ connector: injected() });
      }
    } catch (error) {
      const parsed = parseError(error);
      throw new Error(parsed.message);
    }
  };

  // Sign message for backend authentication
  const signMessage = async (message: string): Promise<string> => {
    if (!isConnected) {
      throw new Error(parseError(new Error(ERROR_CODES.WALLET_NOT_CONNECTED)).message);
    }
    try {
      const signature = await signMessageAsync({ message });
      return signature;
    } catch (error) {
      const parsed = parseError(error);
      throw new Error(parsed.message);
    }
  };

  // Create authentication message (memoized to prevent recreation)
  const createAuthMessage = useCallback((address: string, timestamp: number = Date.now()): string => {
    return `HealChain Authentication\nAddress: ${address}\nTimestamp: ${timestamp}`;
  }, []);

  return {
    address,
    isConnected,
    chainId,
    connectWallet,
    disconnect,
    signMessage,
    createAuthMessage,
    isConnecting,
    isSigning,
  };
}

