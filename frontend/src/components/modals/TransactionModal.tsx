/**
 * HealChain Frontend - TransactionModal Component
 * Modal for displaying transaction status
 */

'use client';

import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { useAccount } from 'wagmi';
import { getChainConfig } from '@/lib/web3';

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: 'pending' | 'confirming' | 'success' | 'error';
  hash?: string;
  message?: string;
  onManualVerify?: () => void;
  isManuallyVerifying?: boolean;
}

export default function TransactionModal({
  isOpen,
  onClose,
  status,
  hash,
  message,
  onManualVerify,
  isManuallyVerifying = false,
}: TransactionModalProps) {
  const { chainId } = useAccount();
  const chainConfig = chainId ? getChainConfig(chainId) : null;

  // Get block explorer URL based on network
  const getBlockExplorerUrl = () => {
    if (!hash) return null;
    
    if (chainId === 11155111) {
      // Sepolia testnet
      return `https://sepolia.etherscan.io/tx/${hash}`;
    } else if (chainId === 1) {
      // Ethereum mainnet
      return `https://etherscan.io/tx/${hash}`;
    } else {
      // Localhost/Ganache - no public block explorer
      // Could use a local block explorer if available, but for now return null
      return null;
    }
  };

  const blockExplorerUrl = getBlockExplorerUrl();
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-12 w-12 text-green-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-12 w-12 text-red-500" />;
      default:
        return (
          <div className="h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
    }
  };

  const getStatusTitle = () => {
    switch (status) {
      case 'pending':
        return 'Transaction Pending';
      case 'confirming':
        return 'Confirming Transaction';
      case 'success':
        return 'Transaction Successful';
      case 'error':
        return 'Transaction Failed';
      default:
        return 'Transaction';
    }
  };

  const getStatusMessage = () => {
    if (message) return message;
    switch (status) {
      case 'pending':
        return 'Your transaction is being processed...';
      case 'confirming':
        return 'Waiting for blockchain confirmation...';
      case 'success':
        return 'Your transaction has been confirmed!';
      case 'error':
        return 'An error occurred. Please try again.';
      default:
        return '';
    }
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white dark:bg-gray-800 p-6 text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900 dark:text-white">
                    {getStatusTitle()}
                  </Dialog.Title>
                  <button
                    type="button"
                    className="text-gray-400 hover:text-gray-500"
                    onClick={onClose}
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="flex flex-col items-center justify-center py-6">
                  {getStatusIcon()}
                  <p className="mt-4 text-sm text-gray-600 dark:text-gray-400 text-center">
                    {getStatusMessage()}
                  </p>
                  {hash && (
                    <div className="mt-4 space-y-2">
                      {blockExplorerUrl ? (
                        <a
                          href={blockExplorerUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-800 underline block"
                        >
                          View on {chainId === 11155111 ? 'Sepolia Etherscan' : 'Etherscan'}
                        </a>
                      ) : (
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          <p className="font-mono break-all">{hash}</p>
                          <p className="mt-1 text-xs">
                            Local network transaction (Ganache/Hardhat)
                          </p>
                          <p className="text-xs mt-1">
                            Check your local node logs or Ganache UI to view transaction details
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {(status === 'success' || status === 'error' || status === 'confirming') && (
                  <div className="mt-4 space-y-2">
                    {status === 'confirming' && onManualVerify && (
                      <button
                        type="button"
                        className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={onManualVerify}
                        disabled={isManuallyVerifying}
                      >
                        {isManuallyVerifying ? 'Verifying...' : 'Verify Manually (If Confirmed in MetaMask)'}
                      </button>
                    )}
                    <button
                      type="button"
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      onClick={onClose}
                    >
                      {status === 'confirming' ? 'Close & Refresh' : 'Close'}
                    </button>
                    {status === 'confirming' && (
                      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
                        {onManualVerify 
                          ? 'If MetaMask shows the transaction as confirmed, click "Verify Manually" to proceed.'
                          : 'If MetaMask shows the transaction as confirmed, you can close this modal and refresh the page.'}
                      </p>
                    )}
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

