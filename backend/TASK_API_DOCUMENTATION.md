# 🔧 HealChain Task API Documentation

## 📋 Overview

The HealChain Task API provides endpoints for managing federated learning tasks, including creation, status tracking, and miner participation. This API supports the complete task lifecycle from creation to reward distribution.

## 🚀 Base URL

```
http://localhost:3000/tasks
```

## 🎯 Endpoints

### 1. Create Task (M1)
**POST** `/tasks/create`

Creates a new federated learning task with commit hash.

**Request Body:**
```json
{
  "taskID": "task_123",
  "publisher": "0x1234567890123456789012345678901234567890",
  "accuracy": "1000000000000000000",
  "deadline": "1735699200",
  "message": "Task creation message",
  "signature": "0x..."
}
```

**Response:**
```json
{
  "taskID": "task_123",
  "commitHash": "0x...",
  "deadline": "1735699200"
}
```

**Status Codes:**
- `201` - Task created successfully
- `400` - Invalid input
- `409` - Task already exists

---

### 2. Get Open Tasks ⭐ **FL Client Endpoint**
**GET** `/tasks/open`

Retrieves all open tasks available for miner participation. This is the endpoint that FL clients poll.

**Response:**
```json
[
  {
    "taskID": "task_123",
    "publisher": "0x1234567890123456789012345678901234567890",
    "deadline": "1735699200",
    "status": "OPEN",
    "createdAt": "2025-01-01T00:00:00.000Z"
  },
  {
    "taskID": "task_124",
    "publisher": "0x0987654321098765432109876543210987654321",
    "deadline": "1735699300",
    "status": "OPEN",
    "createdAt": "2025-01-01T00:01:00.000Z"
  }
]
```

**Features:**
- ✅ Automatically updates task statuses based on deadlines
- ✅ Only returns tasks with `OPEN` status
- ✅ Filters out tasks past their deadline
- ✅ Ordered by creation date (newest first)

**Status Codes:**
- `200` - Success
- `500` - Server error

---

### 3. Get Task Details
**GET** `/tasks/:taskID`

Retrieves detailed information about a specific task.

**Parameters:**
- `taskID` (string) - Unique task identifier

**Response:**
```json
{
  "taskID": "task_123",
  "publisher": "0x1234567890123456789012345678901234567890",
  "commitHash": "0x...",
  "nonceTP": "abc123...",
  "deadline": "1735699200",
  "status": "OPEN",
  "publishTx": "0x...",
  "createdAt": "2025-01-01T00:00:00.000Z",
  "updatedAt": "2025-01-01T00:00:00.000Z",
  "miners": [
    {
      "address": "0x1111111111111111111111111111111111111111"
    },
    {
      "address": "0x2222222222222222222222222222222222222222"
    }
  ],
  "gradients": [
    {
      "minerAddress": "0x1111111111111111111111111111111111111111",
      "status": "COMMITTED"
    },
    {
      "minerAddress": "0x2222222222222222222222222222222222222222",
      "status": "REVEALED"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `404` - Task not found
- `500` - Server error

---

### 4. List All Tasks
**GET** `/tasks`

Retrieves all tasks with optional filtering and pagination.

**Query Parameters:**
- `status` (string, optional) - Filter by task status
- `publisher` (string, optional) - Filter by publisher address
- `limit` (number, optional) - Maximum number of tasks to return (default: 50)
- `offset` (number, optional) - Number of tasks to skip (default: 0)

**Examples:**
```
GET /tasks?status=OPEN&limit=10
GET /tasks?publisher=0x1234...&status=COMMIT_CLOSED
GET /tasks?limit=20&offset=40
```

**Response:**
```json
[
  {
    "taskID": "task_123",
    "publisher": "0x1234567890123456789012345678901234567890",
    "deadline": "1735699200",
    "status": "OPEN",
    "createdAt": "2025-01-01T00:00:00.000Z",
    "updatedAt": "2025-01-01T00:00:00.000Z",
    "_count": {
      "miners": 5,
      "gradients": 3
    }
  }
]
```

**Status Codes:**
- `200` - Success
- `400` - Invalid query parameters
- `500` - Server error

---

### 5. Update Task Status
**PUT** `/tasks/:taskID/status`

Updates the status of a specific task (admin only).

**Parameters:**
- `taskID` (string) - Unique task identifier

**Request Body:**
```json
{
  "status": "COMMIT_CLOSED",
  "message": "Status update message",
  "signature": "0x..."
}
```

**Response:**
```json
{
  "taskID": "task_123",
  "publisher": "0x1234567890123456789012345678901234567890",
  "commitHash": "0x...",
  "nonceTP": "abc123...",
  "deadline": "1735699200",
  "status": "COMMIT_CLOSED",
  "publishTx": "0x...",
  "createdAt": "2025-01-01T00:00:00.000Z",
  "updatedAt": "2025-01-01T00:05:00.000Z"
}
```

**Status Codes:**
- `200` - Status updated successfully
- `400` - Invalid input
- `404` - Task not found
- `401` - Unauthorized
- `500` - Server error

---

### 6. Check Task Deadlines
**POST** `/tasks/check-deadlines`

Manually triggers deadline checking and status updates for all tasks.

**Response:**
```json
{
  "updated": true
}
```

**Features:**
- ✅ Moves `CREATED` tasks to `OPEN` if deadline passed
- ✅ Moves `OPEN` tasks to `COMMIT_CLOSED` if deadline passed
- ✅ Automatically called by `/tasks/open` endpoint

**Status Codes:**
- `200` - Deadlines checked successfully
- `500` - Server error

---

## 🔄 Task Status Flow

```
CREATED → OPEN → COMMIT_CLOSED → REVEAL_OPEN → REVEAL_CLOSED → AGGREGATING → VERIFIED → REWARDED
    ↓         ↓              ↓              ↓               ↓            ↓          ↓
  Initial   Deadline    Commit         Reveal          Reveal       Aggregation  Rewards
           Passed       Deadline       Deadline        Deadline     Complete    Distributed
