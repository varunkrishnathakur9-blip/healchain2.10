# Miner Proof Creation and Upload Guide

## Overview

According to **Algorithm 2** from your BTP Report, miners must submit a proof (`proofi`) when registering for a task. This proof is verified against the task's dataset requirements (D) using `VerifyMinerProof(r.pki, r.proofi, taskPool[taskID].meta.D)`.

## What is a Miner Proof?

A miner proof demonstrates that you have:
1. **Access to the required dataset** (e.g., chestxray, mnist, cifar10)
2. **System capabilities** to participate in federated learning
3. **Valid credentials** for the task

## Proof Formats Accepted

The system accepts three proof formats:

1. **IPFS Link** (Recommended): `ipfs://Qm...` or `https://ipfs.io/ipfs/Qm...`
2. **HTTP/HTTPS URL**: `https://your-domain.com/proof.json`
3. **JSON System Proof** (Inline): Direct JSON string

## Creating a Valid Proof

### Option 1: JSON System Proof (Easiest for Testing)

A valid JSON proof should contain:

```json
{
  "dataset": "chestxray",
  "capabilities": [
    "local_training",
    "gradient_computation",
    "ndd_fe_encryption",
    "dgc_compression"
  ],
  "system_info": {
    "platform": "linux",
    "python_version": "3.10",
    "gpu_available": true,
    "memory_gb": 16
  },
  "miner_address": "0x...",
  "timestamp": "2025-01-03T16:00:00Z",
  "signature": "optional_cryptographic_signature"
}
```

**Required Fields:**
- `dataset`: Must match the task's dataset (e.g., "chestxray", "mnist", "cifar10")
- `capabilities`: Array of strings describing your system capabilities

**Optional Fields:**
- `system_info`: System specifications
- `miner_address`: Your wallet address
- `timestamp`: Proof creation time
- `signature`: Cryptographic signature (for enhanced security)

### Option 2: IPFS Link (Recommended for Production)

1. Create a JSON proof file (as shown above)
2. Upload it to IPFS
3. Use the IPFS hash as your proof

## Step-by-Step Guide

### Method 1: Using the Utility Script (Recommended)

1. **Run the proof generator script:**
   ```bash
   cd fl_client
   python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourAddress
   ```

2. **The script will:**
   - Generate a valid proof JSON
   - Optionally upload to IPFS (if IPFS Desktop is running)
   - Output the proof string to use in registration

3. **Copy the output** and paste it into the "Miner Proof" field when registering

### Method 2: Manual Creation

#### Step 1: Create Proof JSON

Create a file `miner_proof.json`:

```json
{
  "dataset": "chestxray",
  "capabilities": [
    "local_training",
    "gradient_computation",
    "ndd_fe_encryption",
    "dgc_compression"
  ],
  "system_info": {
    "platform": "linux",
    "python_version": "3.10",
    "gpu_available": true
  },
  "miner_address": "0xYourWalletAddress",
  "timestamp": "2025-01-03T16:00:00Z"
}
```

**Important:** Replace:
- `"chestxray"` with the actual dataset from the task (check task details)
- `"0xYourWalletAddress"` with your actual wallet address

#### Step 2: Upload to IPFS

**Using IPFS Desktop (Recommended):**

