# 🏥 HealChain FL Client (Miner) - Production Edition

This repository implements the **production-ready miner-side FL client** for HealChain, a blockchain-enabled privacy-preserving federated learning framework.

**Status**: ✅ **Production Ready** - Only for genuine FL operations  
**Compliance**: 100% compliant with BTP Phase 1 Report (Chapter 4)  
**Review**: See [FL_CLIENT_REVIEW.md](./FL_CLIENT_REVIEW.md) for detailed compliance review

---

## ⚠️ CRITICAL: Genuine Client Requirement

**The aggregator ONLY processes submissions from GENUINE FL clients.**

- ✅ **Genuine FL Clients**: Full M3 workflow with real encryption, training, and scoring
- ❌ **Mock Clients**: Disabled in production - the aggregator will reject mock submissions

This ensures:
- Real local model training happens at miners
- Genuine gradient compression and encryption
- Authentic contribution scoring
- Secure blockchain integration

---

## 📋 Overview

The FL client implements complete miner-side operations for HealChain federated learning:

- **M3**: Local model training, gradient compression (DGC), contribution scoring (||Δ′||₂), NDD-FE encryption
- **M5**: Candidate block verification and consensus voting
- **M7**: Score revelation on-chain for reward distribution

The backend is treated as **untrusted** and is used only for metadata routing. All cryptographic operations happen locally on the client with real encryption (no mocks).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (required)
- Virtual environment (required)
- HealChain contracts deployed and running
- Backend server running on port 3000
- Blockchain node (Ganache/Hardhat) on port 8545

### Installation

#### 1. Create Virtual Environment

```bash
cd fl_client
py -3.11 -m venv venv
```

#### 2. Activate Virtual Environment

**Windows (PowerShell)**:
```bash
venv\Scripts\activate
```

**Windows (CMD)**:
```bash
venv\Scripts\activate.bat
```

**Linux/Mac**:
```bash
source venv/bin/activate
```

#### 3. Verify Python Version

```bash
python --version
# Expected: Python 3.11.x (NOT 3.10 or earlier)
```

#### 4. Upgrade pip

```bash
python -m pip install --upgrade pip setuptools wheel
```

#### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### Configuration

#### 1. Environment Setup

```bash
cp .env.example .env
```

#### 2. Configure Environment Variables (.env)

**CRITICAL**: These must be configured correctly for genuine FL operations.

```bash
# === BLOCKCHAIN CONFIGURATION (REQUIRED) ===
RPC_URL=http://localhost:8545
CHAIN_ID=1337

# === MINER WALLET (REQUIRED) ===
# Use actual private key from your miner account (funded with ETH)
MINER_PRIVATE_KEY=0x...
MINER_ADDRESS=0x...

# === BACKEND CONFIGURATION (REQUIRED) ===
BACKEND_URL=http://localhost:3000

# === FL TRAINING CONFIGURATION ===
LOCAL_EPOCHS=1                    # Number of local training epochs
DGC_THRESHOLD=0.9                 # Top-k compression: keep top 10%
BATCH_SIZE=32                     # Training batch size

# === CRYPTOGRAPHIC KEYS (REQUIRED FOR PRODUCTION) ===
# These are provided by the aggregator via /tasks/:taskID/public-keys
# Format: x_hex,y_hex for public keys
TP_PUBLIC_KEY=x_hex,y_hex         # Trusted Party public key
AGGREGATOR_PK=x_hex,y_hex         # Aggregator public key
```

---

## 🎮 Production Usage

### Start the FL Client

```bash
# Activate virtual environment first
venv\Scripts\activate

# Run the genuine FL client
python scripts/start_client.py
```

### Expected Output (Genuine Client)

