"""
ML models for complexity classification.

Canonical model definitions live here. Root-level gat_model.py and
complexity_gnn.py re-export from these modules for backward compatibility.
"""

try:
    from engine.models.gat import GAT
    from engine.models.gnn import ComplexityGNN
except ImportError:
    pass  # torch/torch_geometric not installed (GNN deps are optional)
