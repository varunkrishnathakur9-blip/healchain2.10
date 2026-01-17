/**
 * HealChain Frontend - Web3 Configuration
 * Network and chain configuration for wagmi
 * 
 * Production-ready: All contract addresses must be provided via environment variables.
 * No hardcoded placeholders - ensures proper configuration for each deployment.
 */

import { sepolia } from 'wagmi/chains';
import { defineChain } from 'viem';

// Custom localhost chain with configurable RPC URL
// Defaults to port 7545 (Ganache default) but can be overridden via env var
const localhostRpcUrl = process.env.NEXT_PUBLIC_RPC_URL || 'http://127.0.0.1:7545';

// Create custom localhost chain with the correct RPC URL
export const localhost = defineChain({
  id: 1337, // Common localhost chain ID
  name: 'Localhost',
  nativeCurrency: {
    decimals: 18,
    name: 'Ether',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: {
      http: [localhostRpcUrl],
    },
  },
  testnet: true,
});

// Contract addresses - all must be provided via environment variables
export const CONTRACT_ADDRESSES = {
  // Local development (Hardhat/Ganache)
  localhost: {
    escrow: process.env.NEXT_PUBLIC_ESCROW_ADDRESS || '',
    rewardDistribution: process.env.NEXT_PUBLIC_REWARD_ADDRESS || '',
    blockPublisher: process.env.NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS || '',
    stakeRegistry: process.env.NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS || '',
  },
  // Sepolia testnet
  sepolia: {
    escrow: process.env.NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA || '',
    rewardDistribution: process.env.NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA || '',
    blockPublisher: process.env.NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA || '',
    stakeRegistry: process.env.NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS_SEPOLIA || '',
  },
} as const;

// Supported chains
export const SUPPORTED_CHAINS = [localhost, sepolia];

// Network configuration
export const getChainConfig = (chainId: number) => {
  let config;
  
  if (chainId === localhost.id) {
    config = {
      chain: localhost,
      contracts: CONTRACT_ADDRESSES.localhost,
    };
  } else if (chainId === sepolia.id) {
    config = {
      chain: sepolia,
      contracts: CONTRACT_ADDRESSES.sepolia,
    };
  } else {
    // Default to localhost for unknown chains
    config = {
      chain: localhost,
      contracts: CONTRACT_ADDRESSES.localhost,
    };
  }
  
  // Validate configuration in development (helps catch missing env vars)
  // Only validate on client side (browser) to avoid SSR issues
  if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
    validateChainConfig(chainId, config.contracts);
  }
  
  return config;
};

// Backend API URL
export const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3000';

// Helper to check if a contract address is valid (not empty and properly formatted)
export const isValidContractAddress = (address: string | undefined): address is string => {
  if (!address || address.trim() === '') return false;
  // Basic Ethereum address validation (0x followed by 40 hex characters)
  return /^0x[a-fA-F0-9]{40}$/.test(address.trim());
};

// Helper to validate contract configuration and provide helpful error messages
export const validateChainConfig = (chainId: number, contracts: typeof CONTRACT_ADDRESSES.localhost) => {
  const chainName = chainId === localhost.id ? 'localhost' : chainId === sepolia.id ? 'Sepolia' : 'Unknown';
  
  if (!isValidContractAddress(contracts.escrow)) {
    const envVar = chainId === localhost.id 
      ? 'NEXT_PUBLIC_ESCROW_ADDRESS' 
      : 'NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA';
    console.warn(
      `⚠️  HealChain: Escrow contract address not configured for ${chainName}.\n` +
      `   Please set ${envVar} in your environment variables.\n` +
      `   This is required for task publishing and escrow management.`
    );
  }
  
  // RewardDistribution and BlockPublisher are optional (only needed for M7 and M6)
  if (!isValidContractAddress(contracts.rewardDistribution)) {
    const envVar = chainId === localhost.id 
      ? 'NEXT_PUBLIC_REWARD_ADDRESS' 
      : 'NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA';
    console.info(
      `ℹ️  HealChain: RewardDistribution contract not configured for ${chainName}.\n` +
      `   Set ${envVar} to enable reward distribution (M7).`
    );
  }
  
  if (!isValidContractAddress(contracts.blockPublisher)) {
    const envVar = chainId === localhost.id 
      ? 'NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS' 
      : 'NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA';
    console.info(
      `ℹ️  HealChain: BlockPublisher contract not configured for ${chainName}.\n` +
      `   Set ${envVar} to enable block publishing (M6).`
    );
  }

  if (!isValidContractAddress(contracts.stakeRegistry)) {
    const envVar = chainId === localhost.id 
      ? 'NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS' 
      : 'NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS_SEPOLIA';
    console.warn(
      `⚠️  HealChain: StakeRegistry contract not configured for ${chainName}.\n` +
      `   Please set ${envVar} in your environment variables.\n` +
      `   This is required for PoS aggregator selection (M2).`
    );
  }
};

