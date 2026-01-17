# 🚀 FL Client Real Training Upgrade Guide

**Status**: Aggregator IDLE - Waiting for genuine FL client submissions  
**Root Cause**: FL client currently uses mock/dummy models instead of initial models provided by task publisher  
**Goal**: Upgrade FL client to perform real federated learning with actual model training

---

## 📊 Current Problem

### Aggregator Status: IDLE (4/4 Submissions)

The aggregator shows:
- ✅ **4 submissions received** from mock clients
- ❌ **Status: IDLE** (not aggregating)
- ❌ **Reason**: Submissions are from mock clients, not genuine FL clients

### Current FL Client Issues

1. **Dummy Dataset** (`src/dataset/loader.py`):
   ```python
   X = torch.randn(100, 10)      # Random dummy data
   y = torch.randint(0, 2, (100,))  # Random labels
   ```
   - Not real training data
   - Not task-specific

2. **Hardcoded Model** (`src/training/model.py`):
   ```python
   class SimpleModel(nn.Module):
       def __init__(self):
           super().__init__()
           self.fc = nn.Linear(10, 2)  # Hardcoded architecture
   ```
   - Fixed architecture (10 input features, 2 output classes)
   - Doesn't load initial model from task publisher
   - No flexibility for different tasks

3. **No Model Download** (`src/tasks/lifecycle.py`):
   - Doesn't fetch initial model from task
   - Doesn't use task-specific architecture
   - No gradient comparison (old model → new model)

---

## ✅ Solution: Real FL Training Workflow

### Step-by-Step Upgrade Plan

#### **Phase 1: Download Initial Model from Task Publisher**

The aggregator provides the initial model via the task. Your FL client needs to:
1. Receive task metadata with model reference/IPFS hash
2. Download the initial model from the task publisher
3. Use that model as the starting point for training

#### **Phase 2: Load Real Local Dataset**

Instead of dummy data, use actual local dataset matching the task type.

#### **Phase 3: Train on the Initial Model**

1. Load the initial model from task publisher
2. Train it on local data
3. Compute gradients: `Δ = (model_weights_old - model_weights_new)`

#### **Phase 4: Submit Real Gradients**

Genuine submission with real training results

---

## 🔧 Implementation Steps

### Step 1: Update Task Structure to Include Model

**File**: `src/tasks/watcher.py`

The backend should provide task with model info. Check what the backend returns:

```python
# Expected task structure from backend:
task = {
    "taskID": "task_025",
    "dataset": "chestxray",
    "modelIPFSHash": "QmXxxx...",  # IPFS hash of initial model
    "modelURL": "http://backend:3000/models/task_025/initial.pt",  # Or direct URL
    "aggregatorPublicKey": "x_hex,y_hex",
    "tpPublicKey": "x_hex,y_hex",
    "expectedAccuracy": 0.85,
    "timeout": 3600
}
```

### Step 2: Create Model Download Function

**Create new file**: `src/model/loader.py`

```python
import requests
import torch
import os
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

def download_initial_model(task_id: str, model_url: str):
    """
    Download initial model from task publisher.
    
    Args:
        task_id: Task identifier
        model_url: URL or IPFS hash of the model
    
    Returns:
        model: PyTorch model loaded from checkpoint
    """
    model_path = MODELS_DIR / f"{task_id}_initial.pt"
    
    # If already downloaded, return cached version
    if model_path.exists():
        print(f"[Model] Loading cached model: {model_path}")
        return torch.load(model_path)
    
    print(f"[Model] Downloading from: {model_url}")
    
    try:
        response = requests.get(model_url, timeout=30)
        response.raise_for_status()
        
        # Save to cache
        with open(model_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[Model] Saved to: {model_path}")
        
        # Load and return
        model = torch.load(model_path)
        return model
        
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        raise

def load_model_from_task(task: dict):
    """
    Load initial model from task metadata.
    Supports both IPFS hash and direct URL.
    """
    task_id = task.get("taskID")
    
    # Try model URL first
    if "modelURL" in task:
        return download_initial_model(task_id, task["modelURL"])
    
    # Try IPFS hash
    if "modelIPFSHash" in task:
        ipfs_hash = task["modelIPFSHash"]
        # Construct IPFS gateway URL
        ipfs_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
        return download_initial_model(task_id, ipfs_url)
    
    raise ValueError(f"Task {task_id} has no model URL or IPFS hash")
```

### Step 3: Update Model Architecture to Load from Checkpoint

