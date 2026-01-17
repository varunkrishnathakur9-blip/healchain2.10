# Federated Learning Training and Aggregation Workflow Guide

## Overview

This guide walks you through the complete workflow from miner registration to federated learning training and aggregation, following Algorithm 2-4 from your BTP Report.

## Prerequisites

Before starting, ensure:

1. ✅ **Backend is running** on port 3000
2. ✅ **Blockchain node** is running (Ganache for development)
3. ✅ **Smart contracts deployed** (HealChainEscrow, RewardDistribution)
4. ✅ **Contract addresses configured** in `.env.local` (automatically updated by deployment script)
5. ✅ **Task is published** with escrow automatically locked (M1) - **NEW: Escrow is locked before task creation**
6. ✅ **At least 3 miners registered** with verified proofs (M2)
7. ✅ **Aggregator is selected** via PoS (Algorithm 2.1)
8. ✅ **skFE is derived** and available to aggregator (Algorithm 2.2)

## Complete Workflow

```
M1: Task Publishing (Frontend)
  ↓
M2: Miner Registration (Frontend + Backend)
  ↓
  [When >= 3 verified miners]
  ↓
  Algorithm 2.1: PoS Aggregator Selection ✅
  Algorithm 2.2: Key Derivation (skFE) ✅
  Algorithm 2.3: Key Delivery ✅
  ↓
M3: FL Client Training (Python)
  ↓
M4: Aggregator Secure Aggregation (Python)
  ↓
M5: Miner Verification (FL Client + Aggregator)
  ↓
M6: Block Publishing (Aggregator + Backend)
  ↓
M7: Score Reveal & Rewards (Frontend + Smart Contract)
```

---

## Step-by-Step Guide

### Phase 1: Setup and Registration (M1-M2)

#### 1.1 Publish Task (M1) - **Automatic Escrow Locking**

**IMPORTANT**: With the new workflow, escrow is automatically locked on-chain **before** the task is created in the backend. The task is only created if escrow verification succeeds.

**Frontend**: Navigate to `/publish` and create a task:
1. Fill task details (ID, accuracy, reward, deadline)
2. Provide dataset (D) and initial model link (L) if needed
3. Generate or provide nonce (nonceTP)
4. Click "Publish Task"

**What Happens Automatically**:
1. **Step 1**: Frontend locks escrow on-chain (smart contract call)
2. **Step 2**: Frontend waits for transaction confirmation
3. **Step 3**: After confirmation, frontend sends escrow transaction hash to backend
4. **Step 4**: Backend verifies escrow is locked:
   - Checks transaction receipt is successful
   - Verifies escrow balance > 0
   - Verifies task exists on-chain with status LOCKED
   - Verifies publisher address matches
5. **Step 5**: Backend creates task with status `OPEN` (only if verification succeeds)

**Result**: 
- ✅ Escrow locked on-chain
- ✅ Task created with status = `OPEN` (not `CREATED`)
- ✅ Task ready for miner registration

**Note**: If escrow verification fails, the task is **not created** in the backend. You must ensure:
- You have sufficient ETH balance
- Contract addresses are correctly configured
- Transaction is confirmed on-chain

#### 1.2 Register Miners (M2)

**Frontend**: Navigate to `/mining` and register as miner:
- For each miner wallet:
  1. Generate miner proof using: `python fl_client/scripts/generate_miner_proof.py --dataset chestxray --address 0xYourAddress --upload-ipfs`
  2. Copy IPFS link (e.g., `ipfs://Qm...`)
  3. Click "Register" on task
  4. Paste IPFS link in proof field
  5. Submit registration

**Backend**: Automatically when >= 3 miners register:
- ✅ Verify proofs (Algorithm 2)
- ✅ Select aggregator via PoS (Algorithm 2.1)
- ✅ Derive skFE (Algorithm 2.2)
- ✅ Deliver key (Algorithm 2.3)
- ✅ Update task status to `OPEN`

**Check**: Verify aggregator is selected:
```bash
# Check backend logs or database
# Task should have aggregatorAddress set
```

---

### Phase 2: FL Client Training (M3) - **Frontend-Triggered**

#### 2.1 Start FL Client Service (Local)

**IMPORTANT**: Before triggering training from the frontend, you must start the FL client service on your local machine.

**File**: `fl_client/.env`

