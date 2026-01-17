# 🏥 HealChain Smart Contracts

A comprehensive suite of Ethereum smart contracts implementing a privacy-preserving federated learning framework with commit-reveal schemes and blockchain-based incentive mechanisms.

## 🎯 Overview

HealChain enables decentralized federated learning where multiple participants can collaboratively train machine learning models without sharing raw data. The system uses cryptographic commitments, escrow mechanisms, and proportional reward distribution to ensure fairness and privacy.

## 🏗️ Architecture

### Core Contracts

#### 1. HealChainEscrow
**Purpose**: Manages task creation and reward escrow
- **M1**: Task publishers create federated learning tasks with staked rewards
- **Safety**: Automatic refunds if tasks fail to complete
- **States**: CREATED → LOCKED → PUBLISHED → AWAITING_REVEAL → COMPLETED/FAILED

**Key Functions**:
- `publishTask()` - Create task with escrowed reward
- `lockTask()` - Lock task for accuracy publication
- `publishAccuracy()` - Publish accuracy commit
- `refundPublisher()` - Safety refund mechanism

#### 2. RewardDistribution
**Purpose**: Implements commit-reveal scheme and proportional reward distribution
- **M7a**: Publisher reveals true accuracy
- **M7b**: Miners reveal contribution scores
- **M7c**: Proportional reward distribution based on scores

**Key Functions**:
- `revealAccuracy()` - Publisher reveals target accuracy
- `revealScore()` - Miners reveal contribution scores
- `distribute()` - Calculate and distribute rewards proportionally

#### 3. BlockPublisher
**Purpose**: Records aggregated model blocks on-chain
- **M6**: Aggregators publish final model metadata
- Stores model hashes, accuracy, and score commitments
- Provides immutable record of training results

**Key Functions**:
- `publishBlock()` - Record aggregated model
- `getScoreCommits()` - Retrieve score commitments for verification

### Interface Layer

#### IHealChain
Canonical interface defining all HealChain contract interactions, providing:
- Standardized function signatures
- Type definitions for structs and enums
- Complete protocol specification

## 🔄 Protocol Flow

### M1: Task Creation
1. Publisher commits to target accuracy: `Commit(accuracy || nonceTP)`
2. Publisher stakes reward in escrow contract
3. Task becomes active with deadline

### M2-M3: Training Phase
1. Miners register for participation
2. Miners submit encrypted gradient metadata
3. Aggregator collects and verifies contributions

### M4-M5: Aggregation & Verification
1. Aggregator creates aggregated model
2. Miners verify model quality through consensus
3. Score commitments recorded in block

### M6: Block Publication
1. Aggregator publishes final model metadata
2. Block contains model hash, accuracy, and score commits
3. Task status updated to AWAITING_REVEAL

### M7: Commit-Reveal & Rewards
1. Publisher reveals true accuracy
2. Miners reveal contribution scores
3. Rewards distributed proportionally to scores

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Hardhat v3.1.0+
- Ethereum wallet (MetaMask or local node)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd contracts

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Configure environment variables
# - DEPLOYER_PRIVATE_KEY: Deployer wallet private key
# - SEPOLIA_RPC_URL: Alchemy/Infura endpoint (for testnet)
# - ETHERSCAN_API_KEY: For contract verification (optional)
```

### Compilation
```bash
# Compile all contracts
npm run compile

# Clean build artifacts
npm run clean
```

## 🎮 Deployment

### 🏠 Local Development
```bash
# Start local Hardhat node
npx hardhat node

# Deploy contracts (in separate terminal)
node scripts/deploy-final-working.mjs

# Or use npm script
npm run deploy:localhost
```

### 🌐 Testnet (Sepolia)
```bash
# Set environment variables
export SEPOLIA_RPC_URL="https://sepolia.infura.io/v3/YOUR_PROJECT_ID"
export DEPLOYER_PRIVATE_KEY="your_private_key"

# Deploy to Sepolia testnet
node scripts/deploy-sepolia.js

# Or use npm script
npm run deploy:sepolia
```

### 📝 Deployment Scripts

#### Working Scripts
- `scripts/deploy-final-working.mjs` - ✅ **Recommended for local deployment**
- `scripts/deploy-ganache.js` - Updated local deployment
- `scripts/deploy-sepolia.js` - Sepolia testnet deployment

#### Usage Examples
```bash
# Deploy to localhost (recommended)
node scripts/deploy-final-working.mjs

