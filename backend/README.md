# 🏥 HealChain Backend

A decentralized federated learning coordination backend that manages machine learning tasks, miner participation, gradient aggregation, and reward distribution through blockchain integration.

**Status**: ✅ **100% Compliant** with BTP Phase 1 Report  
**Review**: See [BACKEND_REVIEW.md](./BACKEND_REVIEW.md) for detailed compliance review

---

## 📋 Overview

HealChain backend serves as the coordination layer for federated learning tasks, implementing all 7 modules (M1-M7) from the BTP Phase 1 Report:

- **M1**: Task Publishing with Escrow and Commit
- **M2**: Miner Selection and Key Derivation
- **M3**: Local Model Training and Gradient-Norm Scoring
- **M4**: Secure Aggregation, BSGS Recovery, Evaluation and Candidate Formation
- **M5**: Miner Verification Feedback
- **M6**: Aggregator Verify, Build Payload and Publish On-Chain
- **M7**: Smart Contract Reveal and Reward Distribution

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- Ethereum node (Ganache for development, Sepolia for testnet)
- IPFS node or service (Pinata/NFT.storage)

### Installation
```bash
# Install dependencies
npm install

# Set up environment
cp .env.development .env
# Edit .env with your configuration

# Set up database
npm run prisma:migrate
npm run prisma:generate
```

### Environment Setup

Required environment variables (see `.env.development` for template):

```bash
# Server
PORT=3000
NODE_ENV=development

# Database
DATABASE_URL="postgresql://user:password@localhost:5432/healchain"

# Blockchain
RPC_URL="http://127.0.0.1:8545"
BACKEND_PRIVATE_KEY="0x..."
ESCROW_ADDRESS="0x..."
REWARD_CONTRACT_ADDRESS="0x..."
BLOCK_PUBLISHER_ADDRESS="0x..."

# IPFS
IPFS_API_URL="https://api.pinata.cloud"
IPFS_API_KEY="your_key"
IPFS_API_SECRET="your_secret"
```

### 🔁 Startup Sequence

```bash
# 1. Start Ganache (local blockchain)
ganache

# 2. Start Backend
npm run dev
# Expected: "HealChain backend running on port 3000"

# 3. Start FL Client (in separate terminal)
cd ../fl_client
(venv) python -m scripts.start_client
```

---

## 📡 API Endpoints

### **M1: Task Management** ✅

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/tasks/create` | Create new federated learning task with commit hash | ✅ Wallet |
| `GET` | `/tasks/open` | **Get open tasks for FL client** ⭐ | ❌ Public |
| `GET` | `/tasks/:taskID` | Get specific task details | ❌ Public |
| `GET` | `/tasks` | List all tasks with filtering | ❌ Public |
| `PUT` | `/tasks/:taskID/status` | Update task status | ✅ Wallet |
| `POST` | `/tasks/check-deadlines` | Check and update task deadlines | ❌ Public |

**See**: [TASK_API_DOCUMENTATION.md](./TASK_API_DOCUMENTATION.md) for detailed API documentation

### **M2: Miner Operations** ✅

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/miners/register` | Register miner for task participation | ✅ Wallet |

**Request Body**:
```json
{
  "taskID": "task_123",
  "address": "0x...",
  "publicKey": "0x...",
  "stake": "1000000000000000000",
  "message": "Registration message",
  "signature": "0x..."
}
```

### **M3-M4: Aggregator Operations** ✅

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/aggregator/submit-update` | Submit encrypted gradient metadata | ✅ Wallet |
| `POST` | `/aggregator/submit-candidate` | Submit aggregated model candidate | ✅ Wallet |
| `POST` | `/aggregator/publish` | Publish final block on-chain (M6) | ✅ Wallet |

### **M5: Verification** ✅

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/verification/submit` | Submit verification vote | ✅ Wallet |
| `GET` | `/verification/consensus/:taskID` | Get consensus status | ❌ Public |

