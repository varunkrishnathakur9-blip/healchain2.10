# HealChain Frontend - Protocol-Faithful UI Wireframe Specifications

**Version:** 1.0  
**Date:** 2026-01-02  
**Status:** Protocol-Aligned Specification

---

## 🔒 PROTOCOL CONSTRAINTS (NON-NEGOTIABLE)

- **Frontend Role:** Passive observer + transaction initiator ONLY
- **No Cryptography:** All crypto operations in FL-client, aggregator, or contracts
- **No Training:** Training happens in FL-client (off-chain)
- **No Aggregation:** Aggregation happens in aggregator (off-chain)
- **Source of Truth:** Smart contracts are the ONLY source of truth
- **Backend:** Read-only, untrusted relay
- **Aggregator:** Autonomous, off-chain, read-only visibility

---

## PAGE: /dashboard

**Protocol Modules:**
- M1 (Task Publishing Overview)
- M2-M7 (Task Lifecycle Overview)

**Visible Roles:**
- Publisher
- Miner
- Observer

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Wallet Connect Component                                   │
│ - Role Badge (Publisher/Miner/Observer)                     │
│ - Navigation                                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PROTOCOL STATISTICS PANEL (Read-Only)                        │
│ - Total Tasks (All Statuses)                                 │
│ - Active Tasks (OPEN, CREATED)                               │
│ - Completed Tasks (REWARDED, COMPLETED)                      │
│ - Total Escrow Locked (Sum of all escrowBalance)             │
│ - My Tasks (if Publisher)                                    │
│ - My Participations (if Miner)                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ RECENT TASKS LIST (Read-Only)                                │
│ - Task Card 1: taskID, status, deadline, reward            │
│ - Task Card 2: ...                                           │
│ - Task Card N: ...                                            │
│ - "View All Tasks" Link → /tasks                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ QUICK ACTIONS (Role-Based)                                   │
│ - Publisher: "Publish New Task" → /publish                  │
│ - Miner: "Browse Available Tasks" → /mining                  │
│ - Observer: "View All Tasks" → /tasks                       │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Protocol Statistics Panel**
- **Type:** Read-only
- **Data Source:** 
  - Smart Contract: `HealChainEscrow.escrowBalance()` (aggregated)
  - Backend: `GET /tasks` (filtered by status)
- **Triggered Algorithm Step:** None (observational only)
- **Update Frequency:** Poll every 5 seconds

**2. Recent Tasks List**
- **Type:** Read-only
- **Data Source:** Backend `GET /tasks?limit=10`
- **Triggered Algorithm Step:** None
- **Click Action:** Navigate to `/tasks/[taskID]`

**3. Quick Actions Panel**
- **Type:** Navigation (no protocol action)
- **Data Source:** User role (from wallet)
- **Triggered Algorithm Step:** None

### UI State Mapping:

- **"Total Tasks"** → Backend aggregation of all tasks
- **"Active Tasks"** → Backend filter: `status IN ['CREATED', 'OPEN']`
- **"Completed Tasks"** → Backend filter: `status IN ['REWARDED', 'COMPLETED']`
- **"Total Escrow Locked"** → Smart Contract: Sum of `escrowBalance(taskID)` for all tasks
- **"My Tasks"** → Backend filter: `publisher == walletAddress`
- **"My Participations"** → Backend filter: `miners.contains(walletAddress)`

### Allowed Actions:
- ✅ View statistics (read-only)
- ✅ Navigate to task detail pages
- ✅ Navigate to publish page (Publisher role)
- ✅ Navigate to mining page (Miner role)

### Forbidden Actions:
- ❌ Modify statistics (read-only data)
- ❌ Create tasks from dashboard (must use /publish)
- ❌ Start training from dashboard (training is off-chain)

---

## PAGE: /tasks

**Protocol Modules:**
- M1-M7 (System-wide task observer view)

