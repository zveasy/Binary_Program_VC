# Shared GAT model for training and inference (used by train_gat_dataset.py and predict_complexity.py)
import torch
from torch_geometric.nn import GATConv


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
