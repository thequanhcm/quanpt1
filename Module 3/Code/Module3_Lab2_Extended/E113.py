#pip install backpack-for-pytorch
import torch
import torch.nn as nn
from backpack import backpack, extend
from backpack.extensions import BatchGrad, HessianVectorProduct

# Extend model and loss for BackPACK
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

# Wrap model and loss with backpack
model = extend(SimpleMLP())
loss_fn = extend(nn.CrossEntropyLoss())
def compute_influence(model, x_train, y_train, x_test, y_test, damping=0.01):
    """
    Estimate influence of (x_train, y_train) on loss at (x_test, y_test)
    """
    model.zero_grad()
    
    # 1. Compute ∇θ L(test)
    test_loss = loss_fn(model(x_test.unsqueeze(0)), y_test.unsqueeze(0))
    with backpack(HessianVectorProduct()):
        test_loss.backward(retain_graph=True)
        grad_test = [p.grad.detach().clone() for p in model.parameters()]
    
    # 2. Compute H^-1 * ∇θ L(test) (HVP)
    # Simplified by damping identity approximation
    hvp_approx = [g / damping for g in grad_test]

    # 3. Compute ∇θ L(train)
    model.zero_grad()
    train_loss = loss_fn(model(x_train.unsqueeze(0)), y_train.unsqueeze(0))
    with backpack(BatchGrad()):
        train_loss.backward()
        grad_train = [p.grad_batch[0].detach().clone() for p in model.parameters()]
    
    # 4. Influence = - ∇θ L(train)^T * H^-1 ∇θ L(test)
    influence = sum([
        -torch.sum(g_t * hvp) for g_t, hvp in zip(grad_train, hvp_approx)
    ])
    
    return influence.item(), grad_train, hvp_approx
@torch.no_grad()
def apply_unlearning_update(model, grad_train, hvp_approx, lr=1e-3):
    for p, g_t, hvp in zip(model.parameters(), grad_train, hvp_approx):
        # Approximate update to remove influence of train point
        p.data += lr * (g_t * hvp)  # this is a crude influence-based correction
from torchvision import datasets, transforms

transform = transforms.ToTensor()
mnist = datasets.MNIST(root="./data", train=True, download=True, transform=transform)

x_train, y_train = mnist[0]
x_test, y_test = mnist[1]

# Forward and compute influence
influence, grad_train, hvp_approx = compute_influence(model, x_train, y_train, x_test, y_test)

print(f"Influence score: {influence:.5f}")

# Apply influence-based update
apply_unlearning_update(model, grad_train, hvp_approx)
