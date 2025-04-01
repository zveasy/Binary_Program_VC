import os
import torch
import json
import networkx as nx
from torch_geometric.data import Data

JOERN_CFG_GRAPHS_DIR = "joern_cfg_graphs"
PT_OUTPUT_DIR = "pt_cfg_files"

os.makedirs(PT_OUTPUT_DIR, exist_ok=True)

def build_pyg_from_cfg_json(cfg_json_path):
    with open(cfg_json_path, "r") as f:
        data = json.load(f)
    G = nx.DiGraph()
    for node in data.get("nodes", []):
        G.add_node(node["id"], code=node.get("code", ""))
    for edge in data.get("edges", []):
        if edge["label"] == "CFG":
            G.add_edge(edge["from"], edge["to"])
    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}
    edge_index = []
    for (src, dst) in G.edges:
        edge_index.append([node_map[src], node_map[dst]])
    import torch
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
    x = torch.tensor([[G.degree(n)] for n in node_list], dtype=torch.float)
    # For a demonstration, we can store a dummy label or parse from folder name
    y = torch.zeros(len(node_list), dtype=torch.long)
    return Data(x=x, edge_index=edge_index, y=y)

folders = [
    d for d in os.listdir(JOERN_CFG_GRAPHS_DIR)
    if os.path.isdir(os.path.join(JOERN_CFG_GRAPHS_DIR, d))
]

for folder in folders:
    cfg_json = os.path.join(JOERN_CFG_GRAPHS_DIR, folder, "cfg", "0.json")
    if not os.path.exists(cfg_json):
        continue
    data = build_pyg_from_cfg_json(cfg_json)
    # Save .pt:
    out_file = os.path.join(PT_OUTPUT_DIR, f"{folder}.pt")
    torch.save(data, out_file)
    print("Saved:", out_file)
