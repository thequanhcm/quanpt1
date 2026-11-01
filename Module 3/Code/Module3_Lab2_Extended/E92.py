import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset
import numpy as np
import matplotlib.pyplot as plt

# Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Data loaders
transform = transforms.Compose([transforms.ToTensor()])
mnist_train = datasets.MNIST(root="./data", train=True, download=True, transform=transform)
mnist_test = datasets.MNIST(root="./data", train=False, download=True, transform=transform)
fashion_test = datasets.FashionMNIST(root="./data", train=False, download=True, transform=transform)

train_loader = DataLoader(mnist_train, batch_size=64, shuffle=True)
test_loader = DataLoader(mnist_test, batch_size=64, shuffle=False)
ood_loader = DataLoader(fashion_test, batch_size=64, shuffle=False)

# CNN with Dropout
class CNNDropout(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout2d(0.25)
        self.fc1 = nn.Linear(9216, 128)
        self.dropout2 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        return self.fc2(x)

# Train model
def train(model, loader, epochs=5):
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters())
    criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            output = model(x)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
        print(f"Epoch {epoch+1} done")

model = CNNDropout()
train(model, train_loader)




######


from torch.nn.functional import softmax
from scipy.stats import entropy

# Enable dropout during inference
def enable_dropout(m):
    if isinstance(m, (nn.Dropout, nn.Dropout2d)):
        m.train()

# Predictive entropy from multiple MC passes
def mc_entropy(model, loader, n_passes=30):
    model.eval()
    model.apply(enable_dropout)

    entropies = []
    with torch.no_grad():
        for x, _ in loader:
            x = x.to(device)
            probs_mc = []

            for _ in range(n_passes):
                logits = model(x)
                probs = softmax(logits, dim=1)
                probs_mc.append(probs.cpu().numpy())

            probs_mc = np.stack(probs_mc)  # [n_passes, batch_size, num_classes]
            mean_probs = probs_mc.mean(axis=0)  # [batch_size, num_classes]
            ent = entropy(mean_probs.T)  # compute entropy for each sample
            entropies.extend(ent)

    return np.array(entropies)


entropy_mnist = mc_entropy(model, test_loader)
entropy_ood = mc_entropy(model, ood_loader)

plt.hist(entropy_mnist, bins=50, alpha=0.6, label="MNIST (In-Domain)")
plt.hist(entropy_ood, bins=50, alpha=0.6, label="Fashion-MNIST (OOD)")
plt.xlabel("Predictive Entropy")
plt.ylabel("Count")
plt.title("Uncertainty for In-Domain vs. OOD Samples")
plt.legend()
plt.grid(True)
plt.show()