```

### Status Descriptions

| Status | Description | Trigger |
|--------|-------------|---------|
| `CREATED` | Task created, not yet open | Manual creation |
| `OPEN` | Task open for miner registration | Deadline passed |
| `COMMIT_CLOSED` | Commit phase closed | Commit deadline passed |
| `REVEAL_OPEN` | Reveal phase open | Manual trigger |
| `REVEAL_CLOSED` | Reveal phase closed | Reveal deadline passed |
| `AGGREGATING` | Aggregating gradients | Manual trigger |
| `VERIFIED` | Results verified | Verification complete |
| `REWARDED` | Rewards distributed | Reward distribution complete |
| `CANCELLED` | Task cancelled | Manual cancellation or refund detected |

---

## 🧪 FL Client Integration

### Example Usage

```python
import requests

# Get open tasks
response = requests.get("http://localhost:3000/tasks/open")
tasks = response.json()

for task in tasks:
    print(f"Task ID: {task['taskID']}")
    print(f"Publisher: {task['publisher']}")
    print(f"Deadline: {task['deadline']}")
    print(f"Status: {task['status']}")
    print("---")
```

### Expected Response for FL Client

```json
[
  {
    "taskID": "task_123",
    "publisher": "0x1234567890123456789012345678901234567890",
    "deadline": "1735699200",
    "status": "OPEN",
    "createdAt": "2025-01-01T00:00:00.000Z"
  }
]
```

---

## 🔒 Authentication

Most endpoints require wallet authentication using the `requireWalletAuth` middleware. The authentication process:

1. Client signs a message with their private key
2. Server verifies the signature using the provided address
3. Request is processed if authentication succeeds

**Required Fields for Authenticated Requests:**
- `message` - The message that was signed
- `signature` - The signature of the message

---

## 📊 Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "error": "Invalid input: taskID is required"
}
```

**404 Not Found:**
```json
{
  "error": "Task not found"
}
```

**409 Conflict:**
```json
{
  "error": "Task already exists"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error"
}
```

---

## 🚀 Testing the APIs

### 1. Start the Backend
```bash
cd backend
npm run dev
```

### 2. Test with curl
```bash
# Get open tasks
curl http://localhost:3000/tasks/open

# Create a task
curl -X POST http://localhost:3000/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "taskID": "test_task_1",
    "publisher": "0x1234567890123456789012345678901234567890",
    "accuracy": "1000000000000000000",
    "deadline": "1735699200",
    "message": "Test task creation",
    "signature": "0x..."
  }'

# Get task details
curl http://localhost:3000/tasks/test_task_1
```

### 3. Test with FL Client
```bash
cd fl_client
python scripts/start_client.py
```

---

## 📝 Notes

- All deadlines are Unix timestamps in seconds
- Blockchain addresses should be checksummed
- The `/tasks/open` endpoint automatically handles deadline updates
- Task status transitions are validated to prevent invalid state changes
- Pagination is supported for large task lists

---

**🎉 Your HealChain Task API is now complete and ready for FL client integration!**
