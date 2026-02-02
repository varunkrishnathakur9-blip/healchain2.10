# HealChain Distributed Deployment Guide

## Current Status

✅ **Good News**: The FL Client and Aggregator services are **already configured** for distributed deployment!

- **FL Client**: Binds to `0.0.0.0:5001` (accessible from other machines)
- **Aggregator**: Binds to `0.0.0.0:5002` (accessible from other machines)

## Deployment Architecture

```
┌─────────────────┐      ┌─────────────────┐
│   Machine A     │      │   Machine B     │
│                 │      │                 │
│  Backend:3000   │◄────►│  FL Client:5001 │
│  Frontend:3001  │      │                 │
│  Aggregator:5002│      └─────────────────┘
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   Machine C     │
│                 │
│  FL Client:5001 │
│                 │
└─────────────────┘
```

## Required Modifications

### 1. FL Client Configuration (Machine B, C)

**File**: `fl_client/.env`

```bash
# Replace localhost with the actual IP/hostname of Machine A
BACKEND_URL=http://192.168.1.10:3000   # Use Machine A's IP

# Blockchain endpoint (if using remote node)
RPC_URL=http://192.168.1.10:8545

# Miner credentials (unique per machine)
MINER_PRIVATE_KEY=0xYOUR_UNIQUE_PRIVATE_KEY
MINER_ADDRESS=0xYOUR_WALLET_ADDRESS

# Training parameters (same for all miners)
LOCAL_EPOCHS=1
DGC_THRESHOLD=0.9
```

### 2. Aggregator Configuration (Machine A)

**File**: `aggregator/.env`

Already configured correctly. No changes needed if running on same machine as Backend.

**Optional**: If running on a different machine:
```bash
BACKEND_URL=http://192.168.1.10:3000   # Machine A's IP
AGGREGATOR_PORT=5002
AGGREGATOR_HOST=0.0.0.0  # Already default
```

### 3. Backend Configuration (Machine A)

**File**: `backend/.env`

```bash
# Add these variables to support distributed FL clients
FL_CLIENT_SERVICE_URL=http://localhost:5001  # Not used for remote clients
AGGREGATOR_URL=http://localhost:5002         # Local aggregator

# If aggregator is on a different machine:
# AGGREGATOR_URL=http://192.168.1.11:5002
```

### 4. Frontend Configuration (Machine A)

**File**: `frontend/.env.local`

```bash
# Backend API (should be accessible from user's browser)
NEXT_PUBLIC_BACKEND_URL=http://192.168.1.10:3000

# Blockchain RPC (public endpoint or Machine A's IP)
NEXT_PUBLIC_RPC_URL=http://192.168.1.10:8545
```

## Network Requirements

### Firewall Rules

**Machine A (Backend + Aggregator)**:
- Open port `3000` (Backend API)
- Open port `3001` (Frontend - optional, only if accessing from other machines)
- Open port `5002` (Aggregator API)
- Open port `8545` (Blockchain RPC - if using local Ganache)

**Machine B, C (FL Clients)**:
- Open port `5001` (FL Client API - so backend can trigger training)
- **Important**: Backend needs to reach `http://<machine-b-ip>:5001/api/train`

### Network Discovery

The backend needs to know the URLs of FL client services. Two approaches:

**Option 1: Manual Registration** (Current)
- Miners manually call backend's `/miners/register` endpoint
- Backend stores the FL client service URL

**Option 2: Service Discovery** (Future Enhancement)
- Use a service registry (e.g., Consul, etcd)
- FL clients auto-register their URLs

## Deployment Steps

### On Machine A (Backend + Aggregator)

```bash
# 1. Start Backend
cd c:\repos\healchain\backend
npm run dev

# 2. Start Frontend (optional, can access from any browser)
cd c:\repos\healchain\frontend  
npm run dev

# 3. Start Aggregator
cd c:\repos\healchain\aggregator
python scripts/start_api_service.py
```

### On Machine B (FL Client 1)

```bash
# 1. Clone repository
git clone <repo-url>
cd healchain/fl_client

# 2. Install dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure .env
# Copy .env.example to .env and update:
# - BACKEND_URL=http://192.168.1.10:3000
# - MINER_PRIVATE_KEY=0x...
# - RPC_URL=http://192.168.1.10:8545

# 4. Import dataset (if training on real data)
python scripts/import_real_images.py <dataset-path>

# 5. Start FL Client service
python scripts/start_service.py
```

### On Machine C (FL Client 2)

Repeat the same steps as Machine B, but use a **different** `MINER_PRIVATE_KEY`.

## Current Limitations & Fixes Needed

### ✅ Issue 1: Backend FL Client URL Storage (FIXED)

**Status**: ✅ **IMPLEMENTED**

The backend now stores each miner's FL client URL during registration and uses it when triggering training.

**Changes Made**:
1. Added `flClientUrl` field to Miner model in database schema
2. Updated `POST /miners/register` to accept `flClientUrl` parameter
3. Modified training orchestration to fetch miner's URL from database
4. Falls back to `localhost:5001` if URL not provided (backward compatible)

**Usage**: When registering, include your FL client URL:
```json
{
  "taskID": "task_027",
  "address": "0x...",
  "proof": "ipfs://...",
  "flClientUrl": "http://192.168.1.20:5001"
}
```

### ✅ Issue 2: CORS (Already Fixed)

Both backend and aggregator already have CORS enabled, so cross-origin requests work.

---

## Quick Test (Same Network)

**On Machine A (192.168.1.10)**:
```bash
# Check aggregator is accessible
curl http://192.168.1.10:5002/api/health
# Should return: {"status":"ok"}
```

**On Machine B**:
```bash
# Check backend is accessible
curl http://192.168.1.10:3000/tasks/open
# Should return task list

# Check FL client is accessible from Machine A
# (Run this from Machine A):
curl http://192.168.1.20:5001/api/health
# Should return: {"status":"ok"}
```

## Summary

| Component | Distributed Ready? | Action Needed |
|-----------|-------------------|---------------|
| FL Client | ✅ Yes | Update `BACKEND_URL` in `.env` |
| Aggregator | ✅ Yes | Update `BACKEND_URL` if remote |
| Backend | ✅ Yes | Include `flClientUrl` in registration |
| Frontend | ✅ Yes | Update `NEXT_PUBLIC_BACKEND_URL` |

**Bottom Line**: You can now run FL clients on other machines! When registering a miner, include the `flClientUrl` parameter with the FL client's URL (e.g., `http://192.168.1.20:5001`). The backend will automatically use that URL to trigger training on the remote client.