1. **Open IPFS Desktop** (make sure it's running)

2. **Add File:**
   - Click "Files" tab
   - Click "Import" → "File"
   - Select your `miner_proof.json`
   - Wait for upload to complete

3. **Get IPFS Hash:**
   - Right-click on the uploaded file
   - Select "Copy CID" or "Copy IPFS Path"
   - You'll get something like: `QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco`

4. **Use as Proof:**
   - Format 1: `ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco`
   - Format 2: `https://ipfs.io/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco`

**Using IPFS CLI (Alternative):**

```bash
# Install IPFS CLI if not installed
# Then add your file:
ipfs add miner_proof.json

# Output will show:
# added QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco miner_proof.json

# Use: ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco
```

**Using HTTP Gateway (Alternative):**

If you have a web server, you can:
1. Upload `miner_proof.json` to your server
2. Use the URL: `https://your-domain.com/miner_proof.json`

#### Step 3: Derive Your NDD-FE Public Key

The miner registration form also requires your **NDD-FE public key** (secp256r1). This is different from your Ethereum wallet address.

**Using the utility script (Recommended):**

```bash
cd fl_client
python scripts/derive_pubkey.py
```

This will:
- Read `MINER_PRIVATE_KEY` from your `.env` file
- Compute your public key: `pk = g^sk` (where `g` is the secp256r1 generator)
- Output the public key in format: `x_hex,y_hex`

**Or with explicit private key:**

```bash
python scripts/derive_pubkey.py 0xYourPrivateKey
```

**Output example:**
```
======================================================================
NDD-FE Public Key Derivation (secp256r1)
======================================================================

Private Key: 0x1234567890...abcdef

Public Key:  0000000000000000000000000000000000000000000000000000000000000001,0000000000000000000000000000000000000000000000000000000000000002

======================================================================

📋 Copy this public key for miner registration:

   0000000000000000000000000000000000000000000000000000000000000001,0000000000000000000000000000000000000000000000000000000000000002
```

**Note:** The public key is derived from your `MINER_PRIVATE_KEY` using the secp256r1 curve (different from Ethereum's secp256k1). This is used for NDD-FE encryption and Algorithm 2.2 key derivation.

#### Step 4: Register as Miner

1. Go to the task page in the frontend
2. Fill in the "Miner Proof" field with:
   - IPFS link: `ipfs://Qm...` (recommended)
   - Or direct JSON: `{"dataset":"chestxray","capabilities":[...]}`
3. Fill in the "Public Key" field with the output from `derive_pubkey.py`:
   - Format: `x_hex,y_hex` (64 hex digits each)
   - Example: `0000...0001,0000...0002`
4. Click "Register as Miner"

## Dataset-Specific Examples

### Chest X-Ray Dataset
```json
{
  "dataset": "chestxray",
  "capabilities": [
    "local_training",
    "gradient_computation",
    "ndd_fe_encryption",
    "dgc_compression"
  ],
  "dataset_info": {
    "type": "medical_imaging",
    "format": "dicom",
    "samples_available": 1000
  }
}
```

### MNIST Dataset
```json
{
  "dataset": "mnist",
  "capabilities": [
    "local_training",
    "gradient_computation",
    "ndd_fe_encryption",
    "dgc_compression"
  ],
  "dataset_info": {
    "type": "handwritten_digits",
    "format": "image",
    "samples_available": 60000
  }
}
```

### CIFAR-10 Dataset
```json
{
  "dataset": "cifar10",
  "capabilities": [
    "local_training",
    "gradient_computation",
    "ndd_fe_encryption",
    "dgc_compression"
  ],
  "dataset_info": {
    "type": "object_classification",
    "format": "image",
    "samples_available": 50000
  }
}
```

## Verification Process

When you submit your proof:

1. **Format Check**: System validates proof format (IPFS link, URL, or JSON)
2. **Dataset Match**: If JSON, checks if `proof.dataset === task.dataset`
3. **Content Validation**: Verifies proof structure and required fields
4. **Acceptance**: If valid, miner is added to `validMiners` and `proofVerified = true`

## Troubleshooting

### Error: "Miner proof is required"
- **Solution**: Make sure you've filled in the proof field

### Error: "Miner proof verification failed"
- **Solution**: 
  - Check that your proof format is valid
  - For JSON proofs, ensure `dataset` field matches the task's dataset
  - For IPFS links, ensure the hash is valid (starts with Qm...)

### Error: "Cannot connect to IPFS"
- **Solution**: 
  - Make sure IPFS Desktop is running
  - Check IPFS API URL in backend `.env` file
  - Try using a public IPFS gateway URL instead

### Proof Not Verifying
- **Check:**
  1. Dataset name matches exactly (case-sensitive)
  2. IPFS hash is correct and file is accessible
  3. JSON structure is valid (use JSON validator)

## Best Practices

1. **Use IPFS Links**: More reliable and decentralized
2. **Include System Info**: Helps with verification
3. **Sign Your Proof**: Add cryptographic signature for enhanced security
4. **Keep Proof Updated**: Update if your system capabilities change
5. **Test First**: Use the utility script to generate and validate before registration

## Security Considerations

- **Don't Share Private Keys**: Proof should not contain sensitive information
- **Verify IPFS Content**: Ensure your IPFS node is running and content is accessible
- **Use HTTPS**: If using HTTP URLs, prefer HTTPS for security
- **Validate Before Submission**: Test your proof format before registering

## Quick Reference

| Format | Example | When to Use |
|--------|---------|-------------|
| IPFS Link | `ipfs://Qm...` | Production, permanent storage |
| IPFS Gateway | `https://ipfs.io/ipfs/Qm...` | Alternative IPFS access |
| JSON Inline | `{"dataset":"chestxray",...}` | Testing, quick setup |
| HTTP URL | `https://your-domain.com/proof.json` | Custom hosting |

---

## Getting Your NDD-FE Public Key

When registering as a miner, you'll need your **NDD-FE public key** (secp256r1). This is different from your Ethereum wallet address.

**Quick method:**

```bash
cd fl_client
python scripts/derive_pubkey.py
```

This derives your public key from `MINER_PRIVATE_KEY` using the formula: `pk = g^sk` where `g` is the secp256r1 generator point.

**Output format:** `x_hex,y_hex` (64 hex digits each)

**Example:**
```
0000000000000000000000000000000000000000000000000000000000000001,0000000000000000000000000000000000000000000000000000000000000002
```

Copy this value into the "Public Key" field when registering as a miner.

---

**Need Help?** 
- Proof generation: `fl_client/scripts/generate_miner_proof.py`
- Public key derivation: `fl_client/scripts/derive_pubkey.py`