**Visible Roles:**
- Publisher
- Miner
- Observer

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Page Title: "All Tasks"                                     │
│ - "Publish Task" Button (Publisher only) → /publish         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ FILTER PANEL (Read-Only Filters)                            │
│ - Status Filter: [All | CREATED | OPEN | COMMIT_CLOSED |    │
│                   REVEAL_OPEN | REVEAL_CLOSED | AGGREGATING |│
│                   VERIFIED | REWARDED | CANCELLED]          │
│ - Publisher Filter: [All | My Tasks] (if Publisher)        │
│ - Sort: [Newest | Oldest | Reward (High→Low)]              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TASK LIST (Read-Only Cards)                                  │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task Card                                            │     │
│ │ - Task ID: task_001                                  │     │
│ │ - Status Badge: [OPEN]                              │     │
│ │ - Publisher: 0x1234...5678                          │     │
│ │ - Reward: 1.5 ETH                                   │     │
│ │ - Deadline: 2026-01-10 12:00 UTC                    │     │
│ │ - Miners: 3/5 registered                            │     │
│ │ - Escrow Balance: 1.5 ETH (from contract)           │     │
│ │ - "View Details" Button → /tasks/task_001           │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ [Repeat for each task]                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PAGINATION (Read-Only)                                       │
│ - Page 1 of 5                                                │
│ - Previous | Next                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Filter Panel**
- **Type:** Read-only filter (UI state only)
- **Data Source:** Backend `GET /tasks?status=X&publisher=Y&limit=50&offset=0`
- **Triggered Algorithm Step:** None

**2. Task Card**
- **Type:** Read-only display
- **Data Source:** 
  - Backend: Task metadata
  - Smart Contract: `HealChainEscrow.escrowBalance(taskID)`
- **Triggered Algorithm Step:** None
- **Click Action:** Navigate to `/tasks/[taskID]`

### UI State Mapping:

- **Status Badge** → Backend `task.status` (Prisma enum)
- **Escrow Balance** → Smart Contract `HealChainEscrow.escrowBalance(taskID)`
- **Miners Count** → Backend `task._count.miners`
- **Deadline** → Backend `task.deadline` (converted from BigInt)

### Allowed Actions:
- ✅ Filter tasks by status
- ✅ Filter tasks by publisher
- ✅ Sort tasks
- ✅ Navigate to task detail page
- ✅ Navigate to publish page (Publisher role)

### Forbidden Actions:
- ❌ Edit task details (immutable after M1)
- ❌ Delete tasks (immutable)
- ❌ Modify escrow balance (contract-controlled)

---

## PAGE: /tasks/[taskId]

**Protocol Modules:**
- M1 (Task Publishing)
- M2 (Miner Registration)
- M3 (Training Status - Read-Only)
- M4 (Aggregation Status - Read-Only)
- M5 (Verification Status - Read-Only)
- M6 (Block Publishing Status)
- M7 (Reveal & Rewards)