```bash
# Backend Configuration
BACKEND_URL=http://localhost:3000

# FL Client Service Configuration
FL_CLIENT_SERVICE_PORT=5001  # Port for local service

# Miner Configuration (STATIC - same for all tasks)
MINER_ADDRESS=0xYourMinerAddress  # Your miner wallet address
MINER_PRIVATE_KEY=0xYourPrivateKey  # Your miner private key

# Public Keys (for NDD-FE encryption) - STATIC
TP_PUBLIC_KEY=x_hex,y_hex  # Task Publisher public key
AGGREGATOR_PK=x_hex,y_hex  # Aggregator public key

# Training Configuration - STATIC
LOCAL_EPOCHS=1
DGC_THRESHOLD=0.9

# Blockchain Configuration - STATIC
RPC_URL=http://localhost:8545
CHAIN_ID=1337
```

**Important**: The `.env` file only contains **static miner-specific configuration**. Task-specific details (taskID, dataset, initialModelLink, etc.) are **automatically fetched from the backend** when training is triggered. You don't need to update `.env` for each task!

**Start FL Client Service** (for each miner):
```bash
cd fl_client
python scripts/start_service.py  # Starts HTTP service on port 5001
```

**Note**: The FL client service runs as a local HTTP server that the backend can communicate with to trigger training.

#### 2.2 Trigger Training from Frontend

**Frontend**: Navigate to `/mining` dashboard:

1. **View Registered Tasks**: Your registered tasks appear in "My Participations"
2. **Start Training**: Click "Start Training" button for any task with status `OPEN` or `AGGREGATING`
3. **Monitor Status**: Training status updates automatically:
   - `IDLE`: Ready to start
   - `TRAINING`: Training in progress
   - `COMPLETED`: Training finished, gradient submitted
   - `FAILED`: Training failed (check error message)

**What Happens**:
1. Frontend sends request to backend: `POST /miners/:address/tasks/:taskID/start-training`
2. Backend validates miner registration and task status
3. Backend triggers local FL client service: `POST http://localhost:5001/api/train`
4. FL client service performs training (M3):
   - Local model training
   - Gradient compression (DGC)
   - Contribution scoring (L2 norm)
   - NDD-FE encryption
   - Submission to backend

#### 2.3 What FL Client Does (M3)

For each registered task, the FL client:

1. **Polls Backend**: Checks for open tasks
   ```python
   GET /tasks/open
   ```

2. **Validates Task**: Checks if task is acceptable (dataset match, etc.)

3. **Local Training**:
   - Loads local dataset
   - Trains model for `LOCAL_EPOCHS` epochs
   - Computes gradients

4. **Gradient Compression (DGC)**:
   - Applies DGC threshold
   - Compresses gradients: `Δ' = DGC(Δ, τ)`

5. **Contribution Scoring**:
   - Computes L2 norm: `score = ||Δ'||₂`
   - Commits score: `commit = H(score || nonce)`

6. **NDD-FE Encryption**:
   - Encrypts compressed gradients using NDD-FE
   - Uses TP and Aggregator public keys

7. **Submits to Backend**:
   ```python
   POST /aggregator/submit-update
   {
     "taskID": "task_001",
     "minerAddress": "0x...",
     "scoreCommit": "0x...",
     "encryptedHash": "0x...",
     "message": "auth_message",
     "signature": "0x..."
   }
   ```
   
   **Note**: The FL client's `start_client.py` currently prints the payload but doesn't automatically submit. You may need to:
   - Manually submit via API call, or
   - Update `start_client.py` to call the submission endpoint

**Expected Output**:
```
✅ Found 1 tasks from backend
[M3] Prepared submission for task task_001
{
  "taskID": "task_001",
  "ciphertext": ["0x...", "0x..."],
  "scoreCommit": "0x...",
  "signature": "0x...",
  "miner_pk": "0x...",
  "quantization_scale": 1000.0
}
```

---

### Phase 3: Aggregator Secure Aggregation (M4)

#### 3.1 Start Aggregator Service (Local)

**IMPORTANT**: Before triggering aggregation from the frontend, you must start the aggregator service on your local machine.

**File**: `aggregator/.env`

