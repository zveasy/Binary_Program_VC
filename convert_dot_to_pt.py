#!/usr/bin/env python3
import os
import glob
import pydot
import networkx as nx
import torch
from torch_geometric.data import Data

# Where your 'joern_cfg_graphs' subfolders are
JOERN_CFG_ROOT = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
# We'll write the final .pt files here
PT_OUTPUT_DIR  = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/pt_cfg_files"

os.makedirs(PT_OUTPUT_DIR, exist_ok=True)

def parse_dot_file(dot_path):
    """
    Parse a single *.dot file into a pydot graph, then convert to a NetworkX DiGraph.
    """
    graphs = pydot.graph_from_dot_file(dot_path)
    # 'graphs' can be a list, usually with 1 element for a single DOT file:
    pydot_graph = graphs[0]  
    
    G = nx.DiGraph()
    # Add nodes
    for node in pydot_graph.get_nodes():
        node_id = node.get_name()
        # skip special graph-level "node" or "graph" strings
        if node_id in ('node', 'graph', 'edge'):
            continue
        G.add_node(node_id)  # We could store node attributes here if needed

    # Add edges
    for edge in pydot_graph.get_edges():
        src = edge.get_source()
        dst = edge.get_destination()
        if src in ('node','graph','edge') or dst in ('node','graph','edge'):
            continue
        G.add_edge(src, dst)
    
    return G

def unify_dot_files_in_folder(cfg2_path):
    """
    For a folder 'cfg2' containing multiple DOT files like 0-cfg.dot, 1-cfg.dot, etc.
    Combine them all into one big NetworkX DiGraph.
    """
    big_G = nx.DiGraph()
    dot_files = glob.glob(os.path.join(cfg2_path, "*-cfg.dot"))
    if not dot_files:
        return None  # no DOT files found
    
    for df in dot_files:
        subG = parse_dot_file(df)
        # Merge subG into big_G
        big_G.add_nodes_from(subG.nodes())
        big_G.add_edges_from(subG.edges())
    
    return big_G

def nx_to_pyg(G):
    """
    Convert a NetworkX DiGraph -> PyTorch Geometric Data
    Node feature = node degree, label = 0 for all (dummy).
    """
    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}
    edges = [(node_map[u], node_map[v]) for (u,v) in G.edges()]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    
    # For demonstration: single scalar feature = out-degree
    x = torch.tensor([[G.out_degree(n)] for n in node_list], dtype=torch.float)
    
    # Dummy label (all zeros)
    y = torch.zeros(x.size(0), dtype=torch.long)
    
    return Data(x=x, edge_index=edge_index, y=y)

def main():
    # Iterate over subfolders e.g. "O_1_s12345"
    subfolders = [d for d in os.listdir(JOERN_CFG_ROOT)
                  if os.path.isdir(os.path.join(JOERN_CFG_ROOT, d))]

    for folder in subfolders:
        cfg2_path = os.path.join(JOERN_CFG_ROOT, folder, "cfg2")
        if not os.path.isdir(cfg2_path):
            print(f"Skipping {folder}: no cfg2 directory")
            continue
        
        # Combine all *.dot in 'cfg2' into one big graph
        big_G = unify_dot_files_in_folder(cfg2_path)
        if big_G is None:
            print(f"Skipping {folder}: no .dot files in cfg2/")
            continue
        
        # Convert to PyG
        data = nx_to_pyg(big_G)
        
        # Derive complexity label from folder prefix, e.g. "O_1", "O_n", etc. if you want
        # For now, we'll just store the .pt under a subfolder
        complexity_label = folder.split("_s")[0]
        out_subdir = os.path.join(PT_OUTPUT_DIR, complexity_label)
        os.makedirs(out_subdir, exist_ok=True)
        
        pt_name = f"{folder}.pt"
        pt_path = os.path.join(out_subdir, pt_name)
        torch.save(data, pt_path)
        print(f"Saved {pt_path} ({big_G.number_of_nodes()} nodes, {big_G.number_of_edges()} edges)")

if __name__ == "__main__":
    main()
