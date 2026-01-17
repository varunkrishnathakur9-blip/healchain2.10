# 🏥 HealChain Frontend

Interactive frontend for HealChain - a blockchain-enabled, privacy-preserving federated learning framework.

**Status**: ✅ **100% Compliant** with BTP Phase 1 Report  
**Review**: See [FRONTEND_REVIEW_REPORT.md](./FRONTEND_REVIEW_REPORT.md) for detailed compliance review

## Overview

This frontend provides a role-based UI for:
- **Publishers**: Create and manage federated learning tasks
- **Miners**: Register and participate in training tasks
- **Observers**: Monitor task status and progress

## Features

### Protocol Phase Implementation
- **M1**: Task Publishing with escrow deposit
- **M2-M3**: Miner registration and training participation
- **M7**: Score reveal and reward distribution

### Pages
- **Dashboard** (`/`): Overview of all tasks and statistics
- **Tasks** (`/tasks`): Browse and filter all tasks
- **Task Detail** (`/tasks/[id]`): Detailed view of a specific task
- **Publish** (`/publish`): Create new FL tasks (M1)
- **Mining** (`/mining`): Register as miner and view available tasks (M2-M3)
- **Rewards** (`/rewards`): Reveal scores and claim rewards (M7)

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **Web3**: wagmi v2 + RainbowKit
- **Styling**: Tailwind CSS
- **State Management**: React Hooks + TanStack Query

## Setup

