# HealChain

Blockchain-assisted, privacy-preserving federated learning with secure aggregation, on-chain publication, and commit-reveal reward distribution.

This repository implements the full protocol lifecycle (M1-M7) across:
- `frontend/` (user workflow UI)
- `backend/` (coordination API + persistence + chain bridge)
- `fl_client/` (miner-side local training and secure submission)
- `aggregator/` (secure aggregation, consensus, candidate generation)
- `contracts/` (Escrow, BlockPublisher, RewardDistribution, StakeRegistry)

---

## 1) Project Objective

HealChain enables multiple miners to collaboratively train a model without sharing raw data. The system enforces:
- privacy of local updates (encrypted sparse submissions),
- cryptographic commitments for fairness,
- consensus before publication,
- traceable on-chain state for final outcomes,
- reward distribution tied to protocol rules.

The implementation follows your BTP algorithm sequence:
- **M1** Task publishing + escrow lock + accuracy commit
- **M2** Miner registration + selection + key derivation
- **M3** Local training + DGC compression + score commit + secure submission
- **M4** Secure aggregation + decryption + update + evaluation
- **M5** Decentralized verification feedback + majority decision
- **M6** On-chain publish of verified block metadata
- **M7** Reveal and reward distribution

---

## 2) Functional Architecture

### 2.1 Components

1. **Frontend (`frontend`)**
- Next.js app (port `3001` by default)
- Task publishing, mining participation, verification/reveal/reward UI
- Wallet-based signing and contract calls

2. **Backend (`backend`)**
- Express + TypeScript API (port `3000` by default)
- Prisma/PostgreSQL persistence
- Routes for task lifecycle, aggregator relay, verification, rewards
- Bridge between off-chain pipeline and contracts

3. **FL Client (`fl_client`)**
- Python service for miner-side training and submission
- Runs local model training, DGC compression, scoring, commitment, encryption
- Service endpoint (port `5001`) used by backend/frontend orchestration

4. **Aggregator (`aggregator`)**
- Python service for secure aggregation (port `5002`)
- Strict sparse payload validation, NDD-FE decrypt, BSGS recovery
- M4/M5 orchestration and candidate construction

5. **Contracts (`contracts`)**
- `HealChainEscrow.sol` (M1 state and funds lock)
- `BlockPublisher.sol` (M6 publish metadata)
- `RewardDistribution.sol` (M7 reveal + distribute)
- `StakeRegistry.sol` (stake-related support)

### 2.2 High-Level Data Flow

1. Publisher creates task and locks escrow (M1).
2. Miners register and are selected (M2).
3. Miners train locally and submit encrypted sparse updates + score commit (M3).
4. Aggregator decrypts/recovers aggregate update, evaluates model, prepares candidate (M4).
5. Participants provide M5 feedback; majority determines proceed/reject.
6. Verified candidate metadata is published on-chain (M6).
7. Publisher/miners reveal, then rewards are distributed (M7).

---

## 3) Implementation Highlights

### 3.1 Secure Aggregation Path (M4)

- Strict sparse schema enforcement (`format`, `protocolVersion`, `ctr`, `totalSize`, `nonzeroIndices`, `values`, `baseMask`).
- NDD-FE sparse decrypt + BSGS recovery with tunable worker/chunk settings.
- Carry-forward behavior for iterative retrain: low-accuracy rounds can publish `W_new` artifact for next round start.
- Runtime evaluator hooks supported (static fallback can be disabled).

### 3.2 Consensus and Verification (M5)

- Candidate validation feedback collected from participants.
- Signature and consistency checks in backend/aggregator paths.
- Majority-based decision controls proceed/reject path.

### 3.3 Publication and Rewards (M6/M7)

- Block publication through BlockPublisher with strict metadata checks in backend flow.
- Commit-reveal pipeline for publisher accuracy and miner score reveals.
- Distribution path supports current reward contract logic (including fallback behavior where configured in deployed contract version).