```bash
# Backend Configuration
BACKEND_URL=http://localhost:3000

# Aggregator Service Configuration
AGGREGATOR_SERVICE_URL=http://localhost:5002  # Local service URL
AGGREGATOR_SERVICE_PORT=5002  # Port for local service

# Aggregator Keys
AGGREGATOR_SK=1234567890...  # Private key (scalar)
AGGREGATOR_PK=x_hex,y_hex   # Public key (EC point)
AGGREGATOR_ADDRESS=0xYourAggregatorAddress  # Required for verification

# Task Publisher Public Key
TP_PUBLIC_KEY=x_hex,y_hex

# Note: skFE will be derived from backend (Algorithm 2.2)
# FE_FUNCTION_KEY is only used as fallback
```

**Start Aggregator Service**:
```bash
cd aggregator
python scripts/start_service.py  # Starts HTTP service on port 5002
```

**Note**: The aggregator service runs as a local HTTP server that the backend can communicate with to trigger aggregation.

#### 3.2 Trigger Aggregation from Frontend

**Frontend**: Navigate to `/mining` dashboard:

1. **Check Aggregator Status**: If you are the selected aggregator for a task, you'll see "You are Aggregator" badge
2. **Start Aggregation**: Click "Start Aggregation" button for the task
3. **Monitor Status**: Aggregation status updates automatically:
   - `IDLE`: Ready to start
   - `WAITING_SUBMISSIONS`: Waiting for miner submissions
   - `AGGREGATING`: Performing secure aggregation
   - `VERIFYING`: Collecting miner verification feedback
   - `PUBLISHING`: Publishing block to blockchain
   - `COMPLETED`: Aggregation complete
   - `FAILED`: Aggregation failed (check error message)

**What Happens**:
1. Frontend sends request to backend: `POST /aggregator/:taskID/start`
2. Backend validates aggregator address matches selected aggregator
3. Backend triggers local aggregator service: `POST http://localhost:5002/api/aggregate`
4. Aggregator service performs aggregation (M4-M6):
   - Fetches key derivation metadata (Algorithm 2.2)
   - Derives skFE deterministically
   - Waits for miner submissions
   - Performs secure aggregation (NDD-FE decryption, BSGS recovery)
   - Builds candidate block
   - Collects miner verification (M5)
   - Publishes block on-chain (M6)

#### 3.3 What Aggregator Does (M4-M6)

**M4: Secure Aggregation**

1. **Initialize Keys**:
   - Loads skA, pkA, pkTP from environment
   - **Fetches key derivation metadata from backend** (Algorithm 2.2)
   - **Derives skFE deterministically** using same method as backend
   - Logs: `"skFE derived from backend metadata (Algorithm 2.2)"`

2. **Wait for Submissions**:
   - Polls backend: `GET /aggregator/:taskID/submissions`
   - Collects encrypted gradient updates from miners
   - Validates signatures and submissions

3. **Secure Aggregation**:
   - Decrypts using NDD-FE: `ndd_fe_decrypt(ciphertexts, skFE, skA, pkTP)`
   - Recovers gradients using BSGS: `recover_vector(encrypted_aggregate)`
   - Dequantizes gradients
   - Aggregates: `Δ_global = Σ(weights[i] * Δ_i)`

4. **Model Update**:
   - Applies aggregated gradients: `W_new = W_old + η * Δ_global`
   - Evaluates model accuracy

5. **Candidate Block Formation**:
   - Builds candidate block with:
     - Model hash
     - Accuracy
     - Participant list
     - Aggregator signature

**M5: Miner Verification**

1. **Broadcast Candidate**:
   - Sends candidate to backend: `POST /aggregator/:taskID/candidate`
   - Miners poll backend for candidate

2. **Collect Feedback**:
   - Miners verify candidate and submit feedback
   - Aggregator collects: `GET /aggregator/:taskID/feedback`

3. **Consensus Check**:
   - Checks if majority approves candidate
   - If approved → proceed to M6
   - If rejected → abort

**M6: Block Publishing**

1. **Publish Payload**:
   - Sends verified payload to backend: `POST /aggregator/:taskID/publish`
   - Backend publishes to blockchain (smart contract)

2. **Task Status Update**:
   - Task status → `REVEAL_OPEN`
   - Waiting for score reveals (M7)

**Expected Output**:
```
[Aggregator] Starting task task_001
[KeyManager] Loading keys for task task_001
[KeyManager] skFE derived from backend metadata (Algorithm 2.2): 3 miners
[Aggregator] Keys and task metadata loaded
[Aggregator] Waiting for miner submissions
[Aggregator] Received 3 submissions
[Aggregator] Performing NDD-FE secure aggregation
[Aggregator] Model updated | round=1 | accuracy=0.85
[Aggregator] Building candidate block
[Aggregator] Collecting miner verification feedback
[Aggregator] Candidate approved by majority
[Aggregator] Publishing verified payload to backend
[Aggregator] Task task_001 completed (awaiting reveal)
```

