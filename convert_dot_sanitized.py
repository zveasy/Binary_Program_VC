#!/usr/bin/env python3
import os
import glob
import pydot
import re
import networkx as nx
import torch
from torch_geometric.data import Data

JOERN_CFG_ROOT = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
PT_OUTPUT_DIR  = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/pt_cfg_files"
os.makedirs(PT_OUTPUT_DIR, exist_ok=True)

def remove_labels_entirely(raw_dot: str) -> str:
    """
    If a line contains 'label =', remove or blank that entire label portion.
    This is a quick hack: we remove node labels so pydot won't fail on angle brackets.
    """
    lines = raw_dot.splitlines()
    new_lines = []
    for line in lines:
        if "label =" in line:
            # Option 1: remove the line altogether
            # line = "" 
            
            # Option 2: just rewrite label to an empty string
            line = re.sub(r'label\s*=\s*"[^"]*"', 'label = ""', line)
            line = re.sub(r'label\s*=\s*<[^>]*>', 'label = ""', line)
            # if there's more complicated multi-line tags, they'd be cut here
        new_lines.append(line)
    return "\n".join(new_lines)

def parse_dot_file(dot_path: str) -> nx.DiGraph:
    with open(dot_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # Remove or replace all label lines
    sanitized = remove_labels_entirely(raw)

    graphs = pydot.graph_from_dot_data(sanitized)
    if not graphs:
        print(f"[WARNING] pydot failed to parse: {dot_path}")
        return None

    pydot_graph = graphs[0]
    G_nx = nx.drawing.nx_pydot.from_pydot(pydot_graph)
    return G_nx

def unify_dot_files_in_folder(cfg2_path: str) -> nx.DiGraph:
    big_G = nx.DiGraph()
    dot_files = glob.glob(os.path.join(cfg2_path, "*-cfg.dot"))
    if not dot_files:
        return None
    
    success = False
    for df in dot_files:
        subG = parse_dot_file(df)
        if subG is None:
            continue
        success = True
        big_G.add_nodes_from(subG.nodes())
        big_G.add_edges_from(subG.edges())
    
    return big_G if success else None

def nx_to_pyg(G: nx.DiGraph) -> Data:
    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}
    edges = [(node_map[u], node_map[v]) for (u,v) in G.edges()]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    x = torch.tensor([[G.out_degree(n)] for n in node_list], dtype=torch.float)
    y = torch.zeros(len(node_list), dtype=torch.long)
    
    return Data(x=x, edge_index=edge_index, y=y)

def main():
    subfolders = [d for d in os.listdir(JOERN_CFG_ROOT)
                  if os.path.isdir(os.path.join(JOERN_CFG_ROOT, d))]

    for folder in subfolders:
        cfg2_path = os.path.join(JOERN_CFG_ROOT, folder, "cfg2")
        if not os.path.isdir(cfg2_path):
            continue

        complexity_label = folder.split("_s")[0]
        out_subdir = os.path.join(PT_OUTPUT_DIR, complexity_label)
        os.makedirs(out_subdir, exist_ok=True)

        pt_name = f"{folder}.pt"
        pt_path = os.path.join(out_subdir, pt_name)
        if os.path.exists(pt_path):
            print(f"[SKIP] {pt_name} already exists.")
            continue

        big_G = unify_dot_files_in_folder(cfg2_path)
        if big_G is None:
            print(f"[SKIP] {folder}: no parseable .dot files in cfg2/")
            continue

        data = nx_to_pyg(big_G)
        torch.save(data, pt_path)
        print(f"[SAVED] {pt_path} ({big_G.number_of_nodes()} nodes, {big_G.number_of_edges()} edges)")

if __name__ == "__main__":
    main()
