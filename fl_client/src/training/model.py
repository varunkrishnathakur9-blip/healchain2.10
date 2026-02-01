import torch
import torch.nn as nn
from pathlib import Path

class SimpleModel(nn.Module):
    """
    Flexible model that can be loaded from checkpoint
    or initialized with custom architecture.
    """
    def __init__(self, input_features=4096, output_classes=2):
        super().__init__()
        self.fc = nn.Linear(input_features, output_classes)
    
    def forward(self, x):
        # Auto-flatten if input is 4D (batch, channels, height, width)
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        return self.fc(x)
    
    def get_weights(self):
        """For aggregator compatibility"""
        return [p.data.flatten().tolist() for p in self.parameters()]
    
    def set_weights(self, weights):
        """For aggregator compatibility"""
        with torch.no_grad():
            for param, w in zip(self.parameters(), weights):
                param.copy_(torch.tensor(w).reshape(param.shape))

class SimpleCNN(nn.Module):
    """
    Basic CNN for 64x64 images
    """
    def __init__(self):
        super().__init__()
        # Input: (1, 64, 64)
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        # 32x32
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        # 16x16
        self.fc1 = nn.Linear(64 * 16 * 16, 128)
        self.fc2 = nn.Linear(128, 2)

    def forward(self, x):
        # Ensure input is (batch, 1, 64, 64)
        if x.dim() == 2:
            x = x.view(-1, 1, 64, 64)
            
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(-1, 64 * 16 * 16)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
    
    def get_weights(self):
        return [p.data.flatten().tolist() for p in self.parameters()]
    
    def set_weights(self, weights):
        with torch.no_grad():
            for param, w in zip(self.parameters(), weights):
                param.copy_(torch.tensor(w).reshape(param.shape))

# Simple ResNet Block
class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
            
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += identity
        out = self.relu(out)
        return out

class ResNet9(nn.Module):
    """
    Small ResNet-like architecture acceptable for local training
    """
    def __init__(self, num_classes=2):
        super().__init__()
        self.in_channels = 64
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.layer1 = self._make_layer(64, 2, stride=2)
        self.layer2 = self._make_layer(128, 2, stride=2)
        self.avg_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(128, num_classes)

    def _make_layer(self, out_channels, blocks, stride):
        layers = []
        layers.append(ResidualBlock(self.in_channels, out_channels, stride))
        self.in_channels = out_channels
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels))
        return nn.Sequential(*layers)

    def forward(self, x):
        if x.dim() == 2:
            x = x.view(-1, 1, 64, 64)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.avg_pool(out)
        out = out.view(out.size(0), -1)
        out = self.fc(out)
        return out
        
    def get_weights(self):
        return [p.data.flatten().tolist() for p in self.parameters()]
    
    def set_weights(self, weights):
        with torch.no_grad():
            for param, w in zip(self.parameters(), weights):
                param.copy_(torch.tensor(w).reshape(param.shape))

def load_model_checkpoint(checkpoint_path: str):
    """
    Load model from PyTorch checkpoint.
    """
    print(f"[Model] Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, weights_only=False)
    
    # Check if checkpoint is a model object instance
    if isinstance(checkpoint, nn.Module):
        return checkpoint
        
    # Check if it's a state dict
    state_dict = checkpoint
    if isinstance(checkpoint, dict) and 'model' in checkpoint:
        state_dict = checkpoint['model']
        
    # Heuristic to detect model type from state_dict keys
    if any('layer1' in k for k in state_dict.keys()):
        print("[Model] Detected ResNet architecture")
        model = ResNet9()
    elif any('conv1' in k for k in state_dict.keys()):
        print("[Model] Detected CNN architecture")
        model = SimpleCNN()
    else:
        print("[Model] Detected Linear architecture")
        model = SimpleModel()
        
    model.load_state_dict(state_dict)
    return model
