from torch.utils.data import DataLoader, TensorDataset
import torch

def load_local_dataset():
    # Dummy local dataset (replace with real one)
    X = torch.randn(100, 10)
    y = torch.randint(0, 2, (100,))
    return DataLoader(TensorDataset(X, y), batch_size=16)
