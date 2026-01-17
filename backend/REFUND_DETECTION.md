# Refund Detection Service

## Overview

The Refund Detection Service automatically detects when tasks are refunded on-chain and updates the backend task status to `CANCELLED`. This implements the refund mechanism described in **BTP Report Chapter 4, Module 1**.

## How It Works

### On-Chain Refund Process

According to the BTP Report and smart contract implementation:

1. **Task Publisher** calls `refundPublisher(taskID)` after deadline passes
2. **Smart Contract** (`HealChainEscrow.sol`):
   - Verifies deadline has passed
   - Verifies task is not already completed
   - Sets on-chain status to `TaskStatus.FAILED` (enum value 5)
   - Refunds escrow balance to publisher
   - Emits `TaskFailed(taskID)` event

### Backend Detection

The `refundDetectionService.ts` checks for refunded tasks by:

1. **Reading On-Chain Status**: Queries the smart contract's `tasks(taskID)` mapping
2. **Checking Escrow Balance**: Verifies `escrowBalance(taskID)` is 0
3. **Validating Deadline**: Ensures deadline has passed
4. **Updating Status**: Sets backend status to `CANCELLED`

## Status Mapping

| On-Chain Status | Enum Value | Escrow Balance | Backend Status | Meaning |
|----------------|------------|----------------|----------------|---------|
| `CREATED` | 0 | Any | `CREATED` | Task created |
| `LOCKED` | 1 | > 0 | `OPEN` | Escrow locked |
| `PUBLISHED` | 2 | > 0 | Various | Block published |
| `AWAITING_REVEAL` | 3 | > 0 | `REVEAL_OPEN` | Awaiting reveal |
| `COMPLETED` | 4 | 0 | `REWARDED` | **Task completed (rewards distributed)** |
| `FAILED` | 5 | 0 | `CANCELLED` | **Task refunded** |
| `LOCKED/PUBLISHED/AWAITING_REVEAL` | 1-3 | 0 (after deadline) | `CANCELLED` | **Implicit refund (escrow emptied but not completed)** |

## Automatic Detection

The refund detection is integrated into the **Task Status Scheduler** and runs every 60 seconds:

```typescript
// In taskScheduler.ts
async function runSchedulerCycle() {
  // ... other checks ...
  
  // 5. Check for refunded tasks (any status → CANCELLED)
  await checkRefundedTasks();
}
```

## Manual Detection

### Check All Tasks

```bash
POST /tasks/check-refunds
```

**Response:**
```json
{
  "updated": true,
  "count": 1
}
```

### Check Specific Task

```bash
POST /tasks/:taskID/check-refund
```

**Response:**
```json
{
  "taskID": "task_017",
  "isRefunded": true,
  "onChainStatus": 5,
  "escrowBalance": "0",
  "backendStatus": "CANCELLED",
  "message": "Task was refunded on-chain. Status updated to CANCELLED."
}
```

## Implementation Details

### Detection Logic

A task is considered refunded if **either**:

1. **On-chain status is FAILED** (`onChainStatus === 5`) - Explicit refund
2. **Escrow balance is 0 AND deadline has passed AND status is NOT COMPLETED** - Implicit refund

**Important**: Tasks with `COMPLETED` status (enum 4) and zero escrow balance are **NOT** considered refunded - they had rewards successfully distributed.

```typescript
const isFailed = onChainStatus === 5; // FAILED status (explicit refund)
const isCompleted = onChainStatus === 4; // COMPLETED status (rewards distributed)
const isRefunded = escrowBalance === 0n && deadlinePassed && !isCompleted;
```

### Distinguishing Refund vs Reward Distribution

| Scenario | On-Chain Status | Escrow Balance | Backend Action |
|----------|----------------|----------------|----------------|
| **Reward Distribution** | `COMPLETED` (4) | 0 | Update to `REWARDED` (handled by `checkRewardStatus`) |
| **Explicit Refund** | `FAILED` (5) | 0 | Update to `CANCELLED` |
| **Implicit Refund** | `LOCKED/PUBLISHED/AWAITING_REVEAL` (1-3) | 0 (after deadline) | Update to `CANCELLED` |

### Error Handling

- **Task Not Found**: Tasks that don't exist on-chain are silently skipped (normal for test tasks or failed escrow transactions)
- **Filtering**: Only tasks with `publishTx` (actually published on-chain) are checked
- **Error Detection**: Specifically detects `BAD_DATA` errors with `value="0x"` as "task not found"
- **Logging**: Only unexpected errors are logged as warnings
- **RPC Errors**: RPC errors are logged but don't stop the scheduler
- **Individual Errors**: Individual task errors don't prevent checking other tasks

### Expected Behavior

The service will skip tasks that:
- Don't have a `publishTx` (never published on-chain)
- Return `BAD_DATA` error when reading from contract (task doesn't exist)
- Are test tasks or tasks where escrow transaction failed

These are **expected cases** and won't generate warnings in logs.

## BTP Report Compliance

This implementation aligns with **Chapter 4, Module 1** of the BTP Report:

> "Safety: refund if task never completes"
> 
> The escrow mechanism allows the Task Publisher to refund their deposit if the task deadline passes without successful completion. This protects the publisher from scenarios where miners fail to complete the task.

### Key Points:

1. ✅ **Refund Detection**: Automatically detects when `refundPublisher()` is called
2. ✅ **Status Update**: Updates backend to `CANCELLED` to reflect refund state
3. ✅ **Deadline Validation**: Only considers refunds valid after deadline passes
4. ✅ **On-Chain Verification**: Reads directly from smart contract for accuracy

## Logging

All refund detections are logged:

```
[RefundDetection] Updated task task_017: OPEN → CANCELLED (refund detected on-chain)
```

## Testing

To test refund detection:

1. **Create a task** with a past deadline
2. **Call refund** on-chain: `refundPublisher(taskID)`
3. **Wait for scheduler** (60 seconds) or **manually trigger**:
   ```bash
   curl -X POST http://localhost:3000/tasks/check-refunds
   ```
4. **Verify status** updated to `CANCELLED`

## Notes

- Refund detection runs automatically every 60 seconds
- Manual checks are available via API endpoints
- Status updates are idempotent (safe to run multiple times)
- Only active tasks (not already CANCELLED or REWARDED) are checked