**Visible Roles:**
- Publisher (full access)
- Miner (participant view)
- Observer (read-only)

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Task ID: task_001                                           │
│ - Status Badge: [OPEN]                                       │
│ - Back Button → /tasks                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TASK METADATA PANEL (Read-Only)                              │
│ - Publisher: 0x1234...5678                                   │
│ - Reward: 1.5 ETH                                            │
│ - Required Accuracy: 85.5%                                   │
│ - Deadline: 2026-01-10 12:00 UTC                             │
│ - Created: 2026-01-01 10:00 UTC                             │
│ - Dataset: chestxray                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PROTOCOL PHASE TIMELINE (Read-Only)                          │
│                                                               │
│ [M1] Task Published          ✅ Completed                    │
│   └─ Escrow: 1.5 ETH (Locked)                               │
│   └─ Commit Hash: 0xabc...def                               │
│                                                               │
│ [M2] Miner Registration      🔄 In Progress                 │
│   └─ Registered: 3/5 miners                                   │
│   └─ [Register as Miner] Button (Miner only)                │
│                                                               │
│ [M3] Training Phase           ⏳ Pending                     │
│   └─ Status: Waiting for miners                             │
│   └─ Note: Training happens off-chain (FL-client)            │
│                                                               │
│ [M4] Aggregation             ⏳ Pending                      │
│   └─ Status: Waiting for training completion                 │
│   └─ Note: Aggregation happens off-chain (aggregator)        │
│                                                               │
│ [M5] Verification            ⏳ Pending                      │
│   └─ Status: Waiting for aggregation                        │
│   └─ Note: Consensus happens off-chain (aggregator)         │
│                                                               │
│ [M6] Block Publishing        ⏳ Pending                      │
│   └─ Status: Waiting for verification                       │
│   └─ [Publish Block] Button (Publisher only, when ready)    │
│                                                               │
│ [M7] Reveal & Rewards        ⏳ Pending                      │
│   └─ Status: Waiting for block publishing                    │
│   └─ [Reveal Accuracy] Button (Publisher, when M6 done)     │
│   └─ [Reveal Score] Button (Miner, when M7a done)           │
│   └─ [Distribute Rewards] Button (Publisher, when M7b done)│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BLOCKCHAIN STATE PANEL (Read-Only)                           │
│ - Escrow Balance: 1.5 ETH (from contract)                     │
│ - Task Status: LOCKED (from contract)                        │
│ - Accuracy Commit: 0xabc...def (from contract)              │
│ - Model Hash: 0x000...000 (from contract, if M6 done)       │
│ - Accuracy: 0 (from contract, if M6 done)                    │
│ - Block Hash: 0x000...000 (from BlockPublisher, if M6 done) │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PARTICIPANTS PANEL (Read-Only)                                │
│ - Registered Miners: 3                                        │
│   └─ 0x1111...1111 (Registered: 2026-01-02 10:00)           │
│   └─ 0x2222...2222 (Registered: 2026-01-02 11:00)            │
│   └─ 0x3333...3333 (Registered: 2026-01-02 12:00)           │
│ - Aggregator: Not selected yet                              │
│ - Score Reveals: 0/3 (if M7 active)                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ACTION PANEL (Role-Based, Protocol-Aligned)                  │
│                                                               │
│ IF Publisher:                                                │
│   - [Publish Block] (M6, when M5 consensus passed)          │
│   - [Reveal Accuracy] (M7a, when M6 published)               │
│   - [Distribute Rewards] (M7c, when M7b complete)           │
│                                                               │
│ IF Miner (not registered):                                    │
│   - [Register as Miner] (M2)                                 │
│                                                               │
│ IF Miner (registered):                                        │
│   - [Reveal Score] (M7b, when M7a done)                       │
│                                                               │
│ IF Observer:                                                  │
│   - No actions (read-only)                                    │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Task Metadata Panel**
- **Type:** Read-only
- **Data Source:** Backend `GET /tasks/[taskID]`
- **Triggered Algorithm Step:** None

**2. Protocol Phase Timeline**
- **Type:** Read-only status display + conditional action buttons
- **Data Source:** 
  - Backend: Task status, miner count
  - Smart Contract: `HealChainEscrow.tasks(taskID)`
  - Aggregator: Status (read-only via backend)
- **Triggered Algorithm Step:** 
  - M2: Miner registration → Backend `POST /miners/register`
  - M6: Block publishing → Smart Contract `BlockPublisher.publishBlock()`
  - M7a: Accuracy reveal → Smart Contract `RewardDistribution.revealAccuracy()`
  - M7b: Score reveal → Smart Contract `RewardDistribution.revealScore()`
  - M7c: Reward distribution → Smart Contract `RewardDistribution.distribute()`

**3. Blockchain State Panel**
- **Type:** Read-only
- **Data Source:** 
  - `HealChainEscrow.escrowBalance(taskID)`
  - `HealChainEscrow.tasks(taskID)`
  - `BlockPublisher.publishedBlocks(taskID)`
- **Triggered Algorithm Step:** None

**4. Participants Panel**
- **Type:** Read-only
- **Data Source:** Backend `GET /tasks/[taskID]` (includes miners)
- **Triggered Algorithm Step:** None

**5. Action Panel**
- **Type:** Conditional action buttons (protocol-aligned)
- **Data Source:** User role + task status
- **Triggered Algorithm Step:** See Protocol Phase Timeline

### UI State Mapping:

