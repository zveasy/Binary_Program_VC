"""
ComplexityPredictor — predict algorithm complexity from CFG using trained GNN models.

Wraps the GAT inference pipeline into a clean API.
"""

import os
import json
import sys
from typing import Optional

from engine.graph_conversion import DotParser, GraphConverter


class ComplexityPredictor:
    """
    Predict complexity class from a .dot CFG file using a trained GAT model.

    Usage:
        predictor = ComplexityPredictor("gat_model.pt", "gat_label_map.json")
        label = predictor.predict("firmware/cfg.dot")
    """

    def __init__(self, model_path: str, label_map_path: str):
        self.model_path = model_path
        self.label_map_path = label_map_path
        self._model = None
        self._idx_to_label = None

    @property
    def available(self) -> bool:
        """Check if the trained model and label map exist."""
        return (os.path.isfile(self.model_path)
                and os.path.isfile(self.label_map_path))

    def _load(self):
        """Lazy-load model and label map."""
        if self._model is not None:
            return

        import torch
        from engine.models.gat import GAT

        checkpoint = torch.load(self.model_path, map_location="cpu")
        state_dict = checkpoint["state_dict"]
        in_dim = checkpoint["in_dim"]
        hidden_dim = checkpoint["hidden_dim"]
        out_dim = checkpoint["out_dim"]

        with open(self.label_map_path) as f:
            label_map = json.load(f)
        self._idx_to_label = {i: name for name, i in label_map.items()}

        self._model = GAT(in_dim=in_dim, hidden_dim=hidden_dim, out_dim=out_dim)
        self._model.load_state_dict(state_dict)
        self._model.eval()

    def predict(self, dot_path: str) -> Optional[str]:
        """Predict complexity class from a .dot file. Returns label string or None."""
        if not self.available:
            return None

        try:
            self._load()
        except Exception:
            return None

        import torch
        from torch_geometric.data import Batch

        try:
            G = DotParser.parse(dot_path)
        except Exception:
            return None

        if G.number_of_nodes() == 0:
            return "Unknown"

        data = GraphConverter.nx_to_pyg(G)
        batch = Batch.from_data_list([data])

        with torch.no_grad():
            out = self._model(batch)
        logits = out.mean(dim=0, keepdim=True)
        pred_idx = int(logits.argmax(dim=1).item())
        return self._idx_to_label.get(pred_idx, f"class_{pred_idx}")