### **M7: Reward Management** ✅

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/rewards/reveal-accuracy` | Reveal accuracy (M7a) | ✅ Wallet |
| `POST` | `/rewards/reveal-score` | Reveal miner score (M7b) | ✅ Wallet |
| `POST` | `/rewards/distribute` | Distribute rewards (M7c) | ✅ Wallet |

---

## 🗄️ Database Schema

### Core Models

- **Task**: Task metadata, commit hash, status, deadline, publisher
- **Miner**: Miner registration, public keys, stakes, task association
- **Gradient**: Encrypted gradient submissions, score commitments, status
- **Block**: Published blocks, model hashes, score commitments, aggregator
- **KeyDelivery**: Secure key delivery for aggregators (M2)
- **Verification**: Miner verification votes, consensus tracking (M5)
- **Reward**: Reward distribution records (M7)

### Task Status Flow

```
CREATED → OPEN → COMMIT_CLOSED → REVEAL_OPEN → REVEAL_CLOSED 
  → AGGREGATING → VERIFIED → REWARDED
```

### Database Migrations

```bash
# Create new migration
npm run prisma:migrate

# Generate Prisma client
npm run prisma:generate

# Open Prisma Studio (database GUI)
npx prisma studio
```

---

## 🔐 Authentication

The backend uses Ethereum wallet signature authentication:

1. **Client signs message** containing action details with their private key
2. **Backend verifies signature** using Ethers.js `verifyMessage()`
3. **Address extracted** from signature and attached to request
4. **Authorization checked** based on address and action context

**Example**:
```typescript
const message = `Create task: ${taskID}`;
const signature = await wallet.signMessage(message);
// Send { message, signature, ... } to backend
```

**Middleware**: `middleware/auth.ts` - `requireWalletAuth`

---

## 🔗 Blockchain Integration

### Smart Contracts

- **HealChainEscrow**: Task creation and escrow management (M1)
- **RewardDistribution**: Commit-reveal and reward distribution (M7)
- **BlockPublisher**: On-chain block publishing (M6)

### Configuration

- **Provider**: JSON-RPC connection to Ethereum node
- **Signer**: Backend wallet for on-chain transactions
- **Contracts**: Ethers.js contract instances

**Files**: `config/blockchain.config.ts`, `contracts/escrow.ts`

---

## 📦 IPFS Storage

Used for decentralized storage of:
- Aggregated model descriptors
- Block metadata
- Public task information

**Note**: Never stores private gradients or sensitive data

**Service**: `services/ipfsService.ts`

---

## 🏗️ Architecture

### Service Layer

| Service | Module | Description |
|---------|-------|-------------|
| `taskService.ts` | M1 | Task creation, commit hash generation, deadline management |
| `minerSelectionService.ts` | M2 | Miner registration, PoS selection, key derivation coordination |
| `trainingService.ts` | M3 | Gradient submission handling, score commitment storage |
| `aggregationService.ts` | M4 | Aggregation coordination, submission collection |
| `verificationService.ts` | M5 | Verification vote collection, consensus calculation |
| `publisherService.ts` | M6 | On-chain block publishing, transaction management |
| `rewardService.ts` | M7 | Accuracy reveal, score reveal, reward distribution |

### Cryptographic Layer

| Module | Description |
|--------|-------------|
| `crypto/keyDerivation.ts` | NDD-FE functional encryption key derivation (M2) |
| `crypto/keyDelivery.ts` | Secure key delivery to aggregators (M2) |
| `crypto/posSelection.ts` | Deterministic PoS aggregator selection (M2) |
| `crypto/commitReveal.ts` | Commit-reveal scheme utilities (M1, M7) |

### Middleware

- **`auth.ts`**: Wallet signature verification
- **`validation.ts`**: Request field validation

---

## 🛠️ Development

### Scripts

```bash
# Development
npm run dev          # Start development server with hot reload

# Production
npm run build        # Compile TypeScript to JavaScript
npm run start        # Start production server