- **"M1 Completed"** → Contract: `tasks[taskID].status == LOCKED` AND `escrowBalance[taskID] > 0`
- **"M2 In Progress"** → Backend: `task.status == OPEN` AND `miners.length < requiredMiners`
- **"M2 Complete"** → Backend: `task.status == OPEN` AND `miners.length >= requiredMiners`
- **"M3 Pending"** → Backend: `task.status == OPEN` AND training not started (FL-client handles)
- **"M4 Pending"** → Aggregator: No candidate block yet (read via backend)
- **"M5 Pending"** → Aggregator: No consensus result yet (read via backend)
- **"M5 Consensus Passed"** → Aggregator: `consensus == APPROVED` (read via backend)
- **"M6 Ready"** → Aggregator: `consensus == APPROVED` AND contract: `tasks[taskID].status == LOCKED`
- **"M6 Published"** → Contract: `BlockPublisher.publishedBlocks(taskID).timestamp > 0`
- **"M7a Ready"** → Contract: `BlockPublisher.publishedBlocks(taskID).timestamp > 0`
- **"M7a Done"** → Contract: `RewardDistribution.accuracyRevealed(taskID) == true`
- **"M7b Ready"** → Contract: `accuracyRevealed(taskID) == true`
- **"M7b Complete"** → Contract: All registered miners have `minerReveals[taskID][miner].revealed == true`
- **"M7c Ready"** → Contract: `accuracyRevealed(taskID) == true` AND all miners revealed

### Allowed Actions:

**Publisher:**
- ✅ Publish Block (M6) → When M5 consensus passed
- ✅ Reveal Accuracy (M7a) → When M6 published
- ✅ Distribute Rewards (M7c) → When M7b complete

**Miner (not registered):**
- ✅ Register as Miner (M2) → When `task.status == OPEN`

**Miner (registered):**
- ✅ Reveal Score (M7b) → When M7a done

**Observer:**
- ✅ View all information (read-only)

### Forbidden Actions:

- ❌ Start Training (M3) → Training happens in FL-client (off-chain)
- ❌ Submit Gradients (M3) → FL-client handles this
- ❌ Trigger Aggregation (M4) → Aggregator is autonomous
- ❌ Trigger Verification (M5) → Aggregator handles consensus
- ❌ Modify Task Details → Immutable after M1
- ❌ Publish Block before M5 consensus → Protocol violation
- ❌ Reveal Accuracy before M6 published → Protocol violation
- ❌ Reveal Score before M7a → Protocol violation
- ❌ Distribute Rewards before M7b complete → Protocol violation

---

## PAGE: /publish

**Protocol Modules:**
- M1 (Task Publishing ONLY)

**Visible Roles:**
- Publisher (only)

**Access Control:**
- Redirect to `/dashboard` if not Publisher role or wallet not connected

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Page Title: "Publish New Task"                            │
│ - Back Button → /dashboard                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PROTOCOL INFORMATION PANEL (Read-Only)                       │
│ - Module: M1 - Task Publishing                              │
│ - Steps:                                                     │
│   1. Fill task details                                      │
│   2. Generate commit hash (accuracy + nonce)                │
│   3. Create task in backend                                 │
│   4. Submit transaction to escrow (smart contract)         │
│ - Note: Miners can register after escrow is locked         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PUBLISH TASK FORM (Interactive)                              │
│                                                               │
│ Task ID: [text input]                                        │
│   └─ Validation: Unique, alphanumeric                        │
│                                                               │
│ Required Accuracy (%): [number input]                       │
│   └─ Validation: 0 < accuracy <= 100                        │
│   └─ Note: This will be committed (commit-reveal)           │
│                                                               │
│ Reward (ETH): [number input]                                │
│   └─ Validation: > 0                                         │
│   └─ Note: This will be locked in escrow                    │
│                                                               │
│ Deadline: [datetime picker]                                 │
│   └─ Validation: Future date                                │
│   └─ Note: Miners must register before deadline             │
│                                                               │
│ Description (Optional): [textarea]                           │
│   └─ Note: For display only, not stored on-chain            │
│                                                               │
│ [Publish Task] Button                                       │
│   └─ Triggers: Backend create → Contract escrow            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TRANSACTION MODAL (Conditional)                              │
│ - Shows when transaction is pending                         │
│ - Displays: Transaction hash, status                        │
│ - Closes on success → Navigate to /tasks/[taskID]           │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Protocol Information Panel**
- **Type:** Read-only (educational)
- **Data Source:** Static content
- **Triggered Algorithm Step:** None

**2. Publish Task Form**
- **Type:** Interactive form
- **Data Source:** User input
- **Triggered Algorithm Step:** 
  - M1 Step 1: Generate commit hash (frontend generates nonce, computes hash)
  - M1 Step 2: Backend `POST /tasks/create` (with commit hash)
  - M1 Step 3: Smart Contract `HealChainEscrow.publishTask()` (with ETH value)