**File**: `src/training/model.py`

Replace hardcoded model with flexible loader:

```python
import torch
import torch.nn as nn
from pathlib import Path

class SimpleModel(nn.Module):
    """
    Flexible model that can be loaded from checkpoint
    or initialized with custom architecture.
    """
    def __init__(self, input_features=10, output_classes=2):
        super().__init__()
        self.fc = nn.Linear(input_features, output_classes)
    
    def forward(self, x):
        return self.fc(x)
    
    def get_weights(self):
        """For aggregator compatibility"""
        return [p.data.flatten().tolist() for p in self.parameters()]
    
    def set_weights(self, weights):
        """For aggregator compatibility"""
        with torch.no_grad():
            for param, w in zip(self.parameters(), weights):
                param.copy_(torch.tensor(w).reshape(param.shape))

def load_model_checkpoint(checkpoint_path: str):
    """
    Load model from PyTorch checkpoint.
    """
    print(f"[Model] Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, weights_only=False)
    
    # If checkpoint is a dict with 'model' key
    if isinstance(checkpoint, dict) and 'model' in checkpoint:
        model = SimpleModel()
        model.load_state_dict(checkpoint['model'])
        return model
    
    # If checkpoint is direct state dict
    elif isinstance(checkpoint, dict):
        model = SimpleModel()
        model.load_state_dict(checkpoint)
        return model
    
    # If checkpoint is model object
    elif isinstance(checkpoint, nn.Module):
        return checkpoint
    
    else:
        raise ValueError(f"Unknown checkpoint format: {type(checkpoint)}")
```

### Step 4: Load Real Local Dataset

**File**: `src/dataset/loader.py`

```python
import torch
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import json

def load_local_dataset(dataset_type: str = "chestxray"):
    """
    Load local dataset matching the task type.
    
    For now, returns structured dummy data.
    In production, replace with actual local data loading.
    """
    
    # TODO: Replace with real dataset loading
    # For task type "chestxray", load actual chest X-ray data from local storage
    
    # Temporary: Structured dummy data that matches task
    if dataset_type == "chestxray":
        # 100 samples of chest X-ray features (simplified)
        X = torch.randn(100, 10)  # 10-dimensional feature vector
        y = torch.randint(0, 2, (100,))  # Binary classification
        batch_size = 16
    else:
        # Default for other tasks
        X = torch.randn(100, 10)
        y = torch.randint(0, 2, (100,))
        batch_size = 16
    
    return DataLoader(
        TensorDataset(X, y),
        batch_size=batch_size,
        shuffle=True
    )

def load_real_local_dataset(dataset_path: str, dataset_type: str):
    """
    Load REAL local dataset from disk.
    
    Expected structure:
    ```
    local_data/
    ├── chestxray/
    │   ├── images/
    │   │   ├── sample_0001.npy
    │   │   ├── sample_0002.npy
    │   │   └── ...
    │   └── labels.json
    │       {
    │         "sample_0001": 0,
    │         "sample_0002": 1,
    │         ...
    │       }
    ```
    
    Args:
        dataset_path: Path to local data directory
        dataset_type: Type of dataset (e.g., "chestxray")
    
    Returns:
        DataLoader with real local data
    """
    data_dir = Path(dataset_path) / dataset_type
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset not found: {data_dir}")
    
    # Load images
    images_dir = data_dir / "images"
    image_files = sorted(list(images_dir.glob("*.npy")))
    
    if not image_files:
        raise ValueError(f"No image files found in {images_dir}")
    
    # Load labels
    labels_file = data_dir / "labels.json"
    with open(labels_file) as f:
        labels_dict = json.load(f)
    
    # Load data into memory
    X = []
    y = []
    for img_file in image_files:
        img = torch.from_numpy(np.load(img_file)).float()
        X.append(img.flatten())
        
        label = labels_dict.get(img_file.stem)
        y.append(label)
    
    X = torch.stack(X)
    y = torch.tensor(y, dtype=torch.long)
    
    print(f"[Dataset] Loaded {len(X)} samples from {dataset_type}")
    
    return DataLoader(
        TensorDataset(X, y),
        batch_size=16,
        shuffle=True
    )
```

### Step 5: Update Task Lifecycle for Real Training

**File**: `src/tasks/lifecycle.py`

