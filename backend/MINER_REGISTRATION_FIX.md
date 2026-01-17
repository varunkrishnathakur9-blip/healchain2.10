# Miner Registration Error Fix

## Issue
"Internal server error" when registering as miner after adding proof verification.

## Root Cause
The Prisma client needs to be regenerated after the schema change to include the new `proof` and `proofVerified` fields.

## Solution

### Step 1: Stop the Backend Server
Stop the running backend server (Ctrl+C in the terminal where it's running).

### Step 2: Regenerate Prisma Client
```bash
cd backend
npx prisma generate
```

### Step 3: Restart Backend Server
```bash
npm run dev
```

## What Was Fixed

1. **Error Handling**: Improved error messages to show actual error details in development mode
2. **BigInt Serialization**: Fixed BigInt fields in API responses (stake field)
3. **Stake Validation**: Added proper validation and conversion for stake values
4. **Error Logging**: Added detailed error logging for debugging

## Verification

After restarting, try registering as a miner again. The error should be resolved, and if there are any issues, you'll see more detailed error messages.

## If Error Persists

Check the backend console logs for detailed error messages. The improved error handling will now show:
- Error message
- Error type
- Stack trace (in development mode)