```
✅ HealChain FL Client Started
✅ Connected to backend at http://localhost:3000
✅ Blockchain RPC at http://localhost:8545

[Task Discovery] Polling for open tasks...
✅ Found 1 task from backend
  Task ID: task_025
  Dataset: healthcare_records
  Model: SimpleModel

[M3 - Training] Training on task_025...
✅ Local training complete
✅ Gradient computed: shape=(10, 128)
✅ DGC compression applied (90% threshold)
✅ Contribution score: ||Δ'||₂ = 0.847

[M3 - Encryption] Encrypting gradients...
✅ Retrieved TP and aggregator public keys
✅ NDD-FE encryption complete
✅ Real functional encryption applied (secp256r1)

[M3 - Submission] Submitting encrypted update...
{
  "taskID": "task_025",
  "ciphertext": ["0x...", "0x..."],
  "scoreCommit": "0x...",
  "signature": "0x...",
  "miner_pk": "0x..."
}

✅ Submission accepted by aggregator
⏳ Waiting for next task...
```

### Test Configuration

```bash
python scripts/test_client.py
```

This validates:
- Backend connectivity
- Task discovery
- Training pipeline
- Encryption setup
- Blockchain connection

---

## 🔐 Genuine FL Operations (M3)

### Complete Training Workflow

The FL client implements the full M3 workflow as specified in BTP Phase 1 Report Chapter 4:

#### 1. **Local Training**
- Loads private local dataset
- Trains model locally for `LOCAL_EPOCHS`
- **No data leaves the client**

#### 2. **Gradient Computation**
- Computes gradient update: `Δᵢ = (w_old - w_new)`
- Gradient is computed locally only

#### 3. **Gradient Compression (DGC)**
- Applies dynamic gradient compression
- Keeps top `(1 - DGC_THRESHOLD) × 100`% of gradients
- Default: 10% sparsity (threshold=0.9)

#### 4. **Quantization**
- Quantizes gradients for BSGS compatibility
- Maintains accuracy through proper scaling

#### 5. **Contribution Scoring**
- Calculates L2 norm: `score = ||Δ'ᵢ||₂`
- Represents miner's contribution
- Cannot be falsified

#### 6. **Score Commitment**
- Generates commitment: `commit = keccak256(score || nonce || taskID || miner_addr)`
- Prevents score manipulation
- Nonce is cryptographically random

#### 7. **Real NDD-FE Encryption**
- Encrypts compressed gradients with real functional encryption
- Uses secp256r1 elliptic curve (matches aggregator)
- No mock encryption
- Result: `Cᵢ = NDD-FE-Encrypt(Δ'ᵢ, pk_tp, pk_agg)`

#### 8. **Miner Signature**
- Signs submission with miner private key
- Authenticates miner identity
- Cannot be forged

#### 9. **Submission**
- Submits to aggregator: `(Cᵢ, commitᵢ, signature, miner_pk)`
- Aggregator verifies all cryptographic operations
- Aggregator rejects mock clients

### Aggregator Verification

The aggregator verifies:
- ✅ Valid miner signature
- ✅ Real NDD-FE encryption format
- ✅ Proper gradient compression
- ✅ Authentic contribution score
- ✅ Non-mock client operations

**Rejection Criteria**:
- ❌ Missing or invalid signature
- ❌ Mock encryption detected
- ❌ Gradient bounds violated
- ❌ Malformed submissions
- ❌ Unverifiable contributions

---

## 🔄 M5: Candidate Verification

```bash
python scripts/verify_candidate.py
```

Miners verify candidate blocks:
- Download aggregated model from IPFS
- Verify aggregator signature
- Check score commitment inclusion
- Validate model quality
- Vote: VALID or INVALID

---

## 🏆 M7: Score Revelation & Rewards

```bash
python scripts/reveal_scores.py
```

Reveal contribution scores on-chain:
- Retrieve score from local state
- Call `revealScore()` on RewardDistribution contract
- Smart contract distributes rewards
- Requires accuracy reveal by task publisher

---

## 🏗️ Architecture

### Directory Structure

