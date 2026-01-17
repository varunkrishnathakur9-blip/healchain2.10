# HealChain On-Chain Stake Management Implementation

## Overview

This document describes the complete implementation of on-chain Proof of Stake (PoS) aggregator selection for HealChain. The implementation includes a smart contract for stake management, backend integration for on-chain stake validation, and proper PoS selection using validated stakes from the blockchain.

## Table of Contents

1. [Architecture](#architecture)
2. [Smart Contract: StakeRegistry](#smart-contract-stakeregistry)
3. [Backend Integration](#backend-integration)
4. [PoS Selection Algorithm](#pos-selection-algorithm)
5. [Deployment Guide](#deployment-guide)
6. [Usage Guide](#usage-guide)
7. [Security Considerations](#security-considerations)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Architecture

### Overview

The HealChain PoS implementation consists of three main components:

1. **StakeRegistry Smart Contract**: On-chain stake management with deposit, withdrawal, and slashing capabilities
2. **Backend Integration**: Services to read and validate stakes from the blockchain
3. **PoS Selection Algorithm**: Deterministic weighted random selection based on on-chain stakes

### Component Interaction

```
┌─────────────────┐
│  Miners         │
│  (deposit ETH)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ StakeRegistry   │  ◄─── Backend reads stakes
│  Contract       │
│  (on-chain)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Backend        │
│  posSelection   │  ───► Validates stakes
│  Service        │       Selects aggregator
└─────────────────┘
```

---

## Smart Contract: StakeRegistry

### Contract Address

Location: `contracts/src/StakeRegistry.sol`

### Features

1. **Stake Deposition**: Miners deposit ETH to participate in PoS selection
2. **Stake Withdrawal**: Miners can request withdrawal with unlock delay
3. **Stake Slashing**: Misbehaving miners can have stakes slashed
4. **Eligibility Checking**: Verify if miner has sufficient stake (>= MIN_STAKE)
5. **Batch Stake Queries**: Get stakes for multiple miners at once

### Key Functions

#### `depositStake()`
Miners deposit ETH to participate in aggregator selection.

```solidity
function depositStake() external payable;
```

- **Requirements**: `msg.value > 0`
- **Effects**: Increases miner's `totalStake`
- **Events**: `StakeDeposited(address indexed miner, uint256 amount, uint256 totalStake)`

#### `getAvailableStake(address miner)`
Get stake available for PoS selection (excludes pending withdrawals).

```solidity
function getAvailableStake(address miner) public view returns (uint256);
```

- **Returns**: Available stake amount (totalStake - pendingWithdrawal)

#### `isEligible(address miner)`
Check if miner meets minimum stake requirement.

```solidity
function isEligible(address miner) public view returns (bool);
```

- **Returns**: `true` if `getAvailableStake(miner) >= MIN_STAKE`

#### `getStakes(address[] calldata miners)`
Get stakes for multiple miners (optimized for PoS selection).

```solidity
function getStakes(address[] calldata miners) 
    external 
    view 
    returns (uint256[] memory stakes, uint256 totalTotalStake);
```

- **Returns**: Array of stakes and total stake sum

#### `requestWithdrawal(uint256 amount)`
Initiate withdrawal request (unlock period applies).

```solidity
function requestWithdrawal(uint256 amount) external;
```

- **Requirements**: `amount > 0`, `amount <= totalStake - pendingWithdrawal`
- **Effects**: Sets `pendingWithdrawal` and `unlockTime`
- **Events**: `StakeWithdrawalRequested(address indexed miner, uint256 amount, uint256 unlockTime)`

#### `withdrawStake()`
Complete withdrawal after unlock period.

```solidity
function withdrawStake() external;
```

- **Requirements**: `pendingWithdrawal > 0`, `block.timestamp >= unlockTime`
- **Effects**: Transfers ETH to miner, reduces `totalStake`
- **Events**: `StakeWithdrawn(address indexed miner, uint256 amount)`

#### `slashStake(address miner, uint256 amount, string reason)`
Slash stake for misbehavior (only authorized slasher).

```solidity
function slashStake(address miner, uint256 amount, string calldata reason) 
    external 
    onlySlasher;
```

- **Requirements**: Miner has sufficient available stake
- **Effects**: Reduces miner's stake, transfers to owner
- **Events**: `StakeSlashed(address indexed miner, uint256 amount, string reason)`

### Configuration

- **MIN_STAKE**: Minimum stake required for eligibility (default: 1 ETH)
- **UNLOCK_DELAY**: Delay before withdrawal can be completed (default: 7 days)
- **slasher**: Authorized address for slashing (settable by owner)

### Events

```solidity
event StakeDeposited(address indexed miner, uint256 amount, uint256 totalStake);
event StakeWithdrawalRequested(address indexed miner, uint256 amount, uint256 unlockTime);
event StakeWithdrawn(address indexed miner, uint256 amount);
event StakeSlashed(address indexed miner, uint256 amount, string reason);
event MinStakeUpdated(uint256 newMinStake);
event UnlockDelayUpdated(uint256 newUnlockDelay);
```

---

## Backend Integration

### Contract Interaction Service

Location: `backend/src/contracts/stakeRegistry.ts`

This service provides functions to interact with the StakeRegistry contract:

#### `getAvailableStake(minerAddress: string): Promise<bigint>`
Get available stake for a miner (excludes pending withdrawals).

#### `isMinerEligible(minerAddress: string): Promise<boolean>`
Check if miner is eligible for aggregator selection.

#### `getStakes(minerAddresses: string[]): Promise<{stakes: bigint[], totalStake: bigint}>`
Get stakes for multiple miners (optimized batch query).

#### `getStakeInfo(minerAddress: string): Promise<{availableStake, totalStake, pendingWithdrawal, unlockTime}>`
Get full stake information for a miner.

#### `getMinStake(): Promise<bigint>`
Get minimum stake requirement from contract.

### Environment Configuration

Add to `backend/.env.development` or `backend/.env.production`:

```env
STAKE_REGISTRY_ADDRESS=0x...
```

The backend automatically reads this address and initializes the contract connection.

### Miner Registration Flow

Location: `backend/src/services/minerSelectionService.ts`

The `registerMiner` function now:

1. Verifies miner proof (Algorithm 2 requirement)
2. **Validates on-chain stake** from StakeRegistry contract
3. Checks eligibility (must have >= MIN_STAKE)
4. Stores on-chain stake in database for record-keeping
5. Warns if miner is not eligible (but allows registration)

**Important**: Miners can register even without sufficient stake, but they will not be selected as aggregators. The PoS selection algorithm filters to only eligible miners.

---

## PoS Selection Algorithm

### Implementation

Location: `backend/src/crypto/posSelection.ts`

The `selectAggregatorViaPoS` function implements Algorithm 2.1 from the BTP Report:

#### Algorithm Steps

1. **Get Eligible Miners**: 
   - Query database for miners with `proofVerified: true` (Algorithm 2 requirement)
   - Filter to only miners with `isEligible(address) == true` (on-chain check)

2. **Fetch On-Chain Stakes**:
   - Call `getStakes(eligibleAddresses)` to get all stakes in one batch
   - Validate all stakes are > 0

3. **Calculate Total Stake**:
   - Sum all eligible miner stakes
   - Ensure total > 0

4. **Deterministic Weighted Selection**:
   - Seed: `${taskID}:${addresses}:${stakes}` (includes stakes for determinism)
   - Generate deterministic random number using SHA-256 hash
   - Select miner using cumulative distribution function (weighted by stake)

5. **Update Database**:
   - Store selected aggregator address
   - Update miner records with actual on-chain stakes

#### Deterministic Selection

The selection is **deterministic** because:
- Same `taskID` + same eligible miners + same stakes = same aggregator
- Seed includes stakes to ensure changes in stakes affect selection
- Uses SHA-256 hash for pseudo-randomness (reproducible)

This ensures:
- ✅ Consistency across multiple calls
- ✅ Verifiability (anyone can recompute selection)
- ✅ Prevention of manipulation

#### Example Selection

```
Miners: [A, B, C]
Stakes: [2 ETH, 3 ETH, 5 ETH]
Total:  10 ETH

Probabilities:
- A: 20% (2/10)
- B: 30% (3/10)  
- C: 50% (5/10)

Random (0-9): 7
Cumulative: A=2, B=5, C=10
Result: Miner C selected (7 < 10, 7 >= 5)
```

---

## Deployment Guide

### Prerequisites

1. **Compile Contracts**:
   ```bash
   cd contracts
   forge build
   ```

2. **Setup Environment**:
   ```bash
   # contracts/.env
   RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
   DEPLOYER_PRIVATE_KEY=0x...
   ```

### Deploy StakeRegistry

```bash
cd contracts
node scripts/deploy-stake-registry.js
```

The script will:
1. Deploy StakeRegistry contract
2. Configure MIN_STAKE (default: 1 ETH) and UNLOCK_DELAY (default: 7 days)
3. Update `backend/.env.development` with `STAKE_REGISTRY_ADDRESS`
4. Save deployment info to `contracts/deployments/stake-registry.json`

### Verify Deployment

```bash
# Check contract on Etherscan
# Or interact directly:
cast call <STAKE_REGISTRY_ADDRESS> "MIN_STAKE()" --rpc-url $RPC_URL
```

### Configuration

After deployment, configure contract parameters if needed:

```solidity
// Set minimum stake (only owner)
stakeRegistry.setMinStake(ethers.parseEther("2.0")); // 2 ETH

// Set unlock delay (only owner)
stakeRegistry.setUnlockDelay(14 * 24 * 60 * 60); // 14 days

// Set slasher address (only owner)
stakeRegistry.setSlasher(0x...);
```

---

## Usage Guide

### For Miners

#### 1. Deposit Stake

Miners must deposit at least MIN_STAKE to be eligible for aggregator selection:

```javascript
// Using ethers.js
const stakeRegistry = new ethers.Contract(
  STAKE_REGISTRY_ADDRESS,
  abi,
  signer
);

// Deposit 1 ETH
await stakeRegistry.depositStake({
  value: ethers.parseEther("1.0")
});
```

#### 2. Check Eligibility

```javascript
const eligible = await stakeRegistry.isEligible(minerAddress);
const stake = await stakeRegistry.getAvailableStake(minerAddress);
```

#### 3. Register for Task

Miners register through the backend API (stake is validated automatically):

```bash
POST /api/miners/register
{
  "taskID": "...",
  "address": "0x...",
  "proof": "ipfs://...",
  "publicKey": "...",
  "message": "...",
  "signature": "..."
}
```

The backend will:
- Verify proof (Algorithm 2)
- Check on-chain stake eligibility
- Register miner if eligible
- Warn if stake is insufficient (miner won't be selected as aggregator)

#### 4. Request Withdrawal

```javascript
// Request withdrawal of 0.5 ETH
await stakeRegistry.requestWithdrawal(ethers.parseEther("0.5"));
// Wait for unlock delay (7 days default)
```

#### 5. Complete Withdrawal

```javascript
// After unlock delay
await stakeRegistry.withdrawStake();
```

### For Backend/System

#### Query Stakes

```typescript
import { getStakes, isMinerEligible } from './contracts/stakeRegistry';

// Check single miner
const eligible = await isMinerEligible("0x...");

// Get stakes for multiple miners (for PoS selection)
const { stakes, totalStake } = await getStakes([
  "0x...",
  "0x...",
  "0x..."
]);
```

#### Select Aggregator

The PoS selection is automatically called during miner finalization:

```typescript
import { finalizeMiners } from './services/minerSelectionService';

// Automatically selects aggregator using on-chain stakes
const result = await finalizeMiners(taskID);
console.log("Selected aggregator:", result.aggregator);
```

### For Frontend/UI

#### Stake Management Hook

The frontend provides a `useStake` hook for easy stake management:

```typescript
import { useStake } from '@/hooks/useStake';

function MinerDashboard() {
  const {
    minStake,
    availableStake,
    isEligible,
    depositStake,
    refetchStake,
  } = useStake();

  // Deposit stake
  const handleDeposit = async () => {
    await depositStake("1.0"); // Deposit 1 ETH
  };

  return (
    <div>
      <p>Available Stake: {availableStake} ETH</p>
      <p>Minimum Required: {minStake} ETH</p>
      <p>Eligible: {isEligible ? 'Yes' : 'No'}</p>
      <button onClick={handleDeposit}>Deposit Stake</button>
    </div>
  );
}
```

#### Components

- **StakeDepositForm**: Component for depositing stakes
- **MinerRegistrationForm**: Updated to show stake eligibility status
- **Mining Page**: Shows stake status dashboard

#### Environment Variables

Add to `frontend/.env.local` or `frontend/.env`:

```env
NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS=0x...
NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS_SEPOLIA=0x...
```

---

## Security Considerations

### 1. On-Chain Validation

**Critical**: Stakes are always validated from the blockchain. Database values are for record-keeping only and are not trusted for selection.

### 2. Deterministic Selection

The selection algorithm is deterministic and includes stakes in the seed. This prevents:
- Last-minute stake manipulation
- Selection gaming
- Inconsistent aggregator selection

### 3. Withdrawal Delay

The unlock delay (default: 7 days) prevents:
- Quick deposit-withdraw cycles to game selection
- Stakes being withdrawn mid-task

### 4. Slashing Mechanism

Authorized slasher can slash stakes for:
- Malicious aggregation
- Incorrect model updates
- Protocol violations

### 5. Minimum Stake Requirement

MIN_STAKE prevents:
- Sybil attacks with tiny stakes
- Free-riding on selection process

### 6. Proof Verification

Miners must provide valid proofs (Algorithm 2) AND sufficient stake. Both are required.

---

## Testing

### Manual Testing

#### 1. Test Stake Deposit

```bash
# Using cast (Foundry)
cast send <STAKE_REGISTRY_ADDRESS> \
  "depositStake()" \
  --value 1ether \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY
```

#### 2. Test Eligibility Check

```bash
cast call <STAKE_REGISTRY_ADDRESS> \
  "isEligible(address)" \
  0x... \
  --rpc-url $RPC_URL
```

#### 3. Test PoS Selection

```typescript
// In backend
const aggregator = await selectAggregatorViaPoS(taskID);
console.log("Selected:", aggregator);
```

### Automated Testing

Create tests in `contracts/test/StakeRegistry.test.ts`:

```typescript
describe("StakeRegistry", () => {
  it("should allow deposit and eligibility check", async () => {
    await stakeRegistry.depositStake({ value: ethers.parseEther("1.0") });
    const eligible = await stakeRegistry.isEligible(minerAddress);
    expect(eligible).to.be.true;
  });

  it("should filter ineligible miners in PoS selection", async () => {
    // Register 3 miners, only 2 have sufficient stake
    // Verify only eligible miners are considered
  });
});
```

---

## Troubleshooting

### Issue: "No eligible miners with sufficient stake found"

**Cause**: Miners have registered but haven't deposited stakes or don't meet MIN_STAKE requirement.

**Solution**:
1. Check miner stakes: `await stakeRegistry.getAvailableStake(address)`
2. Check MIN_STAKE: `await stakeRegistry.MIN_STAKE()`
3. Ensure miners deposit sufficient stake before registration

### Issue: "Error getting on-chain stake"

**Cause**: Contract address not configured or network connectivity issue.

**Solution**:
1. Verify `STAKE_REGISTRY_ADDRESS` in backend `.env`
2. Check RPC_URL is correct and accessible
3. Verify contract is deployed on the correct network

### Issue: Selection returns different aggregator on each call

**Cause**: Stakes are changing between calls or seed is not deterministic.

**Solution**:
1. Ensure stakes are locked (no pending withdrawals)
2. Verify seed includes stakes: `${taskID}:${addresses}:${stakes}`
3. Check deterministicRandom function is using same seed

### Issue: Miner registered but not selected as aggregator

**Cause**: Miner doesn't meet eligibility requirements.

**Check**:
1. Proof is verified: `proofVerified: true`
2. On-chain stake >= MIN_STAKE: `await stakeRegistry.isEligible(address)`
3. No pending withdrawals affecting available stake

---

## Migration from Old Implementation

### Before (Database-Only Stakes)

- Stakes stored in database only
- No validation
- Default stake = 1 for all miners
- Not a true PoS system

### After (On-Chain Stakes)

- Stakes validated from blockchain
- Must deposit to StakeRegistry contract
- True PoS with economic security
- Slashing mechanism for misbehavior

### Migration Steps

1. **Deploy StakeRegistry Contract**:
   ```bash
   node contracts/scripts/deploy-stake-registry.js
   ```

2. **Update Backend Environment**:
   ```env
   STAKE_REGISTRY_ADDRESS=0x...
   ```

3. **Update Frontend Environment**:
   ```env
   NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS=0x...
   NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS_SEPOLIA=0x...
   ```

4. **Migrate Existing Miners** (if needed):
   - Miners must deposit stakes on-chain
   - Old database stakes are ignored
   - Backend reads from contract only

5. **Restart Backend**:
   ```bash
   cd backend
   npm run build
   npm start
   ```

6. **Rebuild Frontend**:
   ```bash
   cd frontend
   npm run build
   npm start
   ```

---

## Future Enhancements

### Potential Improvements

1. **Dynamic MIN_STAKE**: Adjust based on network conditions or task requirements
2. **Stake Delegation**: Allow miners to delegate stakes to trusted aggregators
3. **Slashing Events**: Automatic slashing based on on-chain verification
4. **Stake Vesting**: Gradual stake unlocking for committed miners
5. **Multi-Token Support**: Support for ERC20 tokens in addition to ETH

### Integration Opportunities

1. **Governance**: Use stakes for protocol governance voting
2. **Reputation System**: Track miner performance and adjust stake requirements
3. **Insurance Pool**: Pool slashed stakes for miner protection

---

## References

- **Algorithm 2.1**: BTP Report Section 4.3 - PoS Aggregator Selection
- **StakeRegistry Contract**: `contracts/src/StakeRegistry.sol`
- **Backend Integration**: `backend/src/contracts/stakeRegistry.ts`
- **PoS Selection**: `backend/src/crypto/posSelection.ts`
- **Miner Registration**: `backend/src/services/minerSelectionService.ts`

---

## Frontend Integration

### Components Added

1. **useStake Hook** (`frontend/src/hooks/useStake.ts`):
   - Provides stake management functionality
   - Reads stake data from StakeRegistry contract
   - Handles deposit, withdrawal requests, and eligibility checks
   - Uses wagmi hooks for blockchain interaction

2. **StakeDepositForm Component** (`frontend/src/components/forms/StakeDepositForm.tsx`):
   - UI for depositing stakes
   - Shows current stake status and eligibility
   - Validates minimum stake requirement
   - Transaction modal integration

3. **Updated MinerRegistrationForm** (`frontend/src/components/forms/MinerRegistrationForm.tsx`):
   - Shows stake eligibility status before registration
   - Warns users if insufficient stake
   - Links to stake deposit page
   - Allows registration even if not eligible (but won't be selected as aggregator)

4. **Updated Mining Page** (`frontend/src/app/mining/page.tsx`):
   - Stake status dashboard at top
   - Shows available stake, minimum required, eligibility
   - Quick access to stake deposit form
   - Handles `?action=stake` URL parameter

### Configuration

1. **Contract ABI**: Added `STAKE_REGISTRY_ABI` to `frontend/src/lib/contracts.ts`
2. **Web3 Config**: Added `stakeRegistry` address to `CONTRACT_ADDRESSES` in `frontend/src/lib/web3.ts`
3. **Environment Variables**: Added `NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS` variables

### User Flow

1. User connects wallet on Mining page
2. Mining page shows stake status (if StakeRegistry configured)
3. If not eligible, user sees warning and can click "Deposit Stake"
4. StakeDepositForm allows depositing ETH
5. After deposit, stake status updates automatically
6. User can register for tasks (eligibility shown in registration form)
7. Only eligible miners can be selected as aggregators (backend validation)

---

## Summary

The HealChain on-chain stake management implementation provides:

✅ **True Proof of Stake**: On-chain stake validation and management
✅ **Security**: Economic security through staked funds
✅ **Deterministic Selection**: Verifiable and consistent aggregator selection
✅ **Flexibility**: Configurable minimum stakes and unlock delays
✅ **Accountability**: Slashing mechanism for misbehavior
✅ **Frontend Integration**: Complete UI for stake management and status display

The implementation follows Algorithm 2.1 from the BTP Report and ensures proper PoS-based aggregator selection with on-chain stake validation. Both backend and frontend are fully integrated with the StakeRegistry contract.
