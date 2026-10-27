import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import train_test_split

# Generate synthetic data: y = sin(x) + noise
np.random.seed(0)
X = np.random.uniform(-3, 3, size=(300, 1))
y = np.sin(X) + 0.1 * np.random.randn(*X.shape)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Convert to torch tensors
X_train_t = torch.tensor(X_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.float32)
X_test_t = torch.tensor(X_test, dtype=torch.float32)


# Define a simple MLP with Dropout
class MCDropoutModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(1, 100)
        self.dropout = nn.Dropout(0.1)
        self.fc2 = nn.Linear(100, 100)
        self.fc3 = nn.Linear(100, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)  # dropout is active during inference too
        x = F.relu(self.fc2(x))
        return self.fc3(x)


def train_model(model, X, y, epochs=500):
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.MSELoss()
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        output = model(X)
        loss = loss_fn(output, y)
        loss.backward()
        optimizer.step()


# Train MC Dropout model
mc_model = MCDropoutModel()
train_model(mc_model, X_train_t, y_train_t)

# Enable dropout during inference
mc_model.train()


# MC sampling
def predict_mc(model, X, n_samples=100):
    preds = []
    with torch.no_grad():
        for _ in range(n_samples):
            preds.append(model(X).cpu().numpy())
    return np.stack(preds)


# Predict on test input
x_plot = np.linspace(-4, 4, 100).reshape(-1, 1)
x_plot_t = torch.tensor(x_plot, dtype=torch.float32)
mc_preds = predict_mc(mc_model, x_plot_t, n_samples=100)

# Plot
mean_preds = mc_preds.mean(axis=0).squeeze()
std_preds = mc_preds.std(axis=0).squeeze()

plt.figure(figsize=(10, 5))
plt.plot(X_train, y_train, 'b.', label='Train Data')
plt.plot(x_plot, np.sin(x_plot), 'g--', label='True Function')
plt.plot(x_plot, mean_preds, 'r', label='MC Dropout Mean')
plt.fill_between(x_plot.squeeze(), mean_preds - 2 * std_preds, mean_preds + 2 * std_preds, color='r', alpha=0.3,
                 label='Uncertainty')
plt.legend()
plt.title("MC Dropout: Predictive Mean and Uncertainty")
plt.xlabel("x")
plt.ylabel("y")
plt.grid(True)
plt.show()


# Define a simple MLP (no dropout)
class EnsembleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 100),
            nn.ReLU(),
            nn.Linear(100, 100),
            nn.ReLU(),
            nn.Linear(100, 1)
        )

    def forward(self, x):
        return self.net(x)


# Train multiple models
def train_ensemble(n_models, X_train, y_train, epochs=500):
    ensemble = []
    for i in range(n_models):
        model = EnsembleModel()
        train_model(model, X_train, y_train, epochs=epochs)
        ensemble.append(model)
    return ensemble


# Train 5 models for the ensemble
ensemble_models = train_ensemble(5, X_train_t, y_train_t)


# Predict using ensemble
def predict_ensemble(models, X):
    preds = []
    with torch.no_grad():
        for model in models:
            model.eval()
            preds.append(model(X).cpu().numpy())
    return np.stack(preds)


ensemble_preds = predict_ensemble(ensemble_models, x_plot_t)

# Mean and uncertainty (std deviation across models)
ensemble_mean = ensemble_preds.mean(axis=0).squeeze()
ensemble_std = ensemble_preds.std(axis=0).squeeze()

# Plot comparison
plt.figure(figsize=(12, 6))
plt.plot(X_train, y_train, 'b.', label='Train Data')
plt.plot(x_plot, np.sin(x_plot), 'g--', label='True Function')
plt.plot(x_plot, ensemble_mean, 'orange', label='Ensemble Mean')
plt.fill_between(x_plot.squeeze(), ensemble_mean - 2 * ensemble_std, ensemble_mean + 2 * ensemble_std,
                 color='orange', alpha=0.3, label='Uncertainty')
plt.legend()
plt.title("Deep Ensemble: Predictive Mean and Uncertainty")
plt.xlabel("x")
plt.ylabel("y")
plt.grid(True)
plt.show()