**3. Transaction Modal**
- **Type:** Transaction status display
- **Data Source:** Transaction receipt from wagmi
- **Triggered Algorithm Step:** None (observational)

### UI State Mapping:

- **"Form Valid"** → All inputs pass validation
- **"Transaction Pending"** → `useWaitForTransactionReceipt.isPending == true`
- **"Transaction Confirmed"** → `useWaitForTransactionReceipt.isSuccess == true`
- **"Task Created"** → Backend returns `taskID` AND contract emits `TaskCreated` event

### Allowed Actions:

- ✅ Fill form fields
- ✅ Submit form (triggers M1 protocol)
- ✅ View transaction status
- ✅ Navigate to created task detail page

### Forbidden Actions:

- ❌ Modify task after publishing (immutable)
- ❌ Cancel escrow deposit (contract-controlled)
- ❌ Skip commit hash generation (protocol requirement)
- ❌ Publish without wallet connection (authentication required)

---

## PAGE: /mining

**Protocol Modules:**
- M2 (Miner Registration)
- M3 (Training Status - Read-Only)
- M4 (Aggregation Status - Read-Only)
- M5 (Verification Status - Read-Only)

**Visible Roles:**
- Miner (primary)
- Observer (read-only)

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Page Title: "Mining Dashboard"                            │
│ - Wallet Address Display                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MY PARTICIPATIONS PANEL (Miner Only)                         │
│ - Tasks I'm Registered For: 2                               │
│   └─ task_001: Status [TRAINING] → View Details             │
│   └─ task_002: Status [AGGREGATING] → View Details          │
│ - Tasks I Can Register For: 3                               │
│   └─ task_003: [Register] Button                            │
│   └─ task_004: [Register] Button                            │
│   └─ task_005: [Register] Button                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AVAILABLE TASKS PANEL (Read-Only)                            │
│ - Filter: [All | Open for Registration]                    │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task Card                                            │     │
│ │ - Task ID: task_003                                  │     │
│ │ - Status: OPEN                                       │     │
│ │ - Reward: 2.0 ETH                                    │     │
│ │ - Required Accuracy: 90%                            │     │
│ │ - Deadline: 2026-01-15 12:00 UTC                    │     │
│ │ - Registered Miners: 2/5                            │     │
│ │ - [Register as Miner] Button (M2)                   │     │
│ │ - [View Details] Link → /tasks/task_003            │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ [Repeat for each available task]                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TRAINING STATUS PANEL (Read-Only, for Registered Tasks)     │
│ - Note: Training happens in FL-client (off-chain)            │
│ - Status: Waiting for FL-client to start                    │
│ - No UI actions available                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AGGREGATION STATUS PANEL (Read-Only)                         │
│ - Note: Aggregation happens in aggregator (off-chain)      │
│ - Status: Waiting for training completion                   │
│ - No UI actions available                                    │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. My Participations Panel**
- **Type:** Read-only list + action buttons
- **Data Source:** Backend `GET /tasks?miner=walletAddress`
- **Triggered Algorithm Step:** None (display only)

**2. Available Tasks Panel**
- **Type:** Read-only list + action buttons
- **Data Source:** Backend `GET /tasks?status=OPEN`
- **Triggered Algorithm Step:** 
  - M2: Miner Registration → Backend `POST /miners/register`

**3. Training Status Panel**
- **Type:** Read-only
- **Data Source:** Backend task status
- **Triggered Algorithm Step:** None (FL-client handles training)

**4. Aggregation Status Panel**
- **Type:** Read-only
- **Data Source:** Aggregator status (via backend)
- **Triggered Algorithm Step:** None (aggregator is autonomous)

### UI State Mapping:

- **"Open for Registration"** → Backend: `task.status == OPEN` AND `deadline > now`
- **"Registered"** → Backend: `task.miners.contains(walletAddress)`
- **"Training In Progress"** → Backend: `task.status == AGGREGATING` (aggregator active)
- **"Aggregation Complete"** → Aggregator: Candidate block exists (read via backend)

### Allowed Actions:

- ✅ Register as Miner (M2) → When task is OPEN and not registered
- ✅ View task details
- ✅ View training status (read-only)
- ✅ View aggregation status (read-only)

