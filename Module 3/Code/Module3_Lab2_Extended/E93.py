import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import numpy as np
# Load dataset
url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00242/ENB2012_data.xlsx"
df = pd.read_excel(url)

# Use features and one of the two targets (e.g. Heating Load)
X = df.iloc[:, :8].values
y = df.iloc[:, 8].values.reshape(-1, 1)  # Heating load

# Normalize
scaler_X = StandardScaler()
scaler_y = StandardScaler()
X = scaler_X.fit_transform(X)
y = scaler_y.fit_transform(y)

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

###

import pyro
import pyro.distributions as dist
from pyro.nn import PyroSample, PyroModule
from pyro.infer.autoguide import AutoDiagonalNormal
from pyro.infer import SVI, Trace_ELBO
from pyro.optim import DCTAdam
import torch
import torch.nn as nn

from matplotlib import pyplot as plt
# Bayesian Neural Network
class BNN(PyroModule):
    def __init__(self):
        super().__init__()
        self.fc1 = PyroModule[nn.Linear](8, 50)
        self.fc1.weight = PyroSample(dist.Normal(0., 1.).expand([50, 8]).to_event(2))
        self.fc1.bias = PyroSample(dist.Normal(0., 1.).expand([50]).to_event(1))

        self.fc2 = PyroModule[nn.Linear](50, 1)
        self.fc2.weight = PyroSample(dist.Normal(0., 1.).expand([1, 50]).to_event(2))
        self.fc2.bias = PyroSample(dist.Normal(0., 1.).expand([1]).to_event(1))

    def forward(self, x, y=None):
        x = torch.relu(self.fc1(x))
        mean = self.fc2(x).squeeze(-1)
        sigma = pyro.sample("sigma", dist.Uniform(0., 1.))  # Aleatoric uncertainty
        with pyro.plate("data", x.shape[0]):
            obs = pyro.sample("obs", dist.Normal(mean, sigma), obs=y)
        return mean


# Prepare tensors
X_train_t = torch.tensor(X_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train.squeeze(), dtype=torch.float32)
X_test_t = torch.tensor(X_test, dtype=torch.float32)

# Inference setup
bnn = BNN()
guide = AutoDiagonalNormal(bnn)
optimizer = DCTAdam({"lr": 0.01})
svi = SVI(bnn, guide, optimizer, loss=Trace_ELBO())

# Training
for epoch in range(3000):
    loss = svi.step(X_train_t, y_train_t)
    if epoch % 500 == 0:
        print(f"Epoch {epoch}, ELBO: {loss:.2f}")


# Posterior predictive sampling
import pyro.poutine


import pyro
import torch
import numpy as np

def predict_bnn(x, n_samples=100):
    preds = []

    for _ in range(n_samples):
        # Sample a trace from the guide (works with AutoGuide after training)
        sampled_trace = pyro.poutine.trace(guide).get_trace(x, None)

        # Replay model with sampled parameters from the guide
        conditioned_model = pyro.poutine.replay(bnn, trace=sampled_trace)

        # Trace the model and run it forward
        trace = pyro.poutine.trace(conditioned_model).get_trace(x, None)

        # Extract the mean of the likelihood from 'obs'
        mean = trace.nodes["obs"]["fn"].loc.detach().cpu().numpy()
        preds.append(mean)

    return np.stack(preds)



bnn_preds = predict_bnn(X_test_t)
mean_preds = bnn_preds.mean(axis=0).squeeze()
std_preds = bnn_preds.std(axis=0).squeeze()

# Plot predictive mean and uncertainty
plt.errorbar(range(len(mean_preds)), mean_preds, yerr=2 * std_preds, fmt='o', alpha=0.6)
plt.title("Bayesian Neural Network Predictions with Uncertainty")
plt.xlabel("Test sample index")
plt.ylabel("Predicted (standardized)")
plt.grid(True)
plt.show()