---

### Phase 4: Score Reveal and Rewards (M7)

#### 4.1 Reveal Scores (Frontend)

**Frontend**: Navigate to `/rewards`:
- For each miner: Reveal score commitment
- Task Publisher: Reveal accuracy commitment
- Submit transactions to smart contract

#### 4.2 Reward Distribution

**Backend**: Automatically calculates proportional rewards:
- Uses revealed scores: `reward_i = (score_i / total_score) * total_reward`
- Distributes via smart contract

---

## Quick Start Commands

### 1. Start Backend
```bash
cd backend
npm run dev
```

### 2. Start Blockchain (Ganache)
```bash
# Run Ganache on port 8545
# Or use existing node
```

### 3. Deploy Contracts (One-time setup)
```bash
cd contracts
# Deploy to localhost (Ganache)
node scripts/deploy-final-working.mjs

# Or deploy to Sepolia
node scripts/deploy-sepolia.js
```

**Note**: The deployment script automatically updates:
- `frontend/.env.local` with contract addresses
- `backend/.env.development` (or `.env.production`) with contract addresses

### 4. Publish Task (Frontend)
```bash
cd frontend
npm run dev
# Navigate to http://localhost:3001/publish
# Create task - escrow will be automatically locked before task creation
```

### 5. Register Miners (Frontend)
```bash
# For each miner:
# 1. Generate proof
cd fl_client
python scripts/generate_miner_proof.py --dataset chestxray --address 0xMiner1 --upload-ipfs

# 2. Register via frontend
# Navigate to http://localhost:3001/mining
# Paste IPFS link and register
```

### 6. Start FL Client Services (3+ Miners)

**NEW**: Start FL client services (one per miner machine):

```bash
# Terminal 1 (Miner 1)
cd fl_client
# Update .env with MINER_ADDRESS=0xMiner1
python scripts/start_service.py  # Starts service on port 5001

# Terminal 2 (Miner 2)
cd fl_client
# Update .env with MINER_ADDRESS=0xMiner2
python scripts/start_service.py  # Starts service on port 5001 (different machine)

# Terminal 3 (Miner 3)
cd fl_client
# Update .env with MINER_ADDRESS=0xMiner3
python scripts/start_service.py  # Starts service on port 5001 (different machine)
```

**Note**: Each miner runs the service on their own machine. The service listens for training triggers from the backend.

### 7. Trigger Training from Frontend

**Frontend**: Navigate to `http://localhost:3001/mining`
- Click "Start Training" button for each registered task
- Monitor training status in real-time
- Training runs automatically on your local FL client service

### 8. Start Aggregator Service