---

## 4) Repository Layout

```text
healchain/
  frontend/      # Next.js UI
  backend/       # Express + Prisma API
  fl_client/     # Python miner service
  aggregator/    # Python aggregation service
  contracts/     # Solidity + Hardhat deployment/test scripts
  artifacts/     # Generated artifacts (models/validation/etc.)
```

---

## 5) Prerequisites

- **OS**: Windows/Linux/macOS (examples below are PowerShell-friendly)
- **Node.js**: 18+
- **Python**: 3.11+
- **PostgreSQL**: 14+
- **Ganache** (or other EVM RPC) for local chain
- **IPFS node** (IPFS Desktop/Kubo) for model/dataset artifact flow

---

## 6) Environment Configuration

Use each module-local env file:

- `contracts/.env`
- `backend/.env.development` (dev), `backend/.env.production` (prod)
- `frontend/.env.local`
- `aggregator/.env`
- `fl_client/.env`

Never commit private keys in production.

### 6.1 Backend (`backend/.env.development`) required

- `PORT=3000`
- `NODE_ENV=development`
- `DATABASE_URL=...`
- `RPC_URL=http://127.0.0.1:7545`
- `BACKEND_PRIVATE_KEY=0x...`
- `ESCROW_ADDRESS=0x...`
- `BLOCK_PUBLISHER_ADDRESS=0x...`
- `REWARD_CONTRACT_ADDRESS=0x...`
- `STAKE_REGISTRY_ADDRESS=0x...` (if used by your routes/features)

### 6.2 Frontend (`frontend/.env.local`) required

- `NEXT_PUBLIC_BACKEND_URL=http://localhost:3000`
- `NEXT_PUBLIC_ESCROW_ADDRESS=0x...`
- `NEXT_PUBLIC_BLOCK_PUBLISHER_ADDRESS=0x...`
- `NEXT_PUBLIC_REWARD_ADDRESS=0x...`
- `NEXT_PUBLIC_STAKE_REGISTRY_ADDRESS=0x...`

### 6.3 Aggregator (`aggregator/.env`) required baseline

- `BACKEND_URL=http://localhost:3000`
- `AGGREGATOR_SK=...`
- `AGGREGATOR_ADDRESS=0x...`
- `AGGREGATOR_PK=x_hex,y_hex`
- `TP_PUBLIC_KEY=x_hex,y_hex`
- `AGGREGATOR_PORT=5002`

Common runtime flags:
- `AGGREGATOR_REQUIRE_RUNTIME_EVALUATOR`
- `AGGREGATOR_VALIDATION_DATA_PATH` or `AGGREGATOR_VALIDATION_DATA_LINK`
- `MODEL_ARTIFACT_USE_IPFS`, `MODEL_ARTIFACT_IPFS_API_URL`, `MODEL_ARTIFACT_IPFS_GATEWAY_URL`
- `NDD_FE_WORKERS`, `BSGS_WORKERS`, timeout/retry settings

### 6.4 FL Client (`fl_client/.env`) required baseline

- `BACKEND_URL=http://localhost:3000`
- `RPC_URL=http://localhost:7545`
- `CHAIN_ID=1337`
- `MINER_PRIVATE_KEY=0x...`
- `MINER_ADDRESS=0x...`
- `LOCAL_EPOCHS=1`
- `DGC_THRESHOLD=0.9`

---

## 7) Local Demo Setup (Development Mode)

Follow this sequence exactly.

### 7.1 Deploy contracts

```powershell
cd contracts
npm install
node scripts/deploy-final-working.mjs
```

Copy deployed addresses into backend/frontend env files.

### 7.2 Backend setup

```powershell
cd backend
npm install
npm run prisma:generate
npm run prisma:migrate
npm run dev
```

Backend runs at `http://localhost:3000`.

### 7.3 Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3001`.

### 7.4 Aggregator setup

```powershell
cd aggregator
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/start_api_service.py
```

