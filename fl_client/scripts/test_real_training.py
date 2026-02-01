import sys
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from training.model import SimpleModel
from training.trainer import local_train
from dataset.loader import load_local_dataset

print("Testing real training workflow...")

# 1. Initialize Model
model = SimpleModel()
print(f"✅ Initial model loaded")

# 2. Load Dataset (Synthetic for now, unless local_data exists)
loader = load_local_dataset("chestxray")
print(f"✅ Dataset loaded")

# 3. Train
initial_weights = [p.data.clone() for p in model.parameters()]
model = local_train(model, loader, epochs=1)
print(f"✅ Training completed")

# 4. Verify weights changed
trained_weights = list(model.parameters())
changed = False
for init, trained in zip(initial_weights, trained_weights):
    diff = (init - trained.data).abs().sum().item()
    if diff > 0:
        changed = True
        print(f"   Parameter changed by: {diff:.6f}")

if changed:
    print("✅ Real training verified - weights updated")
else:
    print("❌ Weights did not change! (Is learning rate 0?)")
