# train_gat_dataset.py

import os
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv
from torch_geometric.data import DataLoader
from sklearn.metrics import accuracy_score, classification_report
from collections import defaultdict

DATA_DIR = "joern_cfg_graphs"  # Adjust this if needed
BATCH_SIZE = 32
EPOCHS = 30

# === 1. Load all .pt CFG graphs ===
print("[INFO] Loading graphs...")
all_graphs = []
label_names = set()

for fname in os.listdir(DATA_DIR):
    if fname.endswith(".pt"):
        label = fname.split("_")[0]
        label_names.add(label)
        graph = torch.load(os.path.join(DATA_DIR, fname))
        graph.label_name = label
        all_graphs.append(graph)

# Build label map (e.g. 'O_n2': 3)
label_names = sorted(list(label_names))
label_map = {name: i for i, name in enumerate(label_names)}
print(f"[INFO] Label Map: {label_map}")

# Convert string labels to int class ids
for g in all_graphs:
    g.y = torch.tensor([label_map[g.label_name]] * g.num_nodes, dtype=torch.long)

# Split train/val
split_idx = int(0.8 * len(all_graphs))
train_graphs = all_graphs[:split_idx]
val_graphs = all_graphs[split_idx:]

train_loader = DataLoader(train_graphs, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_graphs, batch_size=BATCH_SIZE)

# === 2. Define GAT Model ===
class GAT(torch.nn.Module):
    def __init__(self, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.conv1 = GATConv(in_dim, hidden_dim, heads=2, concat=True)
        self.conv2 = GATConv(hidden_dim * 2, out_dim, heads=1, concat=False)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = GAT(in_dim=1, hidden_dim=64, out_dim=len(label_map)).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.005)

# === 3. Training Loop ===
def evaluate(model, loader):
    model.eval()
    y_true, y_pred = [], []

    for batch in loader:
        batch = batch.to(device)
        out = model(batch)
        preds = out.argmax(dim=1).detach().cpu().tolist()
        labels = batch.y.cpu().tolist()

        y_true.extend(labels)
        y_pred.extend(preds)

    acc = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=label_names)
    return acc, report

print("[INFO] Starting training...")
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

    for batch in train_loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        out = model(batch)
        loss = F.cross_entropy(out, batch.y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    val_acc, val_report = evaluate(model, val_loader)
    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss:.4f} | Val Acc: {val_acc:.4f}")

print("\n[INFO] Final Validation Report:\n")
print(val_report)