### Forbidden Actions:

- ❌ Start Training (M3) → FL-client handles this (off-chain)
- ❌ Submit Gradients (M3) → FL-client handles this (off-chain)
- ❌ Trigger Aggregation (M4) → Aggregator is autonomous
- ❌ Verify Block (M5) → Aggregator handles consensus
- ❌ Unregister as Miner → Immutable after M2

---

## PAGE: /rewards

**Protocol Modules:**
- M7 (Commit-Reveal & Reward Distribution)

**Visible Roles:**
- Publisher (M7a, M7c)
- Miner (M7b)
- Observer (read-only)

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Page Title: "Rewards & Reveals"                           │
│ - Role Badge: [Publisher | Miner | Observer]                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PROTOCOL INFORMATION PANEL (Read-Only)                       │
│ - Module: M7 - Commit-Reveal & Rewards                      │
│ - Steps:                                                     │
│   1. Publisher reveals accuracy (M7a)                        │
│   2. Miners reveal scores (M7b)                             │
│   3. Publisher distributes rewards (M7c)                     │
│ - Note: All reveals must match commits from M1/M3           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MY TASKS - PUBLISHER VIEW (Publisher Only)                   │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task: task_001                                       │     │
│ │ - Status: AWAITING_REVEAL                            │     │
│ │ - Escrow: 1.5 ETH                                    │     │
│ │ - Accuracy Commit: 0xabc...def                       │     │
│ │ - Block Published: ✅ (M6 complete)                  │     │
│ │                                                       │     │
│ │ [Reveal Accuracy] Button (M7a)                       │     │
│ │   └─ Opens form: Accuracy value, Nonce                │     │
│ │                                                       │     │
│ │ OR (if M7a done):                                    │     │
│ │ - Accuracy Revealed: 85.5%                            │     │
│ │ - Miners Revealed: 2/3                               │     │
│ │ - [Distribute Rewards] Button (M7c)                  │     │
│ │   └─ Triggers: RewardDistribution.distribute()    │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ [Repeat for each task awaiting reveal]                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MY PARTICIPATIONS - MINER VIEW (Miner Only)                  │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task: task_001                                       │     │
│ │ - Status: REVEAL_OPEN                                │     │
│ │ - Publisher Revealed: ✅ (Accuracy: 85.5%)          │     │
│ │ - My Score Commit: 0xdef...abc                       │     │
│ │ - My Score Revealed: ❌ Not yet                      │     │
│ │                                                       │     │
│ │ [Reveal Score] Button (M7b)                          │     │
│ │   └─ Opens form: Score value, Nonce                  │     │
│ │                                                       │     │
│ │ OR (if revealed):                                    │     │
│ │ - My Score Revealed: ✅ (Score: 150.25)              │     │
│ │ - My Reward Share: 0.5 ETH (pending distribution)    │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ [Repeat for each task where miner participated]             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ REWARD DISTRIBUTION STATUS (Read-Only)                      │
│ - Total Distributed: 5.2 ETH                                │
│ - Pending Distribution: 2.1 ETH                             │
│ - My Total Rewards: 1.5 ETH                                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Protocol Information Panel**
- **Type:** Read-only (educational)
- **Data Source:** Static content
- **Triggered Algorithm Step:** None

**2. Publisher View - Reveal Accuracy Form**
- **Type:** Interactive form
- **Data Source:** User input (accuracy, nonce from M1)
- **Triggered Algorithm Step:** 
  - M7a: `RewardDistribution.revealAccuracy(taskID, accuracy, nonce, commitHash)`

**3. Publisher View - Distribute Rewards Button**
- **Type:** Action button
- **Data Source:** Contract state
- **Triggered Algorithm Step:** 
  - M7c: `RewardDistribution.distribute(taskID, miners[])`

**4. Miner View - Reveal Score Form**
- **Type:** Interactive form
- **Data Source:** User input (score, nonce from M3)
- **Triggered Algorithm Step:** 
  - M7b: `RewardDistribution.revealScore(taskID, score, nonce, scoreCommit)`

**5. Reward Distribution Status**
- **Type:** Read-only
- **Data Source:** 
  - Contract: `RewardDistribution.rewardsDistributed(taskID)`
  - Contract: `HealChainEscrow.escrowBalance(taskID)`

