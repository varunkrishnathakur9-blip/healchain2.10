# 🚀 HealChain Deployment Scripts

This directory contains the essential deployment scripts for HealChain smart contracts.

## 📁 Scripts Overview

### 🏠 Local Development

#### `deploy-final-working.mjs` ⭐ **RECOMMENDED**
- **Purpose**: Primary deployment script for local development
- **Usage**: `node scripts/deploy-final-working.mjs` or `npm run deploy`
- **Features**: 
  - Direct ethers provider connection
  - Automatic nonce management
  - Contract verification
  - Comprehensive error handling
  - Environment variable output

#### `deploy-ganache.js`
- **Purpose**: Local deployment via Hardhat
- **Usage**: `npm run deploy:localhost`
- **Features**: 
  - Hardhat runtime integration
  - Reads contract artifacts
  - Environment variable output

### 🌐 Testnet Deployment

#### `deploy-sepolia.js`
- **Purpose**: Sepolia testnet deployment
- **Usage**: `npm run deploy:sepolia`
- **Features**: 
  - Sepolia network configuration
  - Environment variable validation
  - Production-ready deployment

## 🎯 Quick Usage

### Local Development (Recommended)
```bash
# 1. Start Hardhat node
npx hardhat node

# 2. Deploy contracts
npm run deploy
```

### Alternative Local Deployment
```bash
# Using Hardhat integration
npm run deploy:localhost
```

### Sepolia Testnet
```bash
# Set environment variables
export SEPOLIA_RPC_URL="https://sepolia.infura.io/v3/YOUR_PROJECT_ID"
export DEPLOYER_PRIVATE_KEY="your_private_key"

# Deploy to Sepolia
npm run deploy:sepolia
```

## 📋 Deployment Output

All scripts output the contract addresses in the required format for backend integration:

```bash
📋 Add these to your backend .env.development:
ESCROW_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
ESCROW_CONTRACT_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
REWARD_CONTRACT_ADDRESS=0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0
```

## 🔧 Prerequisites

- Hardhat node running (for local deployment)
- Environment variables configured (for testnet)
- Sufficient ETH balance for gas fees

## 🐛 Troubleshooting

### Common Issues
- **Port 8545 in use**: Kill existing Hardhat node
- **Nonce errors**: Restart Hardhat node
- **Insufficient funds**: Check wallet balance

### Solutions
```bash
# Check port usage
netstat -ano | findstr :8545

# Kill process
taskkill /PID <PID> /F

# Restart node
npx hardhat node
```

---

**🚀 Use `deploy-final-working.mjs` for the most reliable deployment experience!**