### Prerequisites
- Node.js 18+
- Backend API running (default: http://localhost:3000)
- Blockchain node (Ganache/Hardhat for local, or Sepolia testnet)

### Installation

```bash
npm install
```

### Environment Variables

**⚠️ Production-Ready Configuration**: All contract addresses must be provided via environment variables. No hardcoded placeholders.

Create a `.env.local` file in the `frontend/` directory with the following variables:

```env
# ============================================
# Backend Configuration
# ============================================
# Backend API URL (default: http://localhost:3000)
NEXT_PUBLIC_BACKEND_URL=http://localhost:3000

# ============================================
# Contract Addresses - Localhost (Ganache/Hardhat)
# ============================================
# REQUIRED: Escrow contract address for task publishing (M1)
# Deploy contracts to your local network and set the deployed address
NEXT_PUBLIC_ESCROW_ADDRESS=

# Optional: RewardDistribution contract for reward distribution (M7)
# Set this if you've deployed the RewardDistribution contract
NEXT_PUBLIC_REWARD_ADDRESS=

# Optional: BlockPublisher contract for block publishing (M6)
# Set this if you've deployed the BlockPublisher contract
NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=

# ============================================
# Contract Addresses - Sepolia Testnet
# ============================================
# REQUIRED: Escrow contract address on Sepolia
# Deploy contracts to Sepolia and set the deployed address
NEXT_PUBLIC_ESCROW_ADDRESS_SEPOLIA=

# Optional: RewardDistribution contract on Sepolia
NEXT_PUBLIC_REWARD_ADDRESS_SEPOLIA=

# Optional: BlockPublisher contract on Sepolia
NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS_SEPOLIA=

# ============================================
# WalletConnect (Optional)
# ============================================
# Get your project ID from https://cloud.walletconnect.com
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=

# ============================================
# Development
# ============================================
# Set to 'true' for additional debug logging
NEXT_PUBLIC_DEBUG=false
```

**Important Notes:**
- **No placeholders**: All contract addresses must be actual deployed contract addresses
- **Network-specific**: Separate addresses for localhost and Sepolia
- **Required vs Optional**: 
  - `NEXT_PUBLIC_ESCROW_ADDRESS` is **required** for M1 (task publishing)
  - RewardDistribution and BlockPublisher are **optional** (only needed for M7 and M6)
- **Any account can access**: Contracts are permissionless - any account on Sepolia or Ganache can interact with them
- **Validation**: The frontend will show helpful warnings in development if addresses are missing

### Development

**Important:** Make sure your backend is running on port 3000 before starting the frontend.

```bash
# Start the frontend (runs on port 3001)
npm run dev
```

The frontend will be available at:
- **Frontend**: [http://localhost:3001](http://localhost:3001)
- **Backend API**: [http://localhost:3000](http://localhost:3000) (must be running separately)

**Note:** The frontend is configured to run on port 3001 to avoid conflicts with the backend on port 3000.

## Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── app/              # Next.js pages
│   │   ├── layout.tsx    # Root layout with providers
│   │   ├── page.tsx      # Dashboard
│   │   ├── publish/      # M1: Task publishing
│   │   ├── mining/       # M2-M3: Miner dashboard
│   │   ├── rewards/      # M7: Rewards & reveal
│   │   └── tasks/        # Task list & detail
│   │
│   ├── components/       # React components
│   │   ├── forms/        # Form components
│   │   ├── modals/       # Modal components
│   │   └── ...           # Base components
│   │
│   ├── hooks/            # Custom React hooks
│   │   ├── useWallet.ts  # Wallet connection
│   │   ├── useContract.ts # Smart contract interactions
│   │   ├── useTask.ts    # Task management
│   │   └── useMiner.ts   # Miner operations
│   │
│   ├── lib/              # Utilities
│   │   ├── contracts.ts  # Contract ABIs
│   │   ├── web3.ts       # Web3 configuration
│   │   └── api.ts        # Backend API client
│   │
│   └── styles/           # Global styles
│       └── globals.css
```

### Key Components

#### Hooks
- **useWallet**: Wallet connection and message signing
- **useContract**: Smart contract write operations
- **useTask**: Task data fetching and management
- **useMiner**: Miner registration

#### Forms
- **PublishTaskForm**: M1 - Create new task with escrow
- **MinerRegistrationForm**: M2 - Register as miner
- **ScoreRevealForm**: M7b - Reveal contribution score

#### Pages
- **Dashboard**: Overview with stats and recent tasks
- **Publish**: Task creation interface
- **Mining**: Available tasks and registration
- **Rewards**: Score reveal and reward claiming
- **Tasks**: Task browsing and filtering

## Protocol Flow

### M1: Task Publishing
1. User fills out task form (accuracy, reward, deadline)
2. Frontend generates commit hash (accuracy + nonce)
3. Backend creates task record
4. User submits transaction to deposit reward in escrow
5. Task status updates to ESCROW_LOCKED

### M2-M3: Miner Participation
1. Miner views available tasks
2. Miner registers for a task (M2)
3. FL client performs training and submits encrypted gradients (M3)
4. Task status updates to TRAINING → AGGREGATED → VERIFIED

### M7: Rewards
1. Publisher reveals accuracy (M7a)
2. Miners reveal scores (M7b)
3. Rewards distributed proportionally (M7c)

## Important Notes

### Frontend Constraints
- **NO cryptography**: All crypto operations happen in FL-client and aggregator
- **NO training**: Training is performed by FL-client
- **Backend is untrusted**: Frontend only uses backend for read-only data and submission routing
- **Blockchain is source of truth**: All critical state comes from smart contracts

### Web3 Integration
- Uses wagmi v2 for contract interactions
- RainbowKit for wallet connection UI
- Supports localhost (Ganache/Hardhat) and Sepolia testnet
- Contract addresses configured per network

## Development Notes

### Contract Interactions
- Write operations use `useWriteContract` hook
- Read operations should use `useReadContract` hook directly in components
- Transaction status tracked with `useWaitForTransactionReceipt`

### Backend API
- All API calls go through `/lib/api.ts`
- Backend serves as read-only data source and submission relay
- Authentication via wallet message signing

### State Management
- React hooks for local state
- TanStack Query for server state caching
- Real-time updates via polling (can be upgraded to WebSockets)

## Testing

See [TESTING.md](./TESTING.md) for testing guide.

```bash
npm test              # Run all tests
npm run test:watch    # Watch mode
npm run test:coverage # With coverage
```

## Improvements

See [IMPROVEMENTS.md](./IMPROVEMENTS.md) for details on recent improvements:
- ✅ Comprehensive error handling system
- ✅ Mobile optimization
- ✅ Testing setup
- ✅ Environment configuration template

## 📋 Compliance Status

**BTP Report Compliance**: ✅ **100%**

All required modules implemented:
- ✅ **M1**: Task Publishing with Escrow and Commit
  - Task creation form ✅
  - Escrow deposit ✅
  - Commit hash generation ✅
- ✅ **M2**: Miner Selection and Registration
  - Miner registration form ✅
  - PoS selection (backend) ✅
- ✅ **M3**: Local Model Training (Read-Only UI)
  - Training status display ✅
  - No training operations (correctly off-chain) ✅
- ✅ **M4-M6**: Aggregation and Verification (Read-Only UI)
  - Status tracking ✅
  - No aggregation operations (correctly off-chain) ✅
- ✅ **M7**: Smart Contract Reveal and Reward Distribution
  - Accuracy reveal (M7a) ✅
  - Score reveal (M7b) ✅
  - Reward distribution (M7c) ✅

**See**: [FRONTEND_REVIEW_REPORT.md](./FRONTEND_REVIEW_REPORT.md) for detailed compliance matrix

---

## Future Enhancements

- [ ] WebSocket integration for real-time updates (see IMPROVEMENTS.md)
- [ ] Aggregator status page
- [ ] Transaction history
- [ ] Advanced filtering and search
- [ ] Task analytics and charts
- [ ] E2E tests with Playwright

## License

See main project LICENSE file.

---

**Last updated**: January 2026  
**Compliance**: ✅ **100%** - All frontend requirements from BTP Report implemented  
**Wireframe Compliance**: ✅ **100%** - All gaps fixed, layout matches specification
