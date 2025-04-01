import os
import json
import torch
import networkx as nx
from torch_geometric.data import Data

INPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
OUTPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/pt_cfg_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def build_pyg_from_cfg_json(json_path):
    with open(json_path) as f:
        data = json.load(f)

    G = nx.DiGraph()
    for node in data.get("nodes", []):
        G.add_node(node["id"], label=node.get("code", ""))

    for edge in data.get("edges", []):
        if edge["label"] == "CFG":
            G.add_edge(edge["from"], edge["to"])

    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}
    edge_index = torch.tensor(
        [[node_map[e[0]], node_map[e[1]]] for e in G.edges],
        dtype=torch.long
    ).t().contiguous()
    x = torch.tensor([[G.degree(n)] for n in node_list], dtype=torch.float)
    y = torch.zeros(x.size(0), dtype=torch.long)  # Placeholder label

    return Data(x=x, edge_index=edge_index, y=y)

# Loop over each folder
for folder in os.listdir(INPUT_DIR):
    full_path = os.path.join(INPUT_DIR, folder)
    cfg_path = os.path.join(full_path, "cfg2", "0.json")

    if not os.path.isfile(cfg_path):
        print(f"Skipping {folder}: no cfg2/0.json")
        continue

    try:
        data = build_pyg_from_cfg_json(cfg_path)

        # Extract label from folder name, e.g., O_n2_s12345 → O_n2
        time_label = folder.split("_s")[0]
        label_dir = os.path.join(OUTPUT_DIR, time_label)
        os.makedirs(label_dir, exist_ok=True)

        pt_path = os.path.join(label_dir, f"{folder}.pt")
        torch.save(data, pt_path)
        print(f"✅ Saved {pt_path}")
    except Exception as e:
        print(f"❌ Failed on {folder}: {e}")
