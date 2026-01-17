/**
 * HealChain Frontend - Contract ABIs
 * Smart contract ABIs for HealChainEscrow, RewardDistribution, BlockPublisher, StakeRegistry
 */

// HealChainEscrow ABI (M1: Task Publishing, M7: Escrow)
export const ESCROW_ABI = [
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'bytes32', name: 'accuracyCommit', type: 'bytes32' },
      { internalType: 'uint256', name: 'deadline', type: 'uint256' },
    ],
    name: 'publishTask',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'refundPublisher',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'tasks',
    outputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'address', name: 'publisher', type: 'address' },
      { internalType: 'uint256', name: 'reward', type: 'uint256' },
      { internalType: 'bytes32', name: 'accuracyCommit', type: 'bytes32' },
      { internalType: 'uint256', name: 'deadline', type: 'uint256' },
      { internalType: 'uint8', name: 'status', type: 'uint8' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'escrowBalance',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'string', name: 'taskID', type: 'string' },
      { indexed: true, internalType: 'address', name: 'publisher', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'reward', type: 'uint256' },
    ],
    name: 'TaskCreated',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [{ indexed: true, internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'TaskLocked',
    type: 'event',
  },
] as const;

// RewardDistribution ABI (M7: Commit-Reveal & Rewards)
export const REWARD_DISTRIBUTION_ABI = [
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'uint256', name: 'accuracy', type: 'uint256' },
      { internalType: 'bytes32', name: 'nonce', type: 'bytes32' },
      { internalType: 'bytes32', name: 'commitHash', type: 'bytes32' },
    ],
    name: 'revealAccuracy',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'uint256', name: 'score', type: 'uint256' },
      { internalType: 'bytes32', name: 'nonce', type: 'bytes32' },
      { internalType: 'bytes32', name: 'scoreCommit', type: 'bytes32' },
    ],
    name: 'revealScore',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'address[]', name: 'miners', type: 'address[]' },
    ],
    name: 'distribute',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'address', name: 'miner', type: 'address' },
    ],
    name: 'minerReveals',
    outputs: [
      { internalType: 'uint256', name: 'score', type: 'uint256' },
      { internalType: 'bool', name: 'revealed', type: 'bool' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'accuracyRevealed',
    outputs: [{ internalType: 'bool', name: '', type: 'bool' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'totalScore',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'string', name: 'taskID', type: 'string' },
      { indexed: false, internalType: 'uint256', name: 'accuracy', type: 'uint256' },
    ],
    name: 'AccuracyRevealed',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'string', name: 'taskID', type: 'string' },
      { indexed: true, internalType: 'address', name: 'miner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'score', type: 'uint256' },
    ],
    name: 'ScoreRevealed',
    type: 'event',
  },
] as const;

// BlockPublisher ABI (M6: Block Publishing)
export const BLOCK_PUBLISHER_ABI = [
  {
    inputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'bytes32', name: 'modelHash', type: 'bytes32' },
      { internalType: 'uint256', name: 'accuracy', type: 'uint256' },
      { internalType: 'bytes32[]', name: 'scoreCommits', type: 'bytes32[]' },
    ],
    name: 'publishBlock',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'string', name: 'taskID', type: 'string' }],
    name: 'publishedBlocks',
    outputs: [
      { internalType: 'string', name: 'taskID', type: 'string' },
      { internalType: 'bytes32', name: 'modelHash', type: 'bytes32' },
      { internalType: 'uint256', name: 'accuracy', type: 'uint256' },
      { internalType: 'address', name: 'aggregator', type: 'address' },
      { internalType: 'bytes32[]', name: 'scoreCommits', type: 'bytes32[]' },
      { internalType: 'uint256', name: 'timestamp', type: 'uint256' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'string', name: 'taskID', type: 'string' },
      { indexed: false, internalType: 'bytes32', name: 'modelHash', type: 'bytes32' },
      { indexed: false, internalType: 'uint256', name: 'accuracy', type: 'uint256' },
      { indexed: true, internalType: 'address', name: 'aggregator', type: 'address' },
    ],
    name: 'BlockPublished',
    type: 'event',
  },
] as const;

// StakeRegistry ABI (M2: PoS Aggregator Selection - On-Chain Stake Management)
export const STAKE_REGISTRY_ABI = [
  {
    inputs: [],
    name: 'depositStake',
    outputs: [],
    stateMutability: 'payable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'uint256', name: 'amount', type: 'uint256' }],
    name: 'requestWithdrawal',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [],
    name: 'withdrawStake',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'address', name: 'miner', type: 'address' }],
    name: 'getAvailableStake',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'address', name: 'miner', type: 'address' }],
    name: 'isEligible',
    outputs: [{ internalType: 'bool', name: '', type: 'bool' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [{ internalType: 'address', name: 'miner', type: 'address' }],
    name: 'getStake',
    outputs: [
      { internalType: 'uint256', name: 'availableStake', type: 'uint256' },
      { internalType: 'uint256', name: 'totalStake', type: 'uint256' },
      { internalType: 'uint256', name: 'pendingWithdrawal', type: 'uint256' },
      { internalType: 'uint256', name: 'unlockTime', type: 'uint256' },
    ],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'MIN_STAKE',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'UNLOCK_DELAY',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    inputs: [],
    name: 'getTotalLocked',
    outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'address', name: 'miner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount', type: 'uint256' },
      { indexed: false, internalType: 'uint256', name: 'totalStake', type: 'uint256' },
    ],
    name: 'StakeDeposited',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'address', name: 'miner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount', type: 'uint256' },
      { indexed: false, internalType: 'uint256', name: 'unlockTime', type: 'uint256' },
    ],
    name: 'StakeWithdrawalRequested',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'address', name: 'miner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount', type: 'uint256' },
    ],
    name: 'StakeWithdrawn',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: 'address', name: 'miner', type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount', type: 'uint256' },
      { indexed: false, internalType: 'string', name: 'reason', type: 'string' },
    ],
    name: 'StakeSlashed',
    type: 'event',
  },
] as const;
