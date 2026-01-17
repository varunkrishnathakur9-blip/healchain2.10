# Task Status Scheduler Implementation

## Overview

The Task Status Scheduler automatically updates task statuses based on deadlines, consensus, and reward distribution. It runs periodically (every 60 seconds) to ensure tasks progress through their lifecycle without manual intervention.

## Features

### ✅ Automatic Status Updates

1. **Deadline-Based Updates**
   - `CREATED` → `OPEN` (when main deadline passes)
   - `OPEN` → `COMMIT_CLOSED` (when main deadline passes)
   - `REVEAL_OPEN` → `REVEAL_CLOSED` (when reveal deadline passes - 7 days after main deadline)

2. **Consensus-Based Updates**
   - `REVEAL_OPEN` → `VERIFIED` (when 50% majority of miners vote VALID)

3. **Reward-Based Updates**
   - `VERIFIED` → `REWARDED` (when all miners have distributed rewards)

4. **Refund Detection**
   - Any status → `CANCELLED` (when task is refunded on-chain after deadline)

## Implementation Details

### Scheduler Service (`taskScheduler.ts`)

- **Interval**: Runs every 60 seconds
- **Startup**: Begins automatically when backend starts
- **Graceful Shutdown**: Stops cleanly on SIGTERM/SIGINT

### Status Update Functions (`taskService.ts`)

#### `checkTaskDeadlines()`
- Updates `CREATED` → `OPEN` when deadline passes
- Updates `OPEN` → `COMMIT_CLOSED` when deadline passes

#### `checkRevealDeadlines()`
- Calculates reveal deadline as: `main deadline + 7 days`
- Updates `REVEAL_OPEN` → `REVEAL_CLOSED` when reveal deadline passes

#### `checkConsensusAndUpdate()`
- Checks all `REVEAL_OPEN` tasks with blocks
- Calculates consensus: `valid_votes ≥ (50% × total_miners)`
- Updates to `VERIFIED` when consensus reached

#### `checkRewardStatus()`
- Checks all `VERIFIED` tasks
- Verifies all miners have rewards with status `DISTRIBUTED`
- Updates to `REWARDED` when all rewards distributed

#### `checkRefundedTasks()` (from `refundDetectionService.ts`)
- Checks all active tasks (not CANCELLED or REWARDED)
- Reads on-chain task status from smart contract
- Updates to `CANCELLED` when:
  - On-chain status is `FAILED` (enum value 5), OR
  - Escrow balance is 0 AND deadline has passed

## API Endpoints

### `GET /tasks/scheduler/status`
Get scheduler status and configuration.

**Response:**
```json
{
  "running": true,
  "interval": 60000,
  "revealDeadlineOffset": 604800
}
```

### `POST /tasks/check-deadlines`
Manually trigger deadline checking (still available for manual use).

### `POST /tasks/check-refunds`
Manually trigger refund detection for all tasks.

**Response:**
```json
{
  "updated": true,
  "count": 2
}
```

### `POST /tasks/:taskID/check-refund`
Check refund status for a specific task and update if refunded.

**Response:**
```json
{
  "taskID": "task_123",
  "isRefunded": true,
  "onChainStatus": 5,
  "escrowBalance": "0",
  "backendStatus": "CANCELLED",
  "message": "Task was refunded on-chain. Status updated to CANCELLED."
}
```

## Status Flow

```
CREATED → OPEN → COMMIT_CLOSED → REVEAL_OPEN → REVEAL_CLOSED → AGGREGATING → VERIFIED → REWARDED
    ↓         ↓              ↓              ↓               ↓            ↓          ↓
  Auto     Auto          Auto          Auto            Auto        Auto      Auto

Any Status → CANCELLED (when refunded on-chain)
    ↓
  Auto
```

## Configuration

- **Schedule Interval**: 60 seconds (configurable in `taskScheduler.ts`)
- **Reveal Deadline Offset**: 7 days (604800 seconds)
- **Consensus Threshold**: 50% majority

## Logging

The scheduler logs all status updates:
- `[TaskScheduler] Updated task {taskID}: {oldStatus} → {newStatus} (reason)`

## Testing

To test the scheduler:

1. **Check if running:**
   ```bash
   curl http://localhost:3000/tasks/scheduler/status
   ```

2. **Monitor logs:**
   Watch backend logs for `[TaskScheduler]` messages

3. **Manual trigger:**
   ```bash
   curl -X POST http://localhost:3000/tasks/check-deadlines
   ```

## Notes

- Scheduler starts automatically on backend startup
- First cycle runs 5 seconds after startup (to allow server to fully initialize)
- All updates are logged for debugging
- Scheduler handles errors gracefully and continues running