# Deploy using Hardhat (alternative)
npx hardhat run scripts/deploy-ganache.js --network localhost

# Deploy to Sepolia
npx hardhat run scripts/deploy-sepolia.js --network sepolia
```

### 🎯 Recent Deployment (Local)
```
✅ HealChainEscrow: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
✅ RewardDistribution: 0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0
✅ Network: Local Hardhat Node (http://127.0.0.1:8545)
✅ Chain ID: 31337
```

## 🧪 Testing

### Run All Tests
```bash
npm test
```

### Specific Test Categories
```bash
# Run specific test files
npx hardhat test test/HealChainEscrow.test.ts
npx hardhat test test/RewardDistribution.test.ts
npx hardhat test test/HealChainIntegration.test.ts

# Run Counter test
npx hardhat test test/Counter.test.ts
```

### 📊 Test Coverage
- **Unit Tests**: Individual contract functionality
- **Integration Tests**: Full protocol flow
- **Commit-Reveal Tests**: Cryptographic verification
- **Edge Case Tests**: Error conditions and security

## ⚙️ Configuration

### Hardhat Config
```typescript
networks: {
  hardhat: {
    type: "edr-simulated",
    chainId: 31337,
    // Note: 'npx hardhat node' runs on port 8545 by default (cannot be changed via config)
    // If using Ganache, you don't need to run 'npx hardhat node' at all
  },
  localhost: {
    type: "http",
    url: "http://127.0.0.1:7545",  // Ganache default port
    chainId: 1337,  // Ganache default chainId
    accounts: [
      "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
      "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690",
      // ... more accounts
    ],
  },
  sepolia: {
    type: "http",
    url: process.env.SEPOLIA_RPC_URL,
    chainId: 11155111,
    accounts: process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [],
  },
}
```

### 🔧 Environment Variables

#### Required for Local Development
```bash
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

#### Required for Sepolia Testnet
```bash
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
DEPLOYER_PRIVATE_KEY=your_private_key_here
ETHERSCAN_API_KEY=your_etherscan_api_key
```

#### Backend Integration (Ganache)
```bash
ESCROW_ADDRESS=<deployed-address>  # Will be set automatically by deployment script
ESCROW_CONTRACT_ADDRESS=<deployed-address>
REWARD_CONTRACT_ADDRESS=<deployed-address>
RPC_URL=http://127.0.0.1:7545  # Ganache port
```

### 📦 Solidity Version
- **Version**: 0.8.28
- **Optimizer**: Enabled (200 runs)
- **Target**: EVM compatible (cancun)

## 🔒 Security Features

### 🛡️ Protection Mechanisms
- **Reentrancy Protection**: All state-changing functions use OpenZeppelin's `ReentrancyGuard`
- **Access Control**: `Ownable` pattern for admin functions
- **Input Validation**: Comprehensive parameter validation
- **Deadline Enforcement**: Time-based task expiration
- **Balance Checks**: Sufficient fund verification

### 🔐 Commit-Reveal Security
- **Cryptographic Commitments**: Keccak256-based commitment schemes
- **Nonce-Based Randomness**: Secure random number generation
- **Tamper-Proof Verification**: Score validation against commitments

## ⛽ Gas Optimization

### 💾 Storage Patterns
- **Efficient Struct Packing**: Optimized data layout
- **Minimal Storage Writes**: Reduced state changes
- **Batch Operations**: Grouped transactions where possible

### ⚡ Loop Optimization
- **Fixed Iteration Limits**: Prevent infinite loops
- **Unchecked Arithmetic**: Safe gas-efficient operations
- **Efficient Data Structures**: Optimized mappings and arrays

## 🔗 Integration

### 💻 Backend Integration
```typescript
import { ethers } from "ethers";

// Contract interaction example
const escrow = new ethers.Contract(escrowAddress, escrowABI, signer);
await escrow.publishTask(taskID, accuracyCommit, deadline, { 
  value: ethers.parseEther("1.0") 
});

// Reward distribution
const reward = new ethers.Contract(rewardAddress, rewardABI, signer);
await reward.revealAccuracy(taskID, accuracy, nonce, commit);
await reward.distribute(taskID, [miner1, miner2, miner3]);
```

### 🌐 Frontend Integration
```javascript
// Web3 integration
const escrowContract = new web3.eth.Contract(escrowABI, escrowAddress);
await escrowContract.methods.publishTask(taskID, accuracyCommit, deadline)
  .send({ from: account, value: rewardAmount });

// Event listening
escrowContract.events.TaskPublished()
  .on('data', (event) => {
    console.log('Task published:', event.returnValues);
  });
```

## 📋 Contract Addresses

### 🏠 Development (Local)
```
HealChainEscrow:     0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
RewardDistribution:  0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0
BlockPublisher:     (Deployed locally)
Network:            Local Hardhat Node (http://127.0.0.1:8545)
Chain ID:           31337
```

### 🌐 Testnet (Sepolia)
```
HealChainEscrow:     (Deploy to Sepolia)
RewardDistribution: (Deploy to Sepolia)
BlockPublisher:     (Deploy to Sepolia)
Network:            Sepolia Testnet
Chain ID:           11155111
```

## 🔍 Monitoring & Verification

### 🔎 Etherscan Verification
```bash
# Verify contracts on Etherscan
npx hardhat verify --network sepolia <contract-address>

# Example:
npx hardhat verify --network sepolia 0x1234...5678
```

### 📊 Event Monitoring
- **Task Events**: TaskPublished, TaskLocked, AccuracyPublished
- **Reward Events**: AccuracyRevealed, ScoreRevealed, RewardsPaid
- **Block Events**: BlockPublished
- **Error Events**: TaskFailed, RefundIssued

## 🐛 Troubleshooting

### 🔧 Common Issues

#### Port Already in Use
```bash
# Check what's using port 8545
netstat -ano | findstr :8545

# Kill the process
taskkill /PID <PID> /F

# Restart Hardhat node
npx hardhat node
```

#### Nonce Issues
```bash
# Restart Hardhat node to reset nonces
# Or wait for pending transactions to clear

# Check current nonce
node -e "const provider = new ethers.JsonRpcProvider('http://127.0.0.1:8545'); provider.getTransactionCount('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266').then(console.log);"
```

#### Compilation Issues
```bash
# Clean and recompile
npx hardhat clean && npx hardhat compile

# Check Solidity version
npx hardhat compile --verbose
```

#### Connection Issues
```bash
# Verify Hardhat node is running
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://127.0.0.1:8545

# Check network status
npx hardhat console --network localhost --eval "console.log('Connected to:', network.name)"
```

### 📝 Error Messages

#### "Cannot read properties of undefined (reading 'getSigners')"
- **Solution**: Use the standalone deployment script: `node scripts/deploy-final-working.mjs`

#### "Nonce too low"
- **Solution**: Restart Hardhat node or wait for pending transactions

#### "Insufficient funds"
- **Solution**: Check wallet balance and ensure sufficient ETH for gas

## 🤝 Contributing

### 📋 Development Guidelines
1. Follow Solidity best practices
2. Add comprehensive tests for new features
3. Document gas costs and optimization
4. Security audit required for major changes
5. Update documentation for API changes

### 🎨 Code Style
- **Indentation**: 4 spaces
- **Comments**: Comprehensive inline documentation
- **NatSpec**: Complete function documentation
- **Type Safety**: Strong typing where applicable
- **Naming**: Clear, descriptive variable and function names

### 🧪 Testing Requirements
- Unit tests for all public functions
- Integration tests for protocol flows
- Edge case and error condition testing
- Gas optimization benchmarks
- Security vulnerability testing

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

### 📚 Resources
- **Test Files**: Check `test/` directory for usage examples
- **Interface Definitions**: Review `src/interfaces/` for protocol specs
- **Protocol Documentation**: See inline code documentation
- **Deployment Guide**: Follow the Quick Start section

### 🐛 Issue Reporting
- **Bug Reports**: Open GitHub issues with detailed reproduction steps
- **Feature Requests**: Submit with clear requirements and use cases
- **Security Issues**: Report privately via security@healchain.dev
- **Questions**: Check documentation or open discussion issues

---

**🚀 Ready to build decentralized federated learning with HealChain!**