```
fl_client/
├── src/
│   ├── tasks/              # Task management (M3)
│   │   ├── lifecycle.py    # M3 complete workflow
│   │   ├── watcher.py      # Task polling
│   │   └── validator.py    # Task validation
│   ├── training/           # Model training
│   │   ├── model.py        # Neural network model
│   │   ├── trainer.py      # Training logic
│   │   └── gradient.py     # Gradient computation
│   ├── model_compression/  # DGC compression (M3)
│   │   └── dgc.py          # Top-k gradient compression
│   ├── crypto/             # Cryptography (REAL, NOT MOCK)
│   │   ├── nddfe.py        # Real NDD-FE encryption (secp256r1)
│   │   └── signature.py    # Miner signatures
│   ├── scoring/            # Contribution scoring (M3)
│   │   └── norm.py         # L2 norm calculation
│   ├── commit/             # Commit-reveal scheme
│   │   ├── commit.py       # Score commitment
│   │   └── reveal.py       # Score revelation
│   ├── dataset/            # Local dataset handling
│   │   ├── loader.py       # Data loading
│   │   └── preprocess.py   # Preprocessing
│   ├── verification/       # Miner verification (M5)
│   │   └── verifier.py     # Block verification
│   ├── chain/              # Blockchain interaction (M7)
│   │   ├── wallet.py       # Wallet management
│   │   └── reveal_tx.py    # On-chain reveals
│   ├── state/              # Local state management
│   ├── config/             # Configuration
│   ├── transport/          # Backend communication
│   └── utils/              # Utilities
├── scripts/
│   ├── start_client.py     # Main entry point (GENUINE ONLY)
│   ├── test_client.py      # Configuration testing
│   ├── reveal_scores.py    # M7 score revelation
│   └── verify_candidate.py # M5 verification
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Key Components

**M3 Workflow** (`src/tasks/lifecycle.py`):
- Implements complete training pipeline
- Real NDD-FE encryption (not mock)
- Proper gradient compression
- Authentic contribution scoring
- No shortcuts or mock operations

**Cryptographic Layer** (`src/crypto/nddfe.py`):
- Real functional encryption using secp256r1
- No mock encryption implementations
- Production-ready cryptography
- Validated and frozen (no further changes)

---

## 📡 Backend Integration

### Genuine Client API Interaction

| Endpoint | Purpose | M3 Phase |
|----------|---------|----------|
| `GET /tasks/open` | Discover tasks | Discovery |
| `GET /tasks/:taskID/public-keys` | Get aggregator keys | Setup |
| `POST /aggregator/:taskID/submissions` | Submit encrypted update | Submission |
| `GET /aggregator/:taskID/key-status` | Check key availability | Status |

**All communication is authenticated with miner signature**

### Backend Assumptions

- ✅ Backend provides genuine task metadata
- ✅ Backend stores aggregator public keys
- ✅ Backend validates miner signatures
- ✅ Backend forwards submissions to aggregator
- ❌ Backend cannot see encrypted gradients
- ❌ Backend cannot falsify contributions
- ❌ Backend cannot approve mock clients

---

## ✅ Security & Authenticity

### Genuine FL Guarantees

- ✅ **Real Training**: Actual model training happens locally
- ✅ **Real Encryption**: NDD-FE encryption with secp256r1 (not mock)
- ✅ **Real Compression**: DGC compression applied to gradients
- ✅ **Real Scoring**: L2 norm contribution scoring
- ✅ **Real Signatures**: Miner signature authentication
- ✅ **No Data Leakage**: Raw data never leaves client
- ✅ **No Mock Operations**: All operations are genuine

### Cryptographic Validation

- ✅ NDD-FE encryption: Real functional encryption
- ✅ Commit-reveal: Secure score commitments
- ✅ Signatures: ECDSA authentication
- ✅ Hashing: Keccak256 commitments
- ✅ Key management: Secure private key handling

### Best Practices (MANDATORY)

- ✅ Private keys **only** in environment variables
- ✅ **Never** hardcode secrets
- ✅ **Never** use mock encryption in production
- ✅ **Always** verify backend responses
- ✅ **Always** run full M3 workflow
- ✅ Use secure random number generation
- ✅ Validate all cryptographic operations

---

## 🛠️ Production Utilities

### Main Scripts

| Script | Purpose | M3 Phase |
|--------|---------|----------|
| `start_client.py` | Main client execution (GENUINE ONLY) | All |
| `test_client.py` | Configuration validation | Setup |
| `reveal_scores.py` | Score revelation (M7) | Rewards |
| `verify_candidate.py` | Block verification (M5) | Consensus |

### Helper Utilities

```bash
# Verify blockchain connectivity and miner balance
python scripts/check_balance.py