### UI State Mapping:

- **"M7a Ready"** → Contract: `BlockPublisher.publishedBlocks(taskID).timestamp > 0` AND `RewardDistribution.accuracyRevealed(taskID) == false`
- **"M7a Done"** → Contract: `RewardDistribution.accuracyRevealed(taskID) == true`
- **"M7b Ready"** → Contract: `accuracyRevealed(taskID) == true` AND `minerReveals[taskID][miner].revealed == false`
- **"M7b Done"** → Contract: `minerReveals[taskID][miner].revealed == true`
- **"M7c Ready"** → Contract: `accuracyRevealed(taskID) == true` AND all miners revealed AND `rewardsDistributed(taskID) == false`
- **"M7c Done"** → Contract: `rewardsDistributed(taskID) == true`

### Allowed Actions:

**Publisher:**
- ✅ Reveal Accuracy (M7a) → When M6 published
- ✅ Distribute Rewards (M7c) → When M7b complete

**Miner:**
- ✅ Reveal Score (M7b) → When M7a done

**Observer:**
- ✅ View all information (read-only)

### Forbidden Actions:

- ❌ Reveal Accuracy before M6 published → Protocol violation
- ❌ Reveal Score before M7a → Protocol violation
- ❌ Distribute Rewards before M7b complete → Protocol violation
- ❌ Modify commit values → Immutable (from M1/M3)
- ❌ Reveal incorrect values → Contract will reject (commit-reveal mismatch)

---

## PAGE: /aggregator

**Protocol Modules:**
- M4 (Secure Aggregation - Read-Only)
- M5 (Miner Consensus - Read-Only)
- M6 (Block Publishing Status - Read-Only)

**Visible Roles:**
- Publisher
- Miner
- Observer

**Note:** This page is READ-ONLY. Aggregator is autonomous and off-chain.

---

