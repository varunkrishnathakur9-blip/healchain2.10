# Frontend ↔ FL-Client Architecture

## Overview

**The frontend does NOT directly interact with the FL-client.** They are completely separate applications that communicate only through the backend API and blockchain.

## Architecture Diagram

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Frontend   │────────▶│   Backend   │◀────────│  FL-Client   │
│  (Next.js)  │         │   (Express) │        │   (Python)   │
│  Port 3001  │         │  Port 3000  │        │  Standalone  │
└─────────────┘         └─────────────┘        └─────────────┘
      │                        │                        │
      │                        │                        │
      └────────────────────────┼────────────────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Blockchain  │
                        │  (Smart      │
                        │   Contracts) │
                        └─────────────┘
```

## Communication Flow

### 1. **Frontend → Backend** (Read-Only Data)
- **Purpose**: Display task status, miner registrations, training progress
- **Endpoints Used**:
  - `GET /tasks` - List all tasks
  - `GET /tasks/:taskID` - Get task details
  - `GET /tasks/open` - Get open tasks (same endpoint FL-client uses)
- **Data Flow**: Frontend polls backend to display current state

### 2. **FL-Client → Backend** (Training Operations)
- **Purpose**: Discover tasks, submit encrypted gradients
- **Endpoints Used**:
  - `GET /tasks/open` - Discover available tasks
  - `POST /aggregator/submit-update` - Submit encrypted gradient metadata (M3)
- **Data Flow**: FL-client performs training off-chain, then submits results

### 3. **Frontend → Blockchain** (On-Chain Actions)
- **Purpose**: Publish tasks, escrow funds, reveal scores, distribute rewards
- **Operations**:
  - M1: `publishTask()` - Escrow reward
  - M7a: `revealAccuracy()` - Publisher reveals accuracy
  - M7b: `revealScore()` - Miner reveals score
  - M7c: `distributeRewards()` - Distribute rewards
- **Data Flow**: Direct smart contract interactions via wagmi

### 4. **FL-Client → Blockchain** (On-Chain Actions)
- **Purpose**: Reveal scores (M7b)
- **Operations**:
  - M7b: `revealScore()` - Miner reveals committed score
- **Data Flow**: Direct smart contract interactions via web3.py

## Key Separation Principles

### ✅ **What Frontend Does**
1. **UI Display**: Shows task status, miner list, training progress (read-only)
2. **User Actions**: 
   - Publisher: Create tasks, escrow funds, reveal accuracy, distribute rewards
   - Miner: Register for tasks, reveal scores
   - Observer: View task status
3. **Blockchain Interactions**: Direct smart contract calls for on-chain operations

### ✅ **What FL-Client Does**
1. **Training**: Performs local model training (off-chain)
2. **Cryptography**: 
   - Gradient compression (DGC)
   - Contribution scoring (||Δ'||₂)
   - NDD-FE encryption
   - Commit generation
3. **Submission**: Submits encrypted gradients to backend
4. **Blockchain Interactions**: Direct smart contract calls for score reveals

### ❌ **What Frontend Does NOT Do**
- ❌ **No Training**: Training happens in FL-client
- ❌ **No Cryptography**: All crypto operations in FL-client/aggregator
- ❌ **No Gradient Submission**: FL-client handles this
- ❌ **No Direct FL-Client Communication**: No API calls to FL-client

### ❌ **What FL-Client Does NOT Do**
- ❌ **No UI**: FL-client is a command-line application
- ❌ **No Frontend Communication**: FL-client doesn't call frontend APIs
- ❌ **No Task Creation**: Publishers use frontend for this

## Example Workflow: Complete Task Lifecycle

### M1: Task Publishing
```
1. Publisher (Frontend) → Backend API: POST /tasks/create
2. Publisher (Frontend) → Smart Contract: publishTask() [Escrow]
3. Backend stores task in database
```

### M2: Miner Registration
```
1. Miner (Frontend) → Backend API: POST /miners/register
2. Backend validates and stores miner registration
3. When 3+ miners registered → Backend auto-selects aggregator
```

### M3: Training Phase
```
1. FL-Client polls Backend API: GET /tasks/open
2. FL-Client performs local training (off-chain)
3. FL-Client computes gradients, scores, commits
4. FL-Client → Backend API: POST /aggregator/submit-update
5. Backend stores encrypted gradient metadata
6. Frontend polls Backend API: GET /tasks/:taskID (shows status)
```

### M4-M6: Aggregation & Verification
```
1. Aggregator (autonomous) processes gradients
2. Aggregator → Backend API: POST /aggregator/submit-candidate
3. Aggregator → Backend API: POST /aggregator/publish
4. Frontend polls Backend API: GET /tasks/:taskID (shows updated status)
```

### M7: Rewards
```
1. Publisher (Frontend) → Smart Contract: revealAccuracy()
2. Miner (FL-Client) → Smart Contract: revealScore()
3. Publisher (Frontend) → Smart Contract: distributeRewards()
4. Frontend polls Backend API: GET /tasks/:taskID (shows reward status)
```

## Frontend Display of FL-Client Activity

The frontend shows FL-client activity **indirectly** through backend state:

### Mining Page (`/mining`)
```typescript
// Shows read-only training status
<Training Status Panel>
  Note: Training happens in FL-client (off-chain)
  Status: Waiting for FL-client to start
  No UI actions available
</Training Status Panel>
```

### Task Detail Page (`/tasks/[id]`)
```typescript
// Shows protocol phase timeline
[M3] Training Phase
  ⏳ Pending
  └─ Status: Waiting for miners
  └─ Note: Training happens off-chain (FL-client)
```

### Task Timeline Component
```typescript
// Displays current phase status
- M3 status comes from backend: task.status === 'AGGREGATING'
- Frontend infers: "Training completed" when status changes
- No direct FL-client communication
```

## Backend as the Bridge

The backend serves as the **untrusted relay** between frontend and FL-client:

1. **Task Discovery**: Both frontend and FL-client use `GET /tasks/open`
2. **Status Updates**: Frontend reads status, FL-client writes status
3. **No Trust Required**: Backend doesn't perform crypto or training
4. **Blockchain is Source of Truth**: Critical state verified on-chain

## Summary

| Component | Role | Communication |
|-----------|------|---------------|
| **Frontend** | UI + On-chain actions | → Backend (read) → Blockchain (write) |
| **FL-Client** | Training + Crypto | → Backend (submit) → Blockchain (reveal) |
| **Backend** | Untrusted relay | ← Frontend ← FL-client |
| **Blockchain** | Source of truth | ← Frontend ← FL-client |

**Key Takeaway**: Frontend and FL-client are **completely independent** and communicate only through:
1. **Backend API** (for task data and submissions)
2. **Blockchain** (for on-chain operations)

There is **no direct frontend ↔ FL-client communication**.