# Check task status on smart contract
python scripts/check_task_status.py

# Test blockchain interaction
python scripts/check_contract.py
```

---

## 🔄 Correct Startup Sequence

### Production Deployment Order

1. **Start Blockchain** (Ganache or Hardhat):
   ```bash
   npx hardhat node
   # or
   ganache-cli
   ```

2. **Deploy HealChain Contracts**:
   ```bash
   cd contracts
   node scripts/deploy-final-working.mjs
   # Verify deployment: Check contract addresses output
   ```

3. **Start Backend Server**:
   ```bash
   cd backend
   npm run dev
   # Expected: "HealChain backend running on port 3000"
   ```

4. **Fund Miner Accounts** (if needed):
   ```bash
   cd fl_client
   python scripts/fund_miner.py
   ```

5. **Start FL Client** (GENUINE ONLY):
   ```bash
   cd fl_client
   (venv) python scripts/start_client.py
   ```

6. **Monitor Aggregator**:
   ```bash
   # In separate terminal
   cd aggregator
   npm run dev
   # Check: http://localhost:3001/aggregator
   ```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. "Backend endpoint not found"
**Solution**: 
- Ensure backend is running: `npm run dev` (port 3000)
- Check `BACKEND_URL` in `.env`
- Verify backend has `/tasks/open` endpoint

#### 2. "Public keys not available"
**Solution**:
- Check backend has cryptographic keys configured
- Verify `TP_PUBLIC_KEY` and `AGGREGATOR_PK` in `.env`
- Or ensure backend provides keys via `/tasks/:taskID/public-keys`

#### 3. "Cannot connect to blockchain"
**Solution**:
- Verify Ganache/Hardhat is running on port 8545
- Check `RPC_URL` in `.env` (should be `http://localhost:8545`)
- Verify `CHAIN_ID` matches your network (usually 1337)

#### 4. "Sender doesn't have enough funds"
**Solution**: Fund the miner account with ETH
```bash
python scripts/fund_miner.py
```

#### 5. "ModuleNotFoundError: No module named 'tasks'"
**Solution**: Set PYTHONPATH
```bash
# PowerShell
$env:PYTHONPATH="src"; python scripts/start_client.py

# Linux/Mac
export PYTHONPATH=$PWD/src
python scripts/start_client.py
```

#### 6. "Aggregator rejected submission (mock client)"
**Solution**: 
- Ensure you're running genuine FL client (not mock)
- Check that M3 workflow is complete
- Verify real NDD-FE encryption is applied
- Check `start_client.py` is being used (not test client)

---

## 📊 M3 Workflow Details

### Complete Training Pipeline (BTP Chapter 4)

```
1. Task Discovery
   └─> Poll /tasks/open
   └─> Validate task compatibility

2. Local Training (M3 Phase 1)
   └─> Load private local dataset
   └─> Train model for LOCAL_EPOCHS
   └─> Compute gradient Δᵢ = (w_old - w_new)

3. Gradient Compression (M3 Phase 2)
   └─> Apply DGC compression (keep top 10%)
   └─> Quantize for BSGS compatibility
   └─> Validate gradient bounds

4. Contribution Scoring (M3 Phase 3)
   └─> Calculate L2 norm: ||Δ'ᵢ||₂
   └─> Generate commitment: keccak256(score || nonce || taskID || addr)
   └─> Save to local state

5. Encryption (M3 Phase 4)
   └─> Retrieve TP and aggregator public keys
   └─> Apply REAL NDD-FE encryption (NOT MOCK)
   └─> Result: Cᵢ = NDD-FE-Encrypt(Δ'ᵢ, pk_tp, pk_agg)

6. Authentication (M3 Phase 5)
   └─> Generate miner signature
   └─> Sign submission payload

7. Submission (M3 Phase 6)
   └─> Submit to aggregator: (Cᵢ, commitᵢ, signature, miner_pk)
   └─> Aggregator verifies all cryptographic operations
   └─> Aggregator accepts ONLY genuine clients
```

