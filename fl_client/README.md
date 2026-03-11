# HealChain FL Client (Miner)

FL client for HealChain miner-side workflow.

Current implementation status:
- M3 implemented: local training, gradient processing, secure submission.
- Integrated with backend + aggregator flow for M4 orchestration.
- Startup prompt workflow enabled for miner identity.

## Protocol Coverage
- `M3` Local training + secure submission: implemented and active.
- `M5` Candidate verification support: available via `scripts/verify_candidate.py`.
- `M7` Reveal utilities: available via `scripts/reveal_scores.py` and `scripts/reveal_accuracy.py`.

## What This Client Does
- Discovers tasks and validates compatibility.
- Runs local training.
- Computes and compresses gradients.
- Quantizes and encrypts sparse update payloads.
- Creates score commitment and miner signature.
- Submits payload to backend for aggregation.

## Important Security Rule
- Each miner must use a unique `MINER_PRIVATE_KEY` per task.
- Reusing one private key across miners causes duplicate `miner_pk` and invalid protocol behavior.

## Prerequisites
- Python 3.11+
- Virtual environment
- Backend running (default `http://localhost:3000`)
- Aggregator API service running
- Local blockchain (Ganache/Hardhat) if on-chain steps are used

## Environment Guide (Multiple venvs)

If you maintain two virtual environments for `fl_client` (for example `venv` and `.venv`), use one consistently per terminal session and verify which interpreter is active before running scripts.

Recommended checks:
```powershell
python --version
python -c "import sys; print(sys.executable)"
```

Common activation commands (Windows PowerShell):
```powershell
# venv
venv\Scripts\Activate

# .venv (if present)
.\.venv\Scripts\Activate.ps1
```

Deactivate current environment before switching:
```powershell
deactivate
```

Reinstall dependencies in each environment you actually use:
```powershell
pip install -r requirements.txt
```

Operational recommendation:
- Use one dedicated venv for day-to-day FL runs.
- Keep the second venv for experiments/testing only.
- Do not mix runs for the same task across different venvs unless dependencies are identical.