Aggregator API runs at `http://localhost:5002`.

### 7.5 FL client setup (per miner)

```powershell
cd fl_client
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/start_service.py
```

FL miner service runs at `http://localhost:5001`.

Important:
- On one machine/port, run one miner service instance at a time and rotate miner key by restart.
- If you run multi-miner simulation, restart service for each miner identity.

---

## 8) End-to-End Demo Flow

1. Connect wallet in frontend.
2. Publish task (M1) with required accuracy, reward, deadline.
3. Register miners (M2) with valid proof/public key.
4. Start training for participants (M3) via frontend/backend trigger to FL client services.
5. Trigger aggregation (M4) once sufficient submissions are present.
6. Let participants submit verification feedback (M5).
7. Publish verified block (M6).
8. Perform reveal(s) and reward distribution (M7).

Validation checks:
- Task page timeline should progress M1 -> M7.
- Backend logs should confirm route success for each phase.
- Chain explorer (Ganache UI) should show block publish/reveal/distribute txs.

---

## 9) Production-Mode Guidance

Production mode here means long-running services and hardened infra (not local demo defaults).

### 9.1 Backend

```powershell
cd backend
npm ci
npm run prisma:generate
npm run build
npm start
```

- Set `NODE_ENV=production`.
- Use production DB + managed RPC + secret manager for keys.
- Run behind process manager/reverse proxy.

### 9.2 Frontend

```powershell
cd frontend
npm ci
npm run build
npm run start
```

- Serve behind reverse proxy/CDN.
- Ensure public env contract addresses match target network.

### 9.3 Python Services (Aggregator + FL client)

- Use dedicated venvs with locked dependencies.
- Run `python scripts/start_api_service.py` (aggregator) and `python scripts/start_service.py` (miners) under service manager.
- Configure robust timeouts/retries and monitoring.
- Keep private keys out of source-controlled `.env`.

### 9.4 Contracts

- Deploy to target chain with audited configuration.
- Update backend/frontend env addresses to those deployments.
- Freeze ABI versions used by backend/frontend to match deployed bytecode.

---

## 10) Troubleshooting

1. **`EADDRINUSE` on frontend/backend/aggregator/fl_client**
- Port already in use. Stop old process or change port.

2. **Frontend task timeline not updating**
- Verify backend task status transitions and API polling response.
- Check that M5/M6 success state is persisted in DB.

3. **Aggregator `Round reset failed`**
- Usually backend timeout or DB transaction timeout.
- Check backend logs around reset route and Prisma transaction duration.

4. **Aggregator BSGS very slow or stuck heartbeat**
- High unique sparse coordinate ratio can increase runtime sharply.
- Tune `BSGS_WORKERS`, `BSGS_CHUNK_SIZE`, dedup flags, and monitor CPU/memory.

5. **Model load/eval errors (`Base model is None`, missing evaluator)**
- Ensure initial/current model link is reachable and loadable.
- Configure runtime evaluator path/hook consistently.

6. **Reward `No scores` or zero distribution**
- Miner reveals did not produce nonzero on-chain score set (or commit/reveal mismatch).
- Confirm M7a and M7b values/nonces/commits are consistent with stored commitments.

7. **Invalid signature / key mismatch**
- Verify miner key/address/public key consistency across frontend, fl_client, backend records.

---

## 11) Useful Commands

1. Derive miner public key:
```powershell
cd fl_client
python scripts/derive_pubkey.py
```

2. Run backend build check:
```powershell
cd backend
npm run build
```

3. Run contract compile/test:
```powershell
cd contracts
npm run compile
npm test
```

---

## 12) Current Completion Status

Based on the current integrated codebase and recent strictness patches:
- Core protocol path M1-M7 is implemented across modules.
- Local demo is runnable end-to-end with proper env wiring and service startup order.

If you want, the next iteration can add a short "quickstart (15-minute demo)" section and a Docker Compose profile for one-command local startup.