---

## 📋 Compliance Status

**BTP Phase 1 Report (Chapter 4)**: ✅ **100% Compliant**

All required M3 operations implemented:
- ✅ **M3.1**: Local model training with real data
- ✅ **M3.2**: Genuine gradient computation
- ✅ **M3.3**: DGC compression (top 10%)
- ✅ **M3.4**: L2 norm scoring (||Δ'ᵢ||₂)
- ✅ **M3.5**: REAL NDD-FE encryption (no mocks)
- ✅ **M3.6**: Score commitment with nonce
- ✅ **M3.7**: Miner signature authentication
- ✅ **M5**: Candidate verification and voting
- ✅ **M7**: Score revelation on-chain

See [FL_CLIENT_REVIEW.md](./FL_CLIENT_REVIEW.md) for detailed compliance matrix

---

## 🔒 Cryptographic Frozen Status

- 🔒 **Cryptographic layer frozen after validation**
- ✅ All crypto operations validated and production-ready
- ✅ Real NDD-FE encryption confirmed (no mocks)
- ✅ BSGS compatibility validated
- ✅ Signature algorithms verified
- ✅ No further crypto modifications needed
- ⚠️ **DO NOT MODIFY** crypto modules without security review

---

## 🧪 Testing & Validation

### Configuration Test

```bash
python scripts/test_client.py
```

Validates:
- Backend connectivity
- Task discovery
- Training pipeline
- Encryption setup
- Blockchain connection

### Production Readiness Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` configured with real miner private key
- [ ] Blockchain running on port 8545
- [ ] Contracts deployed
- [ ] Backend running on port 3000
- [ ] Miner account funded with ETH
- [ ] Configuration test passes
- [ ] First task submission successful

---

## 📚 Documentation

- **[FL_CLIENT_REVIEW.md](./FL_CLIENT_REVIEW.md)**: Detailed compliance review
- **[BTP_Ph1_report.pdf](../BTP_Ph1_report.pdf)**: Chapter 4 - System Architecture
- **Backend API**: See backend README for API documentation
- **Smart Contracts**: See contracts directory for contract ABIs

---

## 🆘 Support & Questions

### Genuine FL Client Requirements

**Q: Will the aggregator accept mock clients?**  
A: No. The aggregator **only accepts genuine FL clients** that perform real training, encryption, and scoring. Mock clients are rejected.

**Q: Are gradients actually encrypted?**  
A: Yes, with real NDD-FE encryption using secp256r1. No mock encryption in production.

**Q: Does local training actually happen?**  
A: Yes, mandatory. The client loads your local dataset and trains the model locally.

**Q: Can I skip DGC compression?**  
A: No, compression is mandatory for contribution scoring and gradient bounds validation.

**Q: How is contribution score calculated?**  
A: L2 norm of compressed gradients: `||Δ'ᵢ||₂`. Cannot be falsified.

**Q: What happens if gradients exceed BSGS bounds?**  
A: Quantization and bounds checking ensure compatibility. Out-of-bounds gradients are clipped.

---

## 🎯 Key Takeaway

**HealChain FL Client is PRODUCTION READY for genuine federated learning operations. The aggregator will ONLY process submissions from clients that perform real training, genuine encryption, and authentic contribution scoring. Mock clients are automatically rejected.**

---

**🚀 Ready for Production - Genuine FL Operations Only!**
