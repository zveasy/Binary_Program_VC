# train_gat_dataset.py

import os
import json
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv
from torch_geometric.data import DataLoader
from sklearn.metrics import accuracy_score, classification_report
from collections import defaultdict

# Configurable paths
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("GAT_DATA_DIR", os.path.join(_REPO_ROOT, "joern_cfg_graphs"))
MODEL_SAVE_PATH = os.environ.get("GAT_MODEL_PATH", os.path.join(_REPO_ROOT, "gat_model.pt"))
LABEL_MAP_SAVE_PATH = os.environ.get("GAT_LABEL_MAP_PATH", os.path.join(_REPO_ROOT, "gat_label_map.json"))

BATCH_SIZE = 32
EPOCHS = 30
IN_DIM = 1
HIDDEN_DIM = 64

# === 1. Load all .pt CFG graphs ===
print("[INFO] Loading graphs from", DATA_DIR, "...")
all_graphs = []
label_names = set()

if not os.path.isdir(DATA_DIR):
    print("[ERROR] DATA_DIR not found:", DATA_DIR)
    exit(1)

for fname in os.listdir(DATA_DIR):
    if fname.endswith(".pt"):
        label = fname.split("_")[0]
        label_names.add(label)
        graph = torch.load(os.path.join(DATA_DIR, fname))
        graph.label_name = label
        all_graphs.append(graph)

if not all_graphs:
    print("[ERROR] No .pt graphs found in", DATA_DIR)
    exit(1)

# Build label map
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
from gat_model import GAT

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
out_dim = len(label_map)
model = GAT(in_dim=IN_DIM, hidden_dim=HIDDEN_DIM, out_dim=out_dim).to(device)
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

# === 4. Save model and label_map for inference ===
os.makedirs(os.path.dirname(MODEL_SAVE_PATH) or ".", exist_ok=True)
torch.save({
    "state_dict": model.state_dict(),
    "in_dim": IN_DIM,
    "hidden_dim": HIDDEN_DIM,
    "out_dim": out_dim,
}, MODEL_SAVE_PATH)
with open(LABEL_MAP_SAVE_PATH, "w") as f:
    json.dump(label_map, f, indent=2)
print(f"\n[INFO] Model saved to {MODEL_SAVE_PATH}")
print(f"[INFO] Label map saved to {LABEL_MAP_SAVE_PATH}")
