# Quick Start: Creating Miner Proof

## Fastest Method (3 Steps)

### Step 1: Generate Proof
```bash
cd fl_client
python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourWalletAddress --upload-ipfs
```

**Replace:**
- `chestxray` with the actual dataset from the task (check task details)
- `0xYourWalletAddress` with your actual wallet address

### Step 2: Copy the IPFS Link
The script will output something like:
```
✅ Uploaded to IPFS!
IPFS Hash (CID): QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco

Use one of these formats for registration:
  • ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
```

### Step 3: Register as Miner
1. Go to the task page in frontend
2. Paste the IPFS link (e.g., `ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco`) into the "Miner Proof" field
3. Click "Register as Miner"

## Alternative: Use JSON Directly (No IPFS)

If IPFS Desktop is not running:

```bash
python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourWalletAddress --json-only
```

Copy the JSON output and paste it directly into the "Miner Proof" field.

## Common Datasets

- **Chest X-Ray**: `--dataset chestxray`
- **MNIST**: `--dataset mnist`
- **CIFAR-10**: `--dataset cifar10`
- **Custom**: `--dataset custom`

## Troubleshooting

**"Cannot connect to IPFS Desktop"**
- Make sure IPFS Desktop is running
- Or use `--json-only` flag to skip IPFS upload

**"Miner proof verification failed"**
- Check that dataset name matches exactly (case-sensitive)
- Ensure your proof format is valid

## Full Documentation

See `MINER_PROOF_GUIDE.md` in the project root for complete documentation.

