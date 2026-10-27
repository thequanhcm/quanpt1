import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, random_split
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from sklearn.metrics import accuracy_score

# Define a simple CNN with dropout for MC Dropout
class MC_Dropout_CNN(nn.Module):
    def __init__(self, dropout_rate=0.5):
        super(MC_Dropout_CNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(dropout_rate)
        self.fc1 = nn.Linear(128 * 8 * 8, 256)
        self.fc2 = nn.Linear(256, 2)  # 2 classes: benign and malignant

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = x.view(x.size(0), -1)
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        return x

# Enable MC Dropout at test time
def enable_dropout(model):
    for m in model.modules():
        if m.__class__.__name__.startswith('Dropout'):
            m.train()

# Predict with uncertainty using MC Dropout
@torch.no_grad()
def predict_mc(model, inputs, n_samples=30):
    model.eval()
    enable_dropout(model)
    preds = []
    for _ in range(n_samples):
        outputs = model(inputs)
        preds.append(F.softmax(outputs, dim=1).cpu().numpy())
    preds = np.stack(preds)  # shape (n_samples, batch_size, num_classes)
    return preds

# Visualization: Grad-CAM + Variance Map (simplified)
from captum.attr import LayerGradCam
from captum.attr import visualization as viz

def compute_gradcam(model, inputs, target_layer, class_idx=None):
    model.eval()
    gradcam = LayerGradCam(model, target_layer)
    attributions = gradcam.attribute(inputs, target=class_idx)
    return attributions

# Example usage:


# Sample training loop

def train_model(model, train_loader, val_loader, n_epochs=2, lr=1e-3, device='cuda'):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    model = model.to(device)

    for epoch in range(n_epochs):
        model.train()
        running_loss = 0.0
        for images, labels in tqdm(train_loader):
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        print(f"Epoch {epoch+1}/{n_epochs}, Loss: {running_loss/len(train_loader):.4f}")
        evaluate(model, val_loader, device)

# Evaluation

def evaluate(model, data_loader, device='cuda'):
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for images, labels in data_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            preds = torch.argmax(outputs, dim=1)
            all_preds.append(preds.cpu())
            all_labels.append(labels.cpu())
    acc = accuracy_score(torch.cat(all_labels), torch.cat(all_preds))
    print(f"Validation Accuracy: {acc:.4f}")

# Accuracy vs Uncertainty Plot

def plot_accuracy_vs_uncertainty(model, data_loader, n_samples=30, device='cuda'):
    model = model.to(device)
    model.eval()
    uncertainties = []
    correct = []

    for images, labels in tqdm(data_loader):
        images, labels = images.to(device), labels.to(device)
        preds = predict_mc(model, images, n_samples=n_samples)
        mean_preds = preds.mean(axis=0)
        variance = preds.var(axis=0).mean(axis=1)  # predictive uncertainty
        pred_labels = np.argmax(mean_preds, axis=1)

        uncertainties.extend(variance.tolist())
        correct.extend((pred_labels == labels.cpu().numpy()).tolist())

    uncertainties = np.array(uncertainties)
    correct = np.array(correct)

    plt.scatter(uncertainties, correct, alpha=0.5)
    plt.xlabel('Predictive Variance (Uncertainty)')
    plt.ylabel('Correct (1) / Incorrect (0)')
    plt.title('Accuracy vs. Uncertainty')
    plt.grid(True)
    plt.savefig("AccvsUncertainty.png")

# Main Setup
if __name__ == "__main__":
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor()
    ])

    dataset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform)

    dataset.targets = [0 if t == 0 else 1 for t in dataset.targets]

    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64)

    model = MC_Dropout_CNN(dropout_rate=0.5)

    train_model(model, train_loader, val_loader, n_epochs=5, lr=1e-3, device=device)

    plot_accuracy_vs_uncertainty(model, val_loader, device=device)

    ### NEW -- Grad-CAM Visualization after training
    model = model.to(device)
    model.eval()

    # Take 1 batch of validation images
    images, labels = next(iter(val_loader))
    images, labels = images.to(device), labels.to(device)

    # Pick one image from the batch
    img = images[0].unsqueeze(0)  # add batch dimension
    label = labels[0].item()

    # Compute Grad-CAM
    attributions = compute_gradcam(model, img, model.conv3, class_idx=label)

    # Squeeze dimensions correctly
    attributions = attributions.squeeze().detach().cpu().numpy()  # shape (H, W)

    # Expand to 3-channel if you want to use visualize_image_attr
    attr_3ch = np.repeat(attributions[..., np.newaxis], 3, axis=-1)

    viz.visualize_image_attr(
        attr_3ch,
        method='heat_map',
        sign='positive',
        show_colorbar=True,
        title='Grad-CAM Map'
    )
    plt.savefig('gradcam_output.png', bbox_inches='tight')
    plt.close()  # close the figure to avoid duplicate plots