# Database
npm run prisma:migrate    # Run database migrations
npm run prisma:generate   # Generate Prisma client
```

### Project Structure

```
backend/
├── src/
│   ├── api/              # Route handlers
│   ├── services/         # Business logic (M1-M7)
│   ├── crypto/           # Cryptographic operations
│   ├── config/           # Configuration
│   ├── contracts/        # Blockchain contract interactions
│   ├── middleware/       # Auth & validation
│   └── utils/            # Utilities
├── prisma/
│   └── schema.prisma     # Database schema
└── dist/                 # Compiled JavaScript
```

---

## 🔒 Security

### Security Features

- ✅ **Wallet Authentication**: All sensitive operations require wallet signatures
- ✅ **Input Validation**: Comprehensive field validation middleware
- ✅ **Cryptographic Security**: Secure random number generation, Keccak256 commitments
- ✅ **Database Security**: Prisma ORM (SQL injection protection)
- ✅ **Error Handling**: Proper error propagation and user-friendly messages

### Best Practices

- Private keys stored in environment variables only
- All sensitive operations require wallet authentication
- Gradient data encrypted before storage
- Commit-reveal scheme prevents data manipulation
- Reentrancy protection in smart contract interactions

---

## 📊 Protocol Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| Minimum Miners | 3 | Minimum miners required for task |
| Consensus Ratio | 50% | Minimum votes for consensus (M5) |
| Aggregation Timeout | 1 hour | Timeout for aggregation phase |
| Verification Timeout | 1 hour | Timeout for verification phase |

---

## 🧪 Testing

### Manual Testing

See [TASK_API_DOCUMENTATION.md](./TASK_API_DOCUMENTATION.md) for API testing examples.

### Integration Testing

Test with FL client:
```bash
# Start backend
npm run dev

# In another terminal, start FL client
cd ../fl_client
python -m scripts.start_client
```

---

## 🚀 Deployment

### Production Setup

1. **Configure Environment**:
   - Set production environment variables
   - Update contract addresses
   - Configure production database

2. **Database Setup**:
   ```bash
   npm run prisma:migrate
   npm run prisma:generate
   ```

3. **Build**:
   ```bash
   npm run build
   ```

4. **Deploy**:
   ```bash
   npm run start
   ```

### Docker Support

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 📚 Documentation

- **[BACKEND_REVIEW.md](./BACKEND_REVIEW.md)**: Comprehensive compliance review
- **[TASK_API_DOCUMENTATION.md](./TASK_API_DOCUMENTATION.md)**: Detailed API documentation
- **BTP Report**: Chapter 4 - Proposed System Architecture

---

## 🔍 Monitoring

### Logging

- Structured logging with custom logger (`utils/logger.ts`)
- Different log levels for development/production
- Error tracking and performance monitoring

### Health Checks

Monitor:
- Database connection status
- Blockchain node connectivity
- IPFS service availability

---

## 🤝 Contributing

### Development Guidelines

1. Follow TypeScript strict mode
2. Add proper error handling
3. Include comprehensive logging
4. Update documentation for new features
5. Test with local blockchain setup

### Code Style

- Use TypeScript strict mode
- Follow existing code patterns
- Add JSDoc comments for public functions
- Use meaningful variable names

---

## 📋 Compliance Status

**BTP Report Compliance**: ✅ **100%**

All 7 modules (M1-M7) fully implemented:
- ✅ M1: Task Publishing with Escrow and Commit
- ✅ M2: Miner Selection and Key Derivation
- ✅ M3: Local Model Training and Gradient-Norm Scoring
- ✅ M4: Secure Aggregation, BSGS Recovery, Evaluation and Candidate Formation
- ✅ M5: Miner Verification Feedback
- ✅ M6: Aggregator Verify, Build Payload and Publish On-Chain
- ✅ M7: Smart Contract Reveal and Reward Distribution

**See**: [BACKEND_REVIEW.md](./BACKEND_REVIEW.md) for detailed compliance matrix

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🆘 Support

### Resources

- **API Documentation**: [TASK_API_DOCUMENTATION.md](./TASK_API_DOCUMENTATION.md)
- **Compliance Review**: [BACKEND_REVIEW.md](./BACKEND_REVIEW.md)
- **BTP Report**: `BTP_Ph1_report.pdf` - Chapter 4

### Common Issues

**Database Connection**:
```bash
# Check PostgreSQL is running
# Verify DATABASE_URL in .env
```

**Blockchain Connection**:
```bash
# Check Ganache/Hardhat node is running
# Verify RPC_URL in .env
```

**Prisma Issues**:
```bash
# Regenerate Prisma client
npm run prisma:generate
```

---

**🚀 HealChain Backend - Production Ready!**
