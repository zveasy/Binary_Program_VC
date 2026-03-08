"""
Graph conversion utilities — parsing .dot files and converting to PyTorch Geometric format.

Unified from convert_dot_to_pt.py and cfg2_to_pt.py.
"""

import os
import glob
from typing import Optional

import networkx as nx

try:
    import pydot
    HAS_PYDOT = True
except ImportError:
    HAS_PYDOT = False

try:
    import torch
    from torch_geometric.data import Data
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class DotParser:
    """Parse .dot graph files into NetworkX DiGraph objects."""

    @staticmethod
    def parse(dot_path: str) -> nx.DiGraph:
        """Parse a single .dot file into a NetworkX DiGraph."""
        if not HAS_PYDOT:
            raise ImportError("pydot is required for parsing .dot files")

        graphs = pydot.graph_from_dot_file(dot_path)
        pydot_graph = graphs[0]

        G = nx.DiGraph()
        skip_names = {'node', 'graph', 'edge'}

        for node in pydot_graph.get_nodes():
            node_id = node.get_name()
            if node_id not in skip_names:
                G.add_node(node_id)

        for edge in pydot_graph.get_edges():
            src, dst = edge.get_source(), edge.get_destination()
            if src not in skip_names and dst not in skip_names:
                G.add_edge(src, dst)

        return G

    @staticmethod
    def parse_folder(cfg_path: str, pattern: str = "*-cfg.dot") -> Optional[nx.DiGraph]:
        """Merge all matching .dot files in a folder into one DiGraph."""
        big_G = nx.DiGraph()
        dot_files = glob.glob(os.path.join(cfg_path, pattern))
        if not dot_files:
            return None

        for df in dot_files:
            sub_G = DotParser.parse(df)
            big_G.add_nodes_from(sub_G.nodes())
            big_G.add_edges_from(sub_G.edges())

        return big_G


class GraphConverter:
    """Convert NetworkX graphs to PyTorch Geometric Data objects."""

    @staticmethod
    def nx_to_pyg(G: nx.DiGraph):
        """Convert a NetworkX DiGraph to a PyTorch Geometric Data object.
        Node feature = out-degree (single scalar). Label = 0 (dummy).
        """
        if not HAS_TORCH:
            raise ImportError("torch and torch_geometric are required for graph conversion")

        node_list = list(G.nodes)
        node_map = {nid: i for i, nid in enumerate(node_list)}
        edges = [(node_map[u], node_map[v]) for u, v in G.edges()]
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

        x = torch.tensor([[G.out_degree(n)] for n in node_list], dtype=torch.float)
        y = torch.zeros(x.size(0), dtype=torch.long)

        return Data(x=x, edge_index=edge_index, y=y)