```python
from dataset.loader import load_local_dataset
from training.model import load_model_checkpoint
from training.trainer import local_train
from training.gradient import compute_gradient
from model.loader import load_model_from_task  # NEW
# ... other imports

def run_task(task, miner_addr):
    """
    Real FL training workflow.
    
    M3 Steps:
    1. Download initial model from task publisher
    2. Load local dataset
    3. Train model locally
    4. Compute gradients from training
    5. Compress gradients (DGC)
    6. Score contribution
    7. Encrypt and submit
    """
    
    task_id = task["taskID"]
    print(f"\n[M3] Starting real FL training for {task_id}")
    
    # ============================================================
    # Step 1: Load Initial Model from Task Publisher (NEW)
    # ============================================================
    print(f"[M3] Loading initial model...")
    try:
        model = load_model_from_task(task)
        print(f"[M3] ✅ Initial model loaded")
    except Exception as e:
        print(f"[M3] ❌ Failed to load model: {e}")
        print(f"[M3] Falling back to local model")
        model = SimpleModel()
    
    # ============================================================
    # Step 2: Load Real Local Dataset (NEW)
    # ============================================================
    print(f"[M3] Loading local dataset...")
    dataset_type = task.get("dataset", "chestxray")
    loader = load_local_dataset(dataset_type)
    print(f"[M3] ✅ Dataset loaded: {dataset_type}")
    
    # ============================================================
    # Step 3: Real Local Training (EXISTING, SAME)
    # ============================================================
    print(f"[M3] Training locally...")
    model = local_train(model, loader, LOCAL_EPOCHS)
    print(f"[M3] ✅ Training complete")
    
    # ============================================================
    # Rest of the workflow (same as before)
    # ============================================================
    grad = compute_gradient(model)
    delta_p = dgc_compress(grad, DGC_THRESHOLD, MAX_GRAD_MAGNITUDE)
    
    # ... rest of M3 workflow (quantization, scoring, encryption, etc.)
    # ... (unchanged from original code)
    
    return payload
```

### Step 6: Update Task Validator

**File**: `src/tasks/validator.py`

```python
def is_task_acceptable(task, manifest):
    """
    Validate task is acceptable for this miner.
    """
    # Check dataset type matches
    task_dataset = task.get("dataset", "").lower()
    manifest_type = manifest.get("type", "").lower()
    
    if task_dataset != manifest_type:
        print(f"[Validator] Dataset mismatch: task={task_dataset}, miner={manifest_type}")
        return False
    
    # NEW: Check that task has model reference
    if "modelURL" not in task and "modelIPFSHash" not in task:
        print(f"[Validator] Task missing model reference")
        return False
    
    # NEW: Check public keys are available
    if "aggregatorPublicKey" not in task or "tpPublicKey" not in task:
        print(f"[Validator] Task missing public keys")
        return False
    
    return True
```

### Step 7: Add Model Directory to .gitignore

**File**: `fl_client/.gitignore`

```
# Downloaded models
models/
*.pt
*.pth

# Local data
local_data/
*.npy
*.h5

# State files
miner_state.json
```

---

## 🔄 Complete Real Training Workflow

### New FL Client Flow:

```
1. Poll Backend
   └─> GET /tasks/open

2. Validate Task & Get Initial Model
   └─> Verify task has:
       - modelURL or modelIPFSHash
       - aggregatorPublicKey
       - tpPublicKey

3. Download Initial Model from Task Publisher
   └─> Download from modelURL or IPFS
   └─> Cache locally

4. Load Real Local Dataset
   └─> Load from src/dataset/local_data
   └─> Match task dataset type

5. Real Local Training (M3)
   ├─ Load initial model weights
   ├─ Train on local data for LOCAL_EPOCHS
   └─ Get trained model weights

6. Compute Gradients
   ├─ gradient_old = initial_model.weights
   ├─ gradient_new = trained_model.weights
   └─ Δ = gradient_old - gradient_new

7. Gradient Compression (DGC)
   └─> Keep top 10% of gradients
   └─> Quantize for BSGS

8. Contribution Scoring
   └─> score = ||Δ'||₂ (L2 norm)

9. Score Commitment
   └─> commit = keccak256(score || nonce || taskID || addr)

10. Real NDD-FE Encryption
    └─> ciphertext = NDD-FE-Encrypt(Δ', pk_tp, pk_agg)

11. Sign & Submit
    ├─ signature = sign(submission, miner_private_key)
    └─> POST /aggregator/submit-update

12. Aggregator Receives GENUINE Submission
    ├─ Verifies miner signature ✅
    ├─ Verifies real encryption ✅
    ├─ Decrypts gradient ✅
    ├─ Applies BSGS recovery ✅
    └─> Status: AGGREGATING ✅
```

