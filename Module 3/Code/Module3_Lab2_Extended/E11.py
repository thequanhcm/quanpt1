import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms

# Simple model
class SimpleMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28*28, 128),
            nn.ReLU(),
            nn.Linear(128, 10)
        )

    def forward(self, x):
        return self.linear(x)

# Prepare dataset (e.g., MNIST) and remove 1 sample
def get_dataset(remove_idx=0):
    transform = transforms.ToTensor()
    full_train = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
    removed_sample = full_train[remove_idx]
    remaining = torch.utils.data.Subset(full_train, [i for i in range(len(full_train)) if i != remove_idx])
    return remaining, removed_sample

def train_model(model, data_loader, epochs=1):
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    model.train()
    for epoch in range(epochs):
        for x, y in data_loader:
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

# Example
train_data, removed = get_dataset()
train_loader = torch.utils.data.DataLoader(train_data, batch_size=64, shuffle=True)
model = SimpleMLP()
train_model(model, train_loader)

def gradient_ascent_unlearn(model, x_target, y_target, lr=1e-2, steps=5):
    model.train()
    x_target = x_target.unsqueeze(0)
    y_target = torch.tensor([y_target])
    criterion = nn.CrossEntropyLoss()

    for _ in range(steps):
        output = model(x_target)
        loss = criterion(output, y_target)
        loss.backward()
        with torch.no_grad():
            for p in model.parameters():
                p.data += lr * p.grad  # Gradient ascent
                p.grad.zero_()

# Example: apply to removed sample
gradient_ascent_unlearn(model, *removed)

