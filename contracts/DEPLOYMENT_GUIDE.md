# HealChain Contract Deployment Guide

## 🚀 Quick Start

### Prerequisites
1. **Ganache** running on `http://127.0.0.1:7545`
2. **Node.js** and npm installed
3. Contracts compiled (`npx hardhat compile`)

### ⚠️ Important Notes

- **You DON'T need `npx hardhat node`** - Use Ganache instead
- **Hardhat node** runs on port 8545 (cannot be changed via config)
- **Ganache** runs on port 7545 (default)
- The deployment script automatically updates your env files

## 📋 Deployment Steps

### 1. Start Ganache
Make sure Ganache is running on `http://127.0.0.1:7545`

### 2. Compile Contracts
```bash
cd contracts
npx hardhat compile
```

### 3. Deploy to Ganache
```bash
npm run deploy
```

Or directly:
```bash
node scripts/deploy-final-working.mjs
```

### 4. What Happens
The deployment script will:
- ✅ Deploy `HealChainEscrow` to Ganache
- ✅ Deploy `RewardDistribution` to Ganache  
- ✅ Automatically update `frontend/.env.local`
- ✅ Automatically update `backend/.env.development`
- ✅ Display the deployed contract addresses

### 5. Restart Services
After deployment, restart:
- **Frontend**: To pick up new `NEXT_PUBLIC_ESCROW_ADDRESS`
- **Backend**: To pick up new `ESCROW_ADDRESS` and `RPC_URL`

## 🔧 Configuration

### Environment Variables

The deployment script uses:
- `DEPLOYER_PRIVATE_KEY` from `contracts/.env` (or defaults to Hardhat account #0)
- RPC URL: `http://127.0.0.1:7545` (Ganache)

### Network Settings

- **Ganache**: Port 7545, Chain ID 1337
- **Hardhat Node**: Port 8545, Chain ID 31337 (not needed if using Ganache)

## ❌ Common Issues

### Issue: Contract not found at address
**Solution**: Deploy the contract using `npm run deploy`

### Issue: Port 8545 vs 7545 confusion
**Solution**: 
- Stop `npx hardhat node` (you don't need it)
- Use Ganache on port 7545
- Update all RPC URLs to `http://127.0.0.1:7545`

### Issue: Transaction succeeds but contract reads fail
**Solution**: 
- Contract not deployed at that address
- Deploy using `npm run deploy`
- Update env files with new addresses

## 📝 Manual Deployment (if script fails)

If the automatic deployment fails, you can manually:

1. Deploy contracts using Hardhat:
   ```bash
   npx hardhat run scripts/deploy-ganache.js --network localhost
   ```

2. Copy the addresses to:
   - `frontend/.env.local`: `NEXT_PUBLIC_ESCROW_ADDRESS=...`
   - `backend/.env.development`: `ESCROW_ADDRESS=...`

## ✅ Verification

After deployment, verify:
1. Contracts exist: Check Ganache transactions
2. Env files updated: Check `frontend/.env.local` and `backend/.env.development`
3. Frontend can read: Check browser console for contract calls
4. Backend can read: Check backend logs for contract verification