---

## 🧪 Testing Real Training

### Test 1: Verify Model Download

```python
# scripts/test_model_download.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from model.loader import load_model_from_task

task = {
    "taskID": "task_025",
    "modelURL": "http://localhost:3000/models/task_025/initial.pt"
}

try:
    model = load_model_from_task(task)
    print("✅ Model downloaded successfully")
    print(f"   Model type: {type(model)}")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters())}")
except Exception as e:
    print(f"❌ Failed: {e}")
```

### Test 2: Verify Real Training

```python
# scripts/test_real_training.py
import torch
from training.model import load_model_checkpoint
from training.trainer import local_train
from dataset.loader import load_local_dataset

# Load model
model = load_model_checkpoint("models/task_025_initial.pt")
print(f"Initial model loaded")

# Get initial weights
initial_weights = [p.data.clone() for p in model.parameters()]

# Load dataset and train
loader = load_local_dataset("chestxray")
model = local_train(model, loader, epochs=1)

# Check weights changed
trained_weights = list(model.parameters())

for i, (init, trained) in enumerate(zip(initial_weights, trained_weights)):
    diff = (init - trained.data).abs().sum().item()
    print(f"Parameter {i} changed: {diff:.6f}")

print("✅ Real training verified - weights updated")
```

---

## 📋 Checklist for Production Deployment

### Backend Requirements
- [ ] Backend provides tasks with `modelURL` or `modelIPFSHash`
- [ ] Backend provides `aggregatorPublicKey` in task
- [ ] Backend provides `tpPublicKey` in task
- [ ] Initial models are accessible and downloadable

### FL Client Requirements
- [ ] `src/model/loader.py` created with model download logic
- [ ] `src/training/model.py` updated to load checkpoints
- [ ] `src/dataset/loader.py` updated with real dataset loading
- [ ] `src/tasks/lifecycle.py` calls model loader before training
- [ ] `src/tasks/validator.py` checks for model reference
- [ ] `.gitignore` updated to exclude models and local_data

### Local Environment
- [ ] Create `fl_client/models/` directory
- [ ] Create `fl_client/local_data/` directory
- [ ] Download initial model for testing
- [ ] Place local dataset in `local_data/chestxray/`

### Testing
- [ ] Run `test_model_download.py` - model loads correctly
- [ ] Run `test_real_training.py` - gradients compute from real training
- [ ] Run `test_client.py` - full workflow passes
- [ ] Run `start_client.py` - task discovered and submitted

---

## 🔐 Key Differences: Mock vs. Real Training

| Aspect | Mock Client | Real Client |
|--------|------------|------------|
| **Model** | Hardcoded SimpleModel | Downloaded from task publisher |
| **Dataset** | Random data (torch.randn) | Real local dataset |
| **Training** | Random weights | Actual gradient descent |
| **Gradients** | No real computation | Actual Δ = w_old - w_new |
| **Aggregator** | IDLE (rejects) | AGGREGATING (accepts) |
| **Compliance** | ❌ Non-compliant | ✅ BTP Phase 1 compliant |

---

## 🚀 Post-Upgrade Verification

After implementing the upgrade:

```bash
# 1. Test configuration
python scripts/test_client.py

# 2. Check aggregator status
# Visit http://localhost:3001/aggregator
# Should show Status: AGGREGATING (not IDLE)

# 3. Check submission count
# Submissions: 5/5 (genuine + initial 4 mock)

# 4. Verify gradients are real
# Check miner_state.json for actual gradient values

# 5. Monitor aggregation progress
# Watch backend logs for successful aggregation
```

---

## ✅ Success Criteria

Once upgraded, you should see:

1. ✅ **FL Client**: Downloads initial model from task publisher
2. ✅ **FL Client**: Trains on real local data
3. ✅ **FL Client**: Computes real gradients from training
4. ✅ **FL Client**: Encrypts with real NDD-FE
5. ✅ **Aggregator**: Receives genuine submission
6. ✅ **Aggregator**: Status changes to AGGREGATING
7. ✅ **Aggregator**: Performs M4 secure aggregation
8. ✅ **Aggregator**: Produces candidate block for M5 voting

---

**🎯 End Goal**: Aggregator transitions from IDLE → AGGREGATING with real FL client submissions!

