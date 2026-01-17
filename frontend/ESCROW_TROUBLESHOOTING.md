# Escrow Transaction Troubleshooting

## Why is Escrow Not Locked?

If your task shows "Escrow Pending" or escrow balance is 0 ETH, it means the on-chain transaction (`publishTask`) was never completed successfully.

### Common Causes

#### 1. **Transaction Rejected in Wallet**
- **Symptom**: Transaction modal appeared but you clicked "Reject" or closed the wallet popup
- **Solution**: Try publishing again and **confirm the transaction** in your wallet (MetaMask, etc.)

#### 2. **Insufficient Balance**
- **Symptom**: Transaction fails with "insufficient funds" error
- **Solution**: 
  - Check your wallet balance
  - Make sure you have enough ETH to cover:
    - The escrow amount (e.g., 0.1 ETH)
    - Gas fees (~0.001 ETH)
  - On Ganache: Import the account and check balance

#### 3. **Wrong Contract Address**
- **Symptom**: Transaction fails or contract not found
- **Solution**:
  - Check `.env.local` has correct contract addresses
  - Verify contracts are deployed on the correct network
  - Default localhost addresses:
    - Escrow: Check your `NEXT_PUBLIC_ESCROW_ADDRESS` environment variable
    - Reward: Check your `NEXT_PUBLIC_REWARD_ADDRESS` environment variable (if configured)

#### 4. **Task Already Exists**
- **Symptom**: Transaction fails with "Task exists" error
- **Solution**: Use a different task ID (must be unique)

#### 5. **Invalid Deadline**
- **Symptom**: Transaction fails with "Invalid deadline"
- **Solution**: Make sure deadline is in the future (not in the past)

#### 6. **Network Mismatch**
- **Symptom**: Transaction fails or contract not found
- **Solution**:
  - Make sure wallet is connected to the correct network (localhost:8545 for Ganache)
  - Check `chainId` matches your deployment

### How to Verify

1. **Check Transaction Hash**:
   - If transaction was submitted, you'll see a hash in the modal
   - Check the transaction on Etherscan (Sepolia) or your local explorer

2. **Check Contract State**:
   - Go to task detail page
   - Look at "Blockchain State" panel
   - Escrow Balance should show > 0 ETH if successful

3. **Check Browser Console**:
   - Open DevTools (F12)
   - Look for transaction errors
   - Check network tab for failed requests

### Test ETH (Fake Ethers) Works Fine!

**Test ETH from Ganache/Hardhat works perfectly** for escrow transactions. The issue is NOT with "fake ethers" - it's that the transaction wasn't completed.

### Step-by-Step Fix

1. **Check Wallet Balance**:
   ```javascript
   // In browser console
   window.ethereum.request({ method: 'eth_getBalance', params: [yourAddress, 'latest'] })
   ```

2. **Verify Contract Address**:
   - Check `.env.local` file
   - Make sure `NEXT_PUBLIC_ESCROW_ADDRESS` matches deployed contract

3. **Try Publishing Again**:
   - Go to `/publish` page
   - Fill in task details
   - **Make sure to confirm the transaction in your wallet**
   - Wait for confirmation (transaction modal will show success)

4. **Check Transaction Status**:
   - After submitting, check the transaction hash
   - Verify it was confirmed on-chain

### Expected Flow

1. ✅ Fill task form
2. ✅ Click "Publish Task"
3. ✅ Wallet popup appears → **CONFIRM**
4. ✅ Transaction submitted (hash shown)
5. ✅ Transaction confirmed (success message)
6. ✅ Escrow locked (check Blockchain State panel)

### If Still Not Working

1. **Check Ganache/Hardhat**:
   - Make sure blockchain is running
   - Check contract deployment logs
   - Verify contract addresses

2. **Check Wallet Connection**:
   - Disconnect and reconnect wallet
   - Switch networks if needed
   - Make sure you're using the correct account

3. **Check Browser Console**:
   - Look for JavaScript errors
   - Check network requests
   - Verify API calls to backend

4. **Try Different Task ID**:
   - Use a completely new task ID
   - Make sure it's unique

### Quick Test

To verify everything is working:

1. **Check Contract Address**:
   ```bash
   # In frontend/.env.local
   NEXT_PUBLIC_ESCROW_ADDRESS=<your-deployed-escrow-contract-address>
   ```

2. **Check Wallet Balance**:
   - Open MetaMask/wallet
   - Should show > 0.1 ETH (for escrow + gas)

3. **Publish Test Task**:
   - Task ID: `test_escrow_001`
   - Reward: `0.01` ETH (small amount for testing)
   - Deadline: Future date
   - **Confirm transaction in wallet**

4. **Verify Success**:
   - Check transaction hash
   - Go to task detail page
   - Escrow Balance should show `0.01 ETH`

### Summary

**Test ETH works fine!** The issue is that the escrow transaction (`publishTask`) was never completed successfully. Most common reasons:
- Transaction rejected in wallet
- Insufficient balance
- Wrong contract address
- Task already exists

Fix: Make sure to **confirm the transaction in your wallet** when publishing a task.