## Setup
1. Create and activate venv:
```powershell
cd fl_client
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install deps:
```powershell
pip install -r requirements.txt
```

3. Configure `.env` from `.env.example`.

Required keys:
- `BACKEND_URL`
- `MINER_PRIVATE_KEY` (can be blank in file; prompted at service startup)
- `MINER_ADDRESS` (auto-derived from entered private key at startup)
- `TP_PUBLIC_KEY` (auto-refreshed per task)
- `AGGREGATOR_PK` (auto-refreshed per task)

Environment sanity checks before each miner run:
```powershell
python -c "import os; print('MINER_ADDRESS=', os.getenv('MINER_ADDRESS')); print('HAS_MINER_KEY=', bool(os.getenv('MINER_PRIVATE_KEY')))"
```

## Startup Prompt Workflow (Current)

When `start_service.py` starts, it now:
1. Clears `MINER_PRIVATE_KEY` in `.env`.
2. Prompts in terminal for miner private key.
3. Validates key format.
4. Derives and updates `MINER_ADDRESS`.
5. Persists both values in `.env`.

During `/api/train`, it now:
1. Fetches latest task keys from backend (`/tasks/:taskID/public-keys`).
2. Updates `.env` with `TP_PUBLIC_KEY` and `AGGREGATOR_PK`.
3. Validates miner key against backend registration (`/miners/:taskID/key-status`).

## Multi-Miner Usage (One Machine, One Port)
1. Stop FL client service.
2. Start service again and enter next miner's private key when prompted.
3. Trigger training + submit for that miner.
4. Repeat per miner.

## Run Modes

### Service mode (used by backend orchestration)
```powershell
python scripts/start_service.py
```

Available endpoints:
- `POST /api/train`
- `GET /api/train/status`
- `POST /api/submit`
- `GET /api/health`

### Script mode (direct run)
```powershell
python scripts/start_client.py
```

## Backend/API Touchpoints
- `GET /tasks/open` for task discovery.
- `GET /tasks/:taskID/public-keys` for task cryptographic keys.
- `POST /aggregator/submit-update` for gradient submission.
- `GET /miners/:taskID/key-status` for preflight key uniqueness validation.

## Submission Payload Format (Current)

The client now submits sparse ciphertext metadata and values together:

```json
{
  "ciphertext": {
    "format": "sparse",
    "protocolVersion": "nddfe_sparse_v1",
    "ctr": 1,
    "totalSize": 2578387,
    "nonzeroIndices": [12, 71, 405],
    "values": ["x1,y1", "x2,y2", "x3,y3"],
    "baseMask": "xb,yb"
  }
}
```

Notes:
- `values` contains encrypted points only for `nonzeroIndices`.
- `baseMask` is required by the aggregator for NDD-FE decrypt.
- `totalSize` preserves target dense vector length for reconstruction.
- `protocolVersion` and `ctr` are mandatory and must match aggregator expectations.
- Miner signature now binds the canonical sparse ciphertext JSON (not just joined point values).

## Useful Scripts
- `python scripts/test_client.py` quick environment/connectivity validation.
- `python scripts/derive_pubkey.py` derive miner public key from `MINER_PRIVATE_KEY`.
- `python scripts/check_balance.py` verify miner account balance.
- `python scripts/check_task_status.py` inspect task state.
- `python scripts/verify_candidate.py` M5 candidate verification.
- `python scripts/reveal_scores.py` M7 score reveal flow.
- `python scripts/reveal_accuracy.py` publisher accuracy reveal helper.

## Integration Notes (Current)
- Backend validates miner key uniqueness per task.
- FL service preflight checks key status before training/submission.
- FL service prompts private key at startup and writes `MINER_PRIVATE_KEY` + `MINER_ADDRESS` to `.env`.
- FL service syncs `TP_PUBLIC_KEY` + `AGGREGATOR_PK` from backend per task during training start.
- Aggregator expects strict sparse ciphertext metadata (`format`, `protocolVersion`, `ctr`, `totalSize`, `nonzeroIndices`, `values`, `baseMask`).
- Legacy submissions without strict sparse metadata are rejected.
- If key conflict exists, training/submission is rejected with a clear error.

## Troubleshooting

`Miner key validation failed`
- Another miner already uses the same `miner_pk` for the task.
- Fix: update `.env` to a unique `MINER_PRIVATE_KEY`, restart service, retrain/resubmit.

`FL service configured for miner X but request is for Y`
- You are using one running service with different miner address.
- Fix: stop service and restart; enter the correct miner private key in startup prompt.

`Task not found` or backend errors
- Verify backend URL and backend server status.

`ModuleNotFoundError` while running scripts
- Run from `fl_client` root with activated venv.
- If needed, set `PYTHONPATH` to `src` for direct script execution.

## Suggested Ops Sequence (Task Run)
1. Start blockchain node (Ganache/Hardhat) if required.
2. Start backend.
3. Start aggregator API service.
4. For each miner, restart FL service and enter miner private key at prompt, then train + submit.
5. Start aggregation from frontend/backend.

## Notes
- This client assumes backend is orchestration/relay and cryptography is client-side.
- Do not rotate a miner key mid-task; keep one keypair per miner for the full task lifecycle.

---

## Extended Reference (Detailed)

This section preserves detailed operational guidance from earlier documentation, updated to current behavior.

### M3 Workflow Detail
1. Task discovery and compatibility validation.
2. Local model training.
3. Gradient computation.
4. DGC compression.
5. Quantization and bounds checks.
6. Contribution scoring (`L2` norm).
7. Score commit generation.
8. NDD-FE encryption using `TP_PUBLIC_KEY` and `AGGREGATOR_PK`.
9. Build canonical sparse ciphertext payload with `protocolVersion`, `ctr`, `nonzeroIndices`, `values`, and `baseMask`.
10. Miner signature generation and submission.

### M5/M7 Utilities
- M5 verification: `python scripts/verify_candidate.py`
- M7 reveal helpers:
  - `python scripts/reveal_scores.py`
  - `python scripts/reveal_accuracy.py`

### Full Startup Order (Expanded)
1. Start blockchain node.
2. Deploy/verify contracts.
3. Start backend (`npm run dev`).
4. Start aggregator API service.
5. Start FL client service for miner A (after `.env` update).
6. Train + submit miner A.
7. Stop FL client, update `.env` for miner B, restart, train + submit.
8. Repeat for all miners.
9. Trigger aggregation.

### Additional Troubleshooting
- `Invalid wallet signature`:
  - Ensure wallet auth `address/message/signature` are from the same signer session.
- `Task not accepting updates`:
  - Task status is not `OPEN`; verify in backend.
- `Gradient already submitted by this miner`:
  - Submission exists; clear gradients (publisher admin action) only if restart is intentional.
- `Insufficient valid submissions`:
  - Verify each miner used distinct keypair and submitted successfully.
- `Ciphertext/weight mismatch`:
  - Usually indicates participant/submission inconsistency; re-check miner submissions and metadata.
- `Sparse payload rejected (missing protocolVersion/ctr/baseMask/indices/totalSize)`:
  - Client version or payload format is stale; update FL client and resubmit all miners for the task.

### Production Checklist
- Python 3.11+ in active venv.
- Correct venv active (`sys.executable` checked).
- Startup prompt completed and `.env` updated for current miner identity.
- Backend and aggregator services healthy.
- Miner has sufficient chain balance if on-chain calls are required.
- Successful training and submission confirmed before switching to next miner.