### Wireframe Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ - Page Title: "Aggregator Status"                           │
│ - Note: Read-Only Transparency View                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AGGREGATOR INFORMATION PANEL (Read-Only)                    │
│ - Status: Active / Inactive                                 │
│ - Current Tasks: 3                                          │
│ - Note: Aggregator is autonomous and off-chain             │
│ - No UI actions available                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TASK AGGREGATION STATUS (Read-Only)                         │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task: task_001                                       │     │
│ │ - Status: AGGREGATING                                 │     │
│ │ - Round: 2/5                                         │     │
│ │ - Gradients Collected: 3/3                           │     │
│ │ - Aggregation: In Progress                           │     │
│ │ - Current Accuracy: 82.5%                            │     │
│ │ - Required Accuracy: 85.0%                            │     │
│ │ - Next Action: Retrain (Round 3)                     │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Task: task_002                                       │     │
│ │ - Status: VERIFIED                                    │     │
│ │ - Round: 5/5                                         │     │
│ │ - Final Accuracy: 87.2%                              │     │
│ │ - Consensus: APPROVED (3/3 miners)                    │     │
│ │ - Candidate Block: Ready for M6                       │     │
│ │   └─ Model Hash: 0x123...abc                          │     │
│ │   └─ Accuracy: 87.2%                                  │     │
│ │   └─ Score Commits: [0xabc..., 0xdef..., 0xghi...]   │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ [Repeat for each task in aggregation]                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CONSENSUS DETAILS (Read-Only)                               │
│ - Task: task_002                                            │
│ - Miners Verified: 3/3                                      │
│   └─ 0x1111...1111: VALID                                   │
│   └─ 0x2222...2222: VALID                                   │
│   └─ 0x3333...3333: VALID                                   │
│ - Consensus Result: APPROVED                                │
│ - Majority Required: 2/3                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BLOCK PUBLISHING STATUS (Read-Only)                          │
│ - Task: task_002                                            │
│ - Candidate Block Status: Ready                              │
│ - On-Chain Status: Not Published                            │
│ - Note: Publisher must call M6 to publish on-chain         │
└─────────────────────────────────────────────────────────────┘
```

### Component Details:

**1. Aggregator Information Panel**
- **Type:** Read-only
- **Data Source:** Aggregator status (via backend)
- **Triggered Algorithm Step:** None

**2. Task Aggregation Status**
- **Type:** Read-only
- **Data Source:** Aggregator state (via backend)
- **Triggered Algorithm Step:** None

**3. Consensus Details**
- **Type:** Read-only
- **Data Source:** Aggregator consensus results (via backend)
- **Triggered Algorithm Step:** None

**4. Block Publishing Status**
- **Type:** Read-only
- **Data Source:** 
  - Aggregator: Candidate block (via backend)
  - Contract: `BlockPublisher.publishedBlocks(taskID)`
- **Triggered Algorithm Step:** None

### UI State Mapping:

- **"Aggregating"** → Aggregator: Task in M4 phase
- **"Consensus Pending"** → Aggregator: M5 verification in progress
- **"Consensus Approved"** → Aggregator: `consensus == APPROVED`
- **"Candidate Block Ready"** → Aggregator: Candidate block exists AND consensus approved
- **"Block Published On-Chain"** → Contract: `BlockPublisher.publishedBlocks(taskID).timestamp > 0`

### Allowed Actions:

- ✅ View aggregation status (read-only)
- ✅ View consensus details (read-only)
- ✅ View candidate blocks (read-only)
- ✅ Navigate to task detail page

### Forbidden Actions:

- ❌ Trigger aggregation → Aggregator is autonomous
- ❌ Modify aggregation results → Aggregator-controlled
- ❌ Force consensus → Aggregator handles M5
- ❌ Publish block from this page → Must use /tasks/[taskID] (M6)

---

## 🎯 CROSS-PAGE CONSISTENCY RULES

### Status Badge Mapping (All Pages)

| Backend Status | Contract Status | Display Badge | Protocol Phase |
|----------------|-----------------|---------------|----------------|
| CREATED        | CREATED         | Created       | M1 (pre-escrow) |
| CREATED        | LOCKED          | Escrow Locked | M1 (post-escrow) |
| OPEN           | LOCKED          | Open          | M2 (miner registration) |
| COMMIT_CLOSED  | LOCKED          | Commit Closed | M2 (deadline passed) |
| AGGREGATING    | LOCKED          | Aggregating   | M4 (aggregator active) |
| VERIFIED       | LOCKED          | Verified      | M5 (consensus passed) |
| REVEAL_OPEN    | AWAITING_REVEAL | Reveal Open   | M7a (ready) |
| REVEAL_CLOSED  | AWAITING_REVEAL | Reveal Closed | M7b (in progress) |
| REWARDED       | COMPLETED       | Rewarded      | M7c (complete) |
| CANCELLED      | FAILED          | Cancelled     | Failed |

### Data Source Priority

1. **Smart Contract** (highest priority) - For escrow, task status, reveals, rewards
2. **Backend** (secondary) - For task metadata, miner lists, aggregator status
3. **Aggregator** (read-only) - For M4-M6 status (via backend relay)

### Update Frequency

- **Contract State:** Poll every 5 seconds (wagmi polling)
- **Backend State:** Poll every 5 seconds (useTask hook)
- **Aggregator State:** Poll every 10 seconds (via backend)

---

## ⚠️ CRITICAL PROHIBITIONS (REPEATED FOR CLARITY)

❌ **No "Start Training" buttons** → Training happens in FL-client (off-chain)  
❌ **No "Compute Score" UI** → Scoring happens in FL-client (off-chain)  
❌ **No "Upload Gradient" UI** → Gradient submission happens in FL-client (off-chain)  
❌ **No client-side hashing or cryptography** → All crypto in FL-client, aggregator, or contracts  
❌ **No backend write assumptions** → Backend is read-only relay  
❌ **No speculative states** → Only display confirmed blockchain/backend state  
❌ **No optimistic UI beyond confirmed state** → Wait for transaction confirmations  

---

## 📋 IMPLEMENTATION CHECKLIST

For each page, verify:

- [ ] All UI states map to explicit protocol steps
- [ ] All actions correspond to smart contract functions or backend reads
- [ ] No forbidden actions are present
- [ ] Role-based access is enforced
- [ ] Data sources are correctly prioritized (contract > backend > aggregator)
- [ ] Status badges match protocol phases
- [ ] Transaction modals show proper states
- [ ] Error handling is protocol-aware
- [ ] No crypto operations in frontend
- [ ] No training/aggregation triggers in UI

---

**END OF SPECIFICATION**