**NEW**: Start aggregator service (on aggregator's machine):

```bash
# Terminal (Aggregator)
cd aggregator
# Update .env with AGGREGATOR_ADDRESS=0xAggregatorAddress
python scripts/start_service.py  # Starts service on port 5002
```

### 9. Trigger Aggregation from Frontend

**Frontend**: Navigate to `http://localhost:3001/mining`
- If you are the selected aggregator, you'll see "You are Aggregator" badge
- Click "Start Aggregation" button for the task
- Monitor aggregation status in real-time
- Aggregation runs automatically on your local aggregator service

---

## Verification Checklist

### Before Training

- [ ] **Smart contracts deployed** and addresses configured in `.env.local`
- [ ] Backend is running and accessible
- [ ] Blockchain node is running (Ganache or Sepolia)
- [ ] **Task is published with status `OPEN`** (escrow automatically locked)
- [ ] **Escrow balance verified** on-chain (check task detail page)
- [ ] At least 3 miners registered with verified proofs
- [ ] Aggregator is selected (check `task.aggregatorAddress`)
- [ ] skFE is derived (check backend logs: "Key derivation/delivery succeeded")
- [ ] **FL client services are running** on each miner's machine (port 5001)
- [ ] **Aggregator service is running** on aggregator's machine (port 5002)
- [ ] FL clients have correct `.env` configuration
- [ ] Aggregator has correct `.env` configuration
- [ ] Frontend is accessible at `http://localhost:3001`

### During Training

- [ ] **Training triggered from frontend** mining dashboard
- [ ] FL client service receives training request from backend
- [ ] FL client performs local training, DGC, encryption
- [ ] FL client submits encrypted gradient to backend
- [ ] Frontend shows training status updates
- [ ] All miners complete training and submit updates

### During Aggregation

- [ ] **Aggregation triggered from frontend** mining dashboard (by aggregator)
- [ ] Aggregator service receives aggregation request from backend
- [ ] Aggregator fetches key derivation metadata (Algorithm 2.2)
- [ ] Aggregator derives skFE deterministically
- [ ] Aggregator performs NDD-FE decryption and secure aggregation
- [ ] Aggregator builds candidate block
- [ ] Frontend shows aggregation status updates

### After Aggregation

- [ ] Candidate block is built
- [ ] Miners verify candidate (M5)
- [ ] Majority consensus reached
- [ ] Block published to backend (M6)
- [ ] Task status updated to `REVEAL_OPEN`
- [ ] Frontend shows aggregation complete status

---

## Troubleshooting

### Escrow Locking Issues (M1)

**Problem**: "Escrow verification failed" when creating task
- **Solution**: 
  1. Verify you have sufficient ETH balance for the reward amount
  2. Check contract addresses are correctly configured in `.env.local`
  3. Verify contracts are deployed at the configured addresses
  4. Check transaction receipt in block explorer (or Ganache logs)
  5. Ensure transaction is confirmed before backend verification

**Problem**: "Task not created" after escrow transaction succeeds
- **Solution**:
  1. Check backend logs for verification errors
  2. Verify escrow balance > 0 on-chain
  3. Verify task exists on-chain with status LOCKED
  4. Verify publisher address matches your wallet address
  5. Check backend can connect to blockchain node

**Problem**: "Contract not deployed" error
- **Solution**:
  1. Deploy contracts using deployment script: `node scripts/deploy-final-working.mjs`
  2. Verify contract addresses are automatically updated in `.env.local`
  3. Restart frontend after updating `.env.local`
  4. Check `NEXT_PUBLIC_ESCROW_ADDRESS` matches deployed contract address

**Problem**: "Transaction reverted" when locking escrow
- **Solution**:
  1. Check task ID is unique (not already exists on-chain)
  2. Verify deadline is in the future
  3. Verify reward amount > 0
  4. Check contract has correct bytecode deployed
  5. Verify you're connected to the correct network (localhost vs Sepolia)

### FL Client Service Issues

**Problem**: "FL client service is not running"
- **Solution**: Start FL client service: `python scripts/start_service.py`
- **Check**: Service should be listening on `http://localhost:5001`
- **Verify**: `curl http://localhost:5001/api/health` (if health endpoint exists)

**Problem**: "Failed to start training" from frontend
- **Solution**: 
  1. Verify FL client service is running
  2. Check backend can reach FL client service (same machine or network)
  3. Verify `FL_CLIENT_SERVICE_URL` in backend `.env` matches service URL
  4. Check FL client `.env` has correct `MINER_ADDRESS` and configuration

**Problem**: "No tasks found"
- **Solution**: Check backend is running and task status is `OPEN`
- **Check**: `GET http://localhost:3000/tasks/open`

**Problem**: "Task not acceptable"
- **Solution**: Verify dataset matches task requirements
- **Check**: Task dataset vs. miner proof dataset

**Problem**: "NDD-FE encryption failed"
- **Solution**: Verify TP_PUBLIC_KEY and AGGREGATOR_PK are set correctly
- **Check**: Keys should be in format `x_hex,y_hex`

### Aggregator Service Issues

**Problem**: "Aggregator service is not running"
- **Solution**: Start aggregator service: `python scripts/start_service.py`
- **Check**: Service should be listening on `http://localhost:5002`
- **Verify**: `curl http://localhost:5002/api/health` (if health endpoint exists)

**Problem**: "Failed to start aggregation" from frontend
- **Solution**: 
  1. Verify aggregator service is running
  2. Check backend can reach aggregator service (same machine or network)
  3. Verify `AGGREGATOR_SERVICE_URL` in backend `.env` matches service URL
  4. Verify you are the selected aggregator for the task
  5. Check aggregator `.env` has correct `AGGREGATOR_ADDRESS` and configuration

**Problem**: "Failed to derive skFE from backend"
- **Solution**: 
  1. Check backend is running
  2. Verify task has >= 3 verified miners
  3. Check aggregator is selected
  4. Verify BACKEND_URL is correct
- **Fallback**: Uses `FE_FUNCTION_KEY` from env (not recommended)

**Problem**: "Insufficient valid submissions"
- **Solution**: 
  1. Ensure all miners have completed training and submitted updates
  2. Check backend has received submissions: `GET /aggregator/:taskID/submissions`
  3. Verify miner signatures are valid
  4. Wait for all registered miners to submit

**Problem**: "Candidate rejected by miners"
- **Solution**: 
  1. Check candidate block is valid
  2. Verify miner verification logic
  3. Check consensus threshold
  4. Review aggregator logs for errors

---

## API Endpoints Reference

### Backend

**Task Management**:
- `GET /tasks/open` - Get open tasks
- `POST /tasks/create` - Create task (M1) - **Requires `escrowTxHash` for verification**

**Miner Operations**:
- `POST /miners/register` - Register miner (M2)
- `GET /miners/my-tasks` - Get miner's registered tasks
- `POST /miners/:address/tasks/:taskID/start-training` - **Trigger FL client training** (M3)
- `GET /miners/:address/tasks/:taskID/training-status` - **Get training status** (M3)

**Aggregator Operations**:
- `POST /aggregator/submit-update` - Submit encrypted gradient (FL client → Backend)
- `GET /aggregator/:taskID/submissions` - Get submissions (Aggregator)
- `GET /aggregator/key-derivation/:taskID` - Get key derivation metadata (Algorithm 2.2)
- `POST /aggregator/:taskID/start` - **Trigger aggregator** (M4-M6)
- `GET /aggregator/:taskID/status` - **Get aggregator status** (M4-M6)
- `POST /aggregator/:taskID/candidate` - Broadcast candidate (M5)
- `GET /aggregator/:taskID/feedback` - Get miner feedback (M5)
- `POST /aggregator/:taskID/publish` - Publish verified block (M6)

**Local Services** (FL Client & Aggregator):
- `POST http://localhost:5001/api/train` - Trigger training (Backend → FL Client Service)
- `GET http://localhost:5001/api/train/status` - Get training status (Backend → FL Client Service)
- `POST http://localhost:5002/api/aggregate` - Trigger aggregation (Backend → Aggregator Service)
- `GET http://localhost:5002/api/aggregate/status` - Get aggregation status (Backend → Aggregator Service)

---

## Next Steps

After aggregation completes:

1. **M7: Score Reveal** - Miners and TP reveal commitments
2. **Reward Distribution** - Proportional rewards distributed
3. **Task Completion** - Task status → `REWARDED`

See `frontend/README.md` for M7 implementation details.

---

## Status: ✅ Ready for Training

All components are configured and ready:
- ✅ Algorithm 2.2: Key derivation working
- ✅ M3: FL client service ready for frontend-triggered training
- ✅ M4: Aggregator service ready for frontend-triggered aggregation
- ✅ Backend APIs ready with orchestration endpoints
- ✅ Frontend mining dashboard with training/aggregation controls

## Recent Workflow Improvements

### Automatic Escrow Locking (M1)

**Key Changes**:
1. **Automatic Escrow Verification**: Escrow is locked on-chain **before** task creation
2. **Atomic Operation**: Task is only created if escrow verification succeeds
3. **Status Management**: Tasks are created with status `OPEN` (not `CREATED`) when escrow is verified
4. **No Manual Steps**: No need for "Complete Escrow" button for new tasks
5. **Deployment Automation**: Contract addresses automatically updated in `.env` files after deployment

**Benefits**:
- ✅ Guaranteed escrow lock before task creation
- ✅ No orphaned tasks without escrow
- ✅ Better error handling and user feedback
- ✅ Automatic environment configuration
- ✅ Production-ready workflow

### Frontend-Triggered Training & Aggregation

**Key Changes**:
1. **FL Client Service**: Runs as local HTTP service, triggered by backend
2. **Aggregator Service**: Runs as local HTTP service, triggered by backend
3. **Frontend Controls**: Mining dashboard provides "Start Training" and "Start Aggregation" buttons
4. **Real-time Status**: Training and aggregation status updates automatically in frontend
5. **Better UX**: All operations can be triggered and monitored from the web interface

**Benefits**:
- ✅ Centralized control from frontend
- ✅ Real-time status monitoring
- ✅ Better user experience
- ✅ Easier to manage multiple miners/tasks
- ✅ No need to manually run Python scripts

**You can now proceed with federated learning training via the frontend mining dashboard!**